"""A pipeline do CATINET: uma busca (manual ou automática) e o vigia que a repete.

`executar_busca` faz UMA rodada completa: lê as configurações, roda o scraper e grava os
chamados novos como Pendentes. É chamada tanto pelo botão "Buscar chamados" quanto pelo
vigia automático (`laco_automatico`), que acorda a cada minuto e roda se já passou o
intervalo configurado.

Garantia de "uma busca de cada vez": um trinco (advisory lock) do próprio PostgreSQL.
Vale entre threads E entre processos, então nem o clique do operador nem um segundo
processo do servidor conseguem rodar duas buscas juntas.
"""

import asyncio
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from crud import chamado as crud_chamado
from services import catinet_credenciais
from services.catinet_scraper import ErroCatinet, analisar_url
from services.database import SessionLocal, engine

log = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parent.parent
TEMPO_MAXIMO_BUSCA = 240  # segundos: login + fila + um pedido por chamado novo
INTERVALO_PADRAO_MIN = 15
INTERVALO_MINIMO_MIN = 5  # abaixo disso estaríamos martelando o CATINET
_ID_TRINCO = 7351001  # número qualquer, só precisa ser sempre o mesmo


@dataclass
class ResultadoBusca:
    executou: bool  # False = nem tentou (sem configuração, ocupada, ainda não é a hora)
    ok: bool
    mensagem: str
    novos: int = 0


def _rodar_scraper(entrada: str) -> dict:
    processo = subprocess.run(
        [sys.executable, "-m", "services.catinet_scraper"],
        input=entrada,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(RAIZ),
        timeout=TEMPO_MAXIMO_BUSCA,
    )
    try:
        return json.loads(processo.stdout)
    except json.JSONDecodeError:
        log.error("Saída inesperada do scraper: %s", (processo.stderr or "")[-500:])
        return {"erro": "A busca terminou de forma inesperada. Veja o log do sistema."}


def intervalo_minutos(db) -> int:
    bruto = crud_chamado.obter_config(db, crud_chamado.CHAVE_INTERVALO)
    try:
        return max(INTERVALO_MINIMO_MIN, int(bruto))
    except ValueError:
        return INTERVALO_PADRAO_MIN


def automatico_ligado(db) -> bool:
    # Só um "0" explícito desliga: sem configuração nenhuma, nasce ligado.
    return crud_chamado.obter_config(db, crud_chamado.CHAVE_AUTO) != "0"


def _ja_na_hora(db) -> bool:
    ultima = crud_chamado.obter_config(db, crud_chamado.CHAVE_ULTIMA_TENTATIVA)
    if not ultima:
        return True
    try:
        return datetime.now() - datetime.fromisoformat(ultima) >= timedelta(
            minutes=intervalo_minutos(db)
        )
    except ValueError:
        return True


def _registrar(db, ok: bool, mensagem: str) -> None:
    agora = datetime.now().isoformat(timespec="seconds")
    crud_chamado.gravar_config(db, crud_chamado.CHAVE_ULTIMA_BUSCA, agora)
    crud_chamado.gravar_config(
        db, crud_chamado.CHAVE_ULTIMO_RESULTADO, ("ok|" if ok else "erro|") + mensagem
    )


def executar_busca(automatica: bool = False) -> ResultadoBusca:
    """Uma rodada completa. Nunca levanta erro: devolve sempre um ResultadoBusca.

    `automatica=True` (o vigia): se faltar configuração ou ainda não for a hora, nem
    tenta e não registra nada — só o clique do operador merece reclamação na tela.
    """
    db = SessionLocal()
    try:
        url = crud_chamado.obter_config(db, crud_chamado.CHAVE_URL_FILA)
        usuario = crud_chamado.obter_config(db, crud_chamado.CHAVE_USUARIO)
        senha = catinet_credenciais.obter_senha(usuario)

        if not (usuario and senha):
            return ResultadoBusca(
                False,
                False,
                "Credenciais não configuradas. Abra o menu do seu nome (canto inferior "
                "esquerdo) e escolha “Credenciais”.",
            )
        if not url:
            return ResultadoBusca(
                False,
                False,
                "Link da fila não configurado. Abra o menu do seu nome e escolha "
                "“Configurações”.",
            )
        try:
            analisar_url(url)
        except ErroCatinet as e:
            return ResultadoBusca(False, False, str(e))

        # Trinco: numa conexão própria, que fica aberta durante toda a busca.
        trinco = engine.connect()
        try:
            if not trinco.execute(text("select pg_try_advisory_lock(:i)"), {"i": _ID_TRINCO}).scalar():
                return ResultadoBusca(False, False, "Já há uma busca em andamento. Aguarde.")
            try:
                db.expire_all()
                if automatica and not _ja_na_hora(db):
                    return ResultadoBusca(False, True, "Ainda não é a hora.")
                # Marca a tentativa ANTES: se falhar, a próxima só vem no intervalo.
                crud_chamado.gravar_config(
                    db,
                    crud_chamado.CHAVE_ULTIMA_TENTATIVA,
                    datetime.now().isoformat(timespec="seconds"),
                )
                return _buscar_e_gravar(db, url, usuario, senha)
            finally:
                trinco.execute(text("select pg_advisory_unlock(:i)"), {"i": _ID_TRINCO})
        finally:
            trinco.close()
    except Exception:
        log.exception("Falha inesperada na busca do CATINET")
        return ResultadoBusca(True, False, "Falha inesperada na busca. Veja o log do sistema.")
    finally:
        db.close()


def _buscar_e_gravar(db, url: str, usuario: str, senha: str) -> ResultadoBusca:
    entrada = json.dumps(
        {
            "url": url,
            "usuario": usuario,
            "senha": senha,
            "conhecidos": sorted(crud_chamado.referencias_existentes(db)),
        }
    )
    try:
        resultado = _rodar_scraper(entrada)
    except subprocess.TimeoutExpired:
        resultado = {"erro": "O CATINET demorou demais para responder."}
    except Exception:
        log.exception("Falha ao executar o scraper do CATINET")
        resultado = {"erro": "Não foi possível executar a busca. Veja o log do sistema."}

    if "erro" in resultado:
        _registrar(db, False, resultado["erro"])
        return ResultadoBusca(True, False, resultado["erro"])

    novos = crud_chamado.salvar_novos(db, resultado["chamados"])
    mensagem = (
        f"{novos} chamado(s) novo(s) encontrado(s)." if novos else "Nenhum chamado novo na fila."
    )
    _registrar(db, True, mensagem)
    return ResultadoBusca(True, True, mensagem, novos)


def _hora_de_rodar() -> bool:
    db = SessionLocal()
    try:
        return automatico_ligado(db) and _ja_na_hora(db)
    finally:
        db.close()


async def laco_automatico() -> None:
    """O vigia. Registrado como "lifespan task" do Reflex: nasce com o servidor e morre
    com ele. Acorda a cada minuto; só trabalha se estiver ligado e já passou o intervalo."""
    await asyncio.sleep(30)  # deixa o servidor terminar de subir
    while True:
        try:
            if await asyncio.to_thread(_hora_de_rodar):
                resultado = await asyncio.to_thread(executar_busca, True)
                if resultado.executou:
                    log.info("Busca automática do CATINET: %s", resultado.mensagem)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Erro no vigia do CATINET")
        await asyncio.sleep(60)
