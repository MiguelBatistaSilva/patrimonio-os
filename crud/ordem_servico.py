"""CRUD da Ordem de Serviço — a entidade central.

Além do CRUD, é aqui que mora a GERAÇÃO AUTOMÁTICA do número (numero) — o código de
negócio que o humano lê (ex.: H0001). O operador NUNCA digita esse número.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.ordem_servico import OrdemServico, OsEquipe
from models.dominio import Modalidade
from config import OS_PREFIXO, OS_DIGITOS


def _proximo_numero(db: Session) -> str:
    """Calcula o próximo número: prefixo + contador preenchido com zeros à esquerda.

    Estratégia: pega o MAIOR número já gravado com este prefixo e soma 1. Como os
    números têm largura fixa (zeros à esquerda), ordenar como texto já dá a ordem certa.

    Nota: sob muitos usuários criando O.S. ao mesmo tempo, o ideal seria uma SEQUENCE
    do PostgreSQL (garante unicidade sob concorrência). Para o uso atual, isto basta —
    e a coluna `numero` é única no banco, então uma colisão jamais passaria batida.
    """
    ultimo = (
        db.query(OrdemServico.numero)
        .filter(OrdemServico.numero.like(f"{OS_PREFIXO}%"))
        .order_by(OrdemServico.numero.desc())
        .first()
    )
    if ultimo is None:
        proximo = 1
    else:
        proximo = int(ultimo[0][len(OS_PREFIXO):]) + 1  # tira o prefixo, vira int, +1
    return f"{OS_PREFIXO}{proximo:0{OS_DIGITOS}d}"


def criar(
    db: Session,
    operador_id: int,
    dados: dict,
    funcionario_ids: list[int] | None = None,
) -> OrdemServico:
    """CREATE — gera o número sozinho, monta a equipe e grava a O.S.

    - `dados`: os campos do formulário, já validados/convertidos pelo state.
    - `operador_id`: vem do usuário logado (não do formulário).
    - `funcionario_ids`: quem vai na equipe (N:N via os_equipe).
    O status nasce "Pendente" (default no model).
    """
    ordem = OrdemServico(
        numero=_proximo_numero(db),
        operador_id=operador_id,
        **dados,
    )
    # Monta os vínculos com a equipe usando o relacionamento: o SQLAlchemy cuida de
    # gravar as linhas de os_equipe com o os_id certo (cascade configurado no model).
    ordem.equipe = [
        OsEquipe(funcionario_id=fid) for fid in (funcionario_ids or [])
    ]
    db.add(ordem)
    db.commit()
    return ordem


def listar(
    db: Session,
    status: str | None = None,
    modalidade_id: int | None = None,
    data_de=None,
    data_ate=None,
) -> list[OrdemServico]:
    """READ — O.S. mais recentes primeiro, com filtros OPCIONAIS.

    Vamos "empilhando" filtros na consulta: cada argumento que vier preenchido vira um
    .filter() a mais. Os que ficarem None são ignorados — então listar(db) sozinho
    devolve tudo. O banco faz o trabalho; nunca filtramos em Python.
    """
    consulta = db.query(OrdemServico)
    if status:
        consulta = consulta.filter(OrdemServico.status == status)
    if modalidade_id:
        consulta = consulta.filter(OrdemServico.modalidade_id == modalidade_id)
    if data_de:
        consulta = consulta.filter(OrdemServico.data_abertura >= data_de)
    if data_ate:
        consulta = consulta.filter(OrdemServico.data_abertura <= data_ate)
    return consulta.order_by(OrdemServico.id.desc()).all()


def obter(db: Session, os_id: int) -> OrdemServico | None:
    """READ de uma só — usada depois na tela de detalhe/impressão."""
    return db.get(OrdemServico, os_id)


def _obter_ou_erro(db: Session, os_id: int) -> OrdemServico:
    ordem = db.get(OrdemServico, os_id)
    if ordem is None:
        raise ValueError("Ordem de Serviço não encontrada.")
    return ordem


def concluir(db: Session, os_id: int, data_conclusao, hora_inicial=None, hora_final=None):
    """Marca como Concluída e grava o que o chefe transcreveu do papel.

    A data é obrigatória; as horas são opcionais (o papel às vezes volta incompleto).
    """
    ordem = _obter_ou_erro(db, os_id)
    ordem.status = "Concluída"
    ordem.data_conclusao = data_conclusao
    ordem.hora_inicial = hora_inicial
    ordem.hora_final = hora_final
    db.commit()
    return ordem


def cancelar(db: Session, os_id: int):
    """Marca como Cancelada."""
    ordem = _obter_ou_erro(db, os_id)
    ordem.status = "Cancelada"
    db.commit()
    return ordem


def reabrir(db: Session, os_id: int):
    """Volta para Pendente e limpa os dados de conclusão (caso o chefe tenha errado)."""
    ordem = _obter_ou_erro(db, os_id)
    ordem.status = "Pendente"
    ordem.data_conclusao = None
    ordem.hora_inicial = None
    ordem.hora_final = None
    db.commit()
    return ordem


# ── Agregações para o dashboard (contar e agrupar no próprio banco) ──

def contagem_por_status(db: Session) -> dict[str, int]:
    """Quantas O.S. há em cada status. SQL: GROUP BY status + COUNT.

    Devolve algo como {"Pendente": 3, "Concluída": 5, "Cancelada": 1}.
    Deixamos o banco contar — é muito mais rápido que trazer tudo e contar em Python.
    """
    linhas = (
        db.query(OrdemServico.status, func.count(OrdemServico.id))
        .group_by(OrdemServico.status)
        .all()
    )
    return {status: total for status, total in linhas}


def contagem_por_modalidade(db: Session) -> list[tuple[str, int]]:
    """Quantas O.S. por modalidade, da mais usada para a menos. (Ignora O.S. sem modalidade.)"""
    return (
        db.query(Modalidade.nome, func.count(OrdemServico.id))
        .join(OrdemServico, OrdemServico.modalidade_id == Modalidade.id)
        .group_by(Modalidade.nome)
        .order_by(func.count(OrdemServico.id).desc())
        .all()
    )
