"""Cérebro da tela Pipeline de Dados (/pipeline), do sino da topbar e dos diálogos do menu.

States separados, de propósito:
- ChamadosState     : a tela em si (buscar no CATINET, listar, aprovar, declinar).
- AlertasState      : o sino da topbar (quantos chamados esperam decisão). A topbar existe
                      em TODAS as páginas, por isso não pode ser do ChamadosState.
- CredenciaisState  : o diálogo "Credenciais" (usuário e senha do CATINET).
- ConfiguracoesState: o diálogo "Configurações" (link da fila e busca automática).

A busca em si mora em services/catinet_pipeline.py (é a mesma que o vigia automático usa).
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import reflex as rx

from crud import chamado as crud_chamado
from models.chamado import STATUS_PENDENTE
from services import catinet_credenciais
from services.catinet_pipeline import (
    INTERVALO_MINIMO_MIN,
    automatico_ligado,
    executar_busca,
    intervalo_minutos,
)
from services.catinet_scraper import ErroCatinet, analisar_url
from services.database import SessionLocal
from state.auth_state import AuthState

log = logging.getLogger(__name__)


@dataclass
class LinhaChamado:
    """Um chamado achatado para a tela (tudo texto)."""

    id: int
    referencia: str
    data: str
    solicitante: str
    telefone: str
    departamento: str
    item: str
    categoria: str
    descricao: str
    os_numero: str


def _para_linha(c) -> LinhaChamado:
    return LinhaChamado(
        id=c.id,
        referencia=c.referencia,
        data=c.data_registro.strftime("%d/%m/%Y %H:%M") if c.data_registro else "—",
        solicitante=c.solicitante or "—",
        telefone=c.telefone or "—",
        departamento=c.departamento or "—",
        item=c.item or "—",
        categoria=c.categoria or "—",
        descricao=c.descricao or "",
        os_numero=c.ordem.numero if c.ordem else "",
    )


def _resumo_ultima_busca(db) -> tuple[str, bool]:
    """('Última busca: 12/10 14:30 — 2 chamado(s) novo(s).', deu_erro)."""
    quando = crud_chamado.obter_config(db, crud_chamado.CHAVE_ULTIMA_BUSCA)
    if not quando:
        return "Nenhuma busca feita ainda.", False
    resultado = crud_chamado.obter_config(db, crud_chamado.CHAVE_ULTIMO_RESULTADO)
    situacao, _, mensagem = resultado.partition("|")
    try:
        hora = datetime.fromisoformat(quando).strftime("%d/%m %H:%M")
    except ValueError:
        hora = quando
    return f"Última busca: {hora} — {mensagem}", situacao == "erro"


class ChamadosState(rx.State):
    filtro: str = STATUS_PENDENTE
    chamados: list[LinhaChamado] = []
    n_pendentes: int = 0
    buscando: bool = False
    mensagem: str = ""
    erro: str = ""
    ultima_busca: str = ""
    ultima_busca_erro: bool = False

    def carregar(self):
        """on_load e depois de toda decisão: relê a lista do banco."""
        db = SessionLocal()
        try:
            self.chamados = [_para_linha(c) for c in crud_chamado.listar(db, self.filtro)]
            self.n_pendentes = crud_chamado.contar_pendentes(db)
            self.ultima_busca, self.ultima_busca_erro = _resumo_ultima_busca(db)
        finally:
            db.close()

    def abrir(self):
        """on_load da página: abre limpa, com os pendentes."""
        self.filtro = STATUS_PENDENTE
        self.mensagem = ""
        self.erro = ""
        self.carregar()

    def set_filtro(self, valor: str | list[str]):
        # o segmented_control entrega str (ou lista, se for de seleção múltipla)
        self.filtro = valor if isinstance(valor, str) else valor[0]
        self.carregar()

    # ── Busca manual no CATINET ─────────────────────────────────────────────────────
    async def buscar(self):
        self.mensagem = ""
        self.erro = ""
        self.buscando = True
        yield  # mostra o "Buscando..." na tela antes de começar a espera

        resultado = await asyncio.to_thread(executar_busca, False)

        self.buscando = False
        if resultado.ok:
            self.mensagem = resultado.mensagem
            self.filtro = STATUS_PENDENTE
        else:
            self.erro = resultado.mensagem
        self.carregar()
        yield AlertasState.carregar

    # ── Decisão do operador ─────────────────────────────────────────────────────────
    async def aprovar(self, chamado_id: int):
        self.mensagem = ""
        self.erro = ""
        auth = await self.get_state(AuthState)
        db = SessionLocal()
        try:
            numero = crud_chamado.aprovar(db, chamado_id, int(auth.user_id))
            self.mensagem = f"Chamado aprovado. Criada a O.S. {numero}."
        except ValueError as e:
            self.erro = str(e)
        except Exception:
            log.exception("Falha ao aprovar chamado %s", chamado_id)
            db.rollback()
            self.erro = "Não foi possível aprovar. Nada foi criado; tente de novo."
        finally:
            db.close()
        self.carregar()
        yield AlertasState.carregar

    async def declinar(self, chamado_id: int):
        self.mensagem = ""
        self.erro = ""
        auth = await self.get_state(AuthState)
        db = SessionLocal()
        try:
            crud_chamado.declinar(db, chamado_id, int(auth.user_id))
            self.mensagem = "Chamado declinado."
        except ValueError as e:
            self.erro = str(e)
        finally:
            db.close()
        self.carregar()
        yield AlertasState.carregar


class AlertasState(rx.State):
    """O sino da topbar: quantos chamados esperam decisão e como foi a última busca."""

    n_pendentes: int = 0
    ultima_busca: str = ""
    ultima_busca_erro: bool = False

    def carregar(self):
        """Roda ao montar a topbar (a cada página) e a cada minuto (ver navbar.py)."""
        db = SessionLocal()
        try:
            self.n_pendentes = crud_chamado.contar_pendentes(db)
            self.ultima_busca, self.ultima_busca_erro = _resumo_ultima_busca(db)
        except Exception:
            log.exception("Falha ao atualizar o sino")
        finally:
            db.close()

    def atualizar_periodico(self, _valor: str = ""):
        """Ligado ao relógio escondido da topbar; só repassa para carregar()."""
        self.carregar()


class CredenciaisState(rx.State):
    aberto: bool = False
    usuario: str = ""
    senha: str = ""
    tem_senha_salva: bool = False
    erro: str = ""

    def ao_abrir(self, aberto: bool):
        self.aberto = aberto
        self.erro = ""
        self.senha = ""  # a senha nunca volta para a tela
        if aberto:
            db = SessionLocal()
            try:
                self.usuario = crud_chamado.obter_config(db, crud_chamado.CHAVE_USUARIO)
            finally:
                db.close()
            self.tem_senha_salva = catinet_credenciais.obter_senha(self.usuario) is not None

    def abrir(self):
        """Ligado ao item 'Credenciais' do menu."""
        self.ao_abrir(True)

    def set_usuario(self, valor: str):
        self.usuario = valor

    def set_senha(self, valor: str):
        self.senha = valor

    def salvar(self):
        self.erro = ""
        usuario = self.usuario.strip()
        if not usuario:
            self.erro = "Informe o usuário."
            return
        if not self.senha and catinet_credenciais.obter_senha(usuario) is None:
            self.erro = "Informe a senha."
            return

        try:
            if self.senha:  # vazio = manter a senha que já está guardada
                catinet_credenciais.guardar_senha(usuario, self.senha)
        except Exception:
            log.exception("Falha ao guardar a senha no cofre do Windows")
            self.erro = "Não foi possível guardar a senha no cofre do Windows."
            return

        db = SessionLocal()
        try:
            crud_chamado.gravar_config(db, crud_chamado.CHAVE_USUARIO, usuario)
        finally:
            db.close()
        self.ao_abrir(False)
        return rx.toast.success("Credenciais do CATINET salvas.")


class ConfiguracoesState(rx.State):
    aberto: bool = False
    url_fila: str = ""
    intervalo: str = ""
    auto_ligado: bool = True
    erro: str = ""

    def ao_abrir(self, aberto: bool):
        self.aberto = aberto
        self.erro = ""
        if aberto:
            db = SessionLocal()
            try:
                self.url_fila = crud_chamado.obter_config(db, crud_chamado.CHAVE_URL_FILA)
                self.intervalo = str(intervalo_minutos(db))
                self.auto_ligado = automatico_ligado(db)
            finally:
                db.close()

    def abrir(self):
        """Ligado ao item 'Configurações' do menu."""
        self.ao_abrir(True)

    def set_url_fila(self, valor: str):
        self.url_fila = valor

    def set_intervalo(self, valor: str):
        self.intervalo = valor

    def set_auto_ligado(self, valor: bool):
        self.auto_ligado = valor

    def salvar(self):
        self.erro = ""
        try:
            analisar_url(self.url_fila)
        except ErroCatinet as e:
            self.erro = str(e)
            return
        try:
            minutos = int(self.intervalo)
        except ValueError:
            minutos = 0
        if minutos < INTERVALO_MINIMO_MIN or minutos > 1440:
            self.erro = (
                f"O intervalo deve ser um número de minutos entre {INTERVALO_MINIMO_MIN} e 1440."
            )
            return

        db = SessionLocal()
        try:
            crud_chamado.gravar_config(db, crud_chamado.CHAVE_URL_FILA, self.url_fila.strip())
            crud_chamado.gravar_config(db, crud_chamado.CHAVE_INTERVALO, str(minutos))
            crud_chamado.gravar_config(
                db, crud_chamado.CHAVE_AUTO, "1" if self.auto_ligado else "0"
            )
        finally:
            db.close()
        self.ao_abrir(False)
        return rx.toast.success("Configurações salvas.")
