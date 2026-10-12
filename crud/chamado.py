"""CRUD dos chamados do CATINET e das configurações do sistema.

Fluxo: `salvar_novos` grava o que o scraper trouxe (como Pendente) -> o operador decide:
`aprovar` cria a O.S. a partir do chamado; `declinar` só marca como descartado.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from crud import dominio as crud_dominio
from crud import ordem_servico as crud_os
from models.chamado import (
    STATUS_APROVADO,
    STATUS_DECLINADO,
    STATUS_PENDENTE,
    ChamadoCatinet,
    ConfigSistema,
)
from models.dominio import Classificacao, Meio, Peso, Setor
from services.importacao_lote import (
    CLASSIFICACAO_PADRAO,
    MEIO_PADRAO,
    PESO_PADRAO,
    indexar,
    normalizar,
)

CHAVE_URL_FILA = "catinet_url_fila"
CHAVE_USUARIO = "catinet_usuario"
CHAVE_INTERVALO = "catinet_intervalo_min"  # minutos entre buscas automáticas
CHAVE_AUTO = "catinet_auto"  # "0" = busca automática desligada
CHAVE_ULTIMA_TENTATIVA = "catinet_ultima_tentativa"  # base do intervalo (ISO)
CHAVE_ULTIMA_BUSCA = "catinet_ultima_busca"  # quando terminou a última busca (ISO)
CHAVE_ULTIMO_RESULTADO = "catinet_ultimo_resultado"  # "ok|mensagem" ou "erro|mensagem"


# ── Configurações (chave/valor) ──────────────────────────────────────────────────────

def obter_config(db: Session, chave: str) -> str:
    linha = db.get(ConfigSistema, chave)
    return (linha.valor or "") if linha else ""


def gravar_config(db: Session, chave: str, valor: str) -> None:
    linha = db.get(ConfigSistema, chave)
    if linha is None:
        db.add(ConfigSistema(chave=chave, valor=valor))
    else:
        linha.valor = valor
    db.commit()


# ── Chamados ─────────────────────────────────────────────────────────────────────────

def referencias_existentes(db: Session) -> set[str]:
    """Todas as referências já capturadas (qualquer status) — para não repetir."""
    return {ref for (ref,) in db.query(ChamadoCatinet.referencia).all()}


def salvar_novos(db: Session, chamados: list[dict]) -> int:
    """Grava os chamados cuja referência ainda não existe. Devolve quantos eram novos."""
    existentes = referencias_existentes(db)
    novos = 0
    for c in chamados:
        ref = c.get("referencia")
        if not ref or ref in existentes:
            continue
        existentes.add(ref)
        db.add(
            ChamadoCatinet(
                referencia=ref,
                evento_id=c["evento_id"],
                data_registro=(
                    datetime.fromisoformat(c["data_registro"]) if c.get("data_registro") else None
                ),
                solicitante=c.get("solicitante"),
                telefone=c.get("telefone"),
                departamento=c.get("departamento"),
                item=c.get("item"),
                categoria=c.get("categoria"),
                descricao=c.get("descricao"),
            )
        )
        novos += 1
    db.commit()
    return novos


def listar(db: Session, status: str) -> list[ChamadoCatinet]:
    """Os do status pedido: os mais recentes primeiro (os antigos já foram vistos)."""
    return (
        db.query(ChamadoCatinet)
        .filter(ChamadoCatinet.status == status)
        .order_by(ChamadoCatinet.data_registro.desc().nullslast(), ChamadoCatinet.id.desc())
        .all()
    )


def contar_pendentes(db: Session) -> int:
    return db.query(ChamadoCatinet).filter(ChamadoCatinet.status == STATUS_PENDENTE).count()


def contagem_por_status(db: Session) -> dict[str, int]:
    linhas = db.query(ChamadoCatinet.status, ChamadoCatinet.id).all()
    contagem = {STATUS_PENDENTE: 0, STATUS_APROVADO: 0, STATUS_DECLINADO: 0}
    for status, _ in linhas:
        contagem[status] = contagem.get(status, 0) + 1
    return contagem


def _pendente_ou_erro(db: Session, chamado_id: int) -> ChamadoCatinet:
    chamado = db.get(ChamadoCatinet, chamado_id)
    if chamado is None:
        raise ValueError("Chamado não encontrado.")
    if chamado.status != STATUS_PENDENTE:
        # Outro operador pode ter decidido enquanto esta tela estava aberta.
        raise ValueError(f"Este chamado já foi {chamado.status.lower()}.")
    return chamado


def aprovar(db: Session, chamado_id: int, operador_id: int) -> str:
    """Cria a O.S. a partir do chamado e marca o chamado como Aprovado. Devolve o número.

    O que o chamado sabe vira campo da O.S.; o que ele NÃO sabe fica em branco para ser
    completado depois (modalidade, itens...). O setor só é preenchido se o departamento
    do chamado bater, pelo nome, com um setor do cadastro — nunca inventamos cadastro.
    """
    chamado = _pendente_ou_erro(db, chamado_id)

    def id_por_nome(modelo, nome: str | None) -> int | None:
        if not nome:
            return None
        pares = [(r.nome, r.id) for r in crud_dominio.listar(db, modelo)]
        return indexar(pares).get(normalizar(nome))

    setor_id = id_por_nome(Setor, chamado.departamento)
    agora = datetime.now()
    ordem = crud_os.criar(
        db,
        operador_id,
        {
            "data_abertura": agora.date(),
            "hora_abertura": agora.time().replace(second=0, microsecond=0),
            "processo_chamado": chamado.referencia,
            "responsavel": chamado.solicitante,
            "contato": chamado.telefone,
            "descricao": chamado.descricao,
            "setor_demandante_id": setor_id,
            "unidade_atendimento_id": setor_id,
            "meio_id": id_por_nome(Meio, MEIO_PADRAO),
            "classificacao_id": id_por_nome(Classificacao, CLASSIFICACAO_PADRAO),
            "peso_id": id_por_nome(Peso, PESO_PADRAO),
        },
    )
    chamado.status = STATUS_APROVADO
    chamado.decidido_por_id = operador_id
    chamado.decidido_em = agora
    chamado.os_id = ordem.id
    db.commit()
    return ordem.numero


def declinar(db: Session, chamado_id: int, operador_id: int) -> None:
    chamado = _pendente_ou_erro(db, chamado_id)
    chamado.status = STATUS_DECLINADO
    chamado.decidido_por_id = operador_id
    chamado.decidido_em = datetime.now()
    db.commit()
