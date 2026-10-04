"""CRUD da Ordem de Serviço — a entidade central.

Além do CRUD, é aqui que mora a GERAÇÃO AUTOMÁTICA do número (numero) — o código de
negócio que o humano lê (ex.: H0001). O operador NUNCA digita esse número.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from models.ordem_servico import OrdemServico, OsEquipe, OsItem
from models.dominio import Modalidade
from models.funcionario import Funcionario
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
    itens: list[dict] | None = None,
) -> OrdemServico:
    """CREATE — gera o número sozinho, monta a equipe e os itens, e grava a O.S.

    - `dados`: os campos do formulário, já validados/convertidos pelo state.
    - `operador_id`: vem do usuário logado (não do formulário).
    - `funcionario_ids`: quem vai na equipe (N:N via os_equipe).
    - `itens`: bens movimentados/atendidos; cada item é um dict com as chaves
      tombo_ns/descricao (1:N via os_item). Opcional — a O.S. pode
      nascer sem nenhum item.
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
    # Mesma ideia para os itens: uma linha de os_item por dict. O ** espalha as chaves
    # (tombo_ns/descricao) direto no construtor do model.
    ordem.itens = [OsItem(**item) for item in (itens or [])]
    db.add(ordem)
    db.commit()
    return ordem


def criar_lote(db: Session, operador_id: int, ordens: list[dict]) -> list[OrdemServico]:
    """CREATE em lote — grava várias O.S. (com seus itens) numa só transação.

    `ordens`: lista de {"dados": {...campos da O.S....}, "itens": [{...}, ...]}.

    TUDO OU NADA: um único commit no fim. Se qualquer uma falhar, o rollback desfaz o
    lote inteiro — nunca fica metade das O.S. gravada e metade não.

    O flush() a cada O.S. é essencial: a sessão tem autoflush desligado, então sem ele
    o _proximo_numero não enxergaria a O.S. recém-adicionada e daria o MESMO número a
    todas (a coluna é única, o commit estouraria).
    """
    criadas = []
    try:
        for item in ordens:
            ordem = OrdemServico(
                numero=_proximo_numero(db),
                operador_id=operador_id,
                **item["dados"],
            )
            ordem.itens = [OsItem(**i) for i in item.get("itens", [])]
            db.add(ordem)
            db.flush()  # grava (ainda sem commit) para o próximo número sair certo
            criadas.append(ordem)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return criadas


def chamados_existentes(db: Session, chamados: list[str]) -> set[str]:
    """Dos Chamados informados, quais já existem em alguma O.S. (para o aviso de duplicidade)."""
    if not chamados:
        return set()
    linhas = (
        db.query(OrdemServico.processo_chamado)
        .filter(OrdemServico.processo_chamado.in_(chamados))
        .distinct()
        .all()
    )
    return {chamado for (chamado,) in linhas}


def atualizar(
    db: Session,
    os_id: int,
    dados: dict,
    funcionario_ids: list[int] | None = None,
    itens: list[dict] | None = None,
) -> OrdemServico:
    """UPDATE — corrige os dados de abertura de uma O.S. já existente.

    NÃO mexe em `numero`, `operador` nem no ciclo de vida (status/datas de conclusão):
    só nos campos que o formulário de edição oferece. Equipe e itens são SUBSTITUÍDOS
    por inteiro — ao reatribuir as listas, o cascade delete-orphan apaga as linhas
    antigas de os_equipe/os_item e grava as novas.
    """
    ordem = _obter_ou_erro(db, os_id)
    for campo, valor in dados.items():
        setattr(ordem, campo, valor)
    ordem.equipe = [OsEquipe(funcionario_id=fid) for fid in (funcionario_ids or [])]
    ordem.itens = [OsItem(**item) for item in (itens or [])]
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


def listar_para_exportacao(db: Session, data_de=None, data_ate=None) -> list[OrdemServico]:
    """READ para o CSV: as O.S. do período, com TUDO já carregado de uma vez.

    Por que não reusar o `listar` acima? Porque a exportação lê muitas O.S. e, de cada
    uma, o nome de 8 tabelas ligadas + equipe + itens. Do jeito preguiçoso (padrão do
    SQLAlchemy), cada um desses acessos vira uma consulta EXTRA por O.S. — é o clássico
    problema "N+1": 500 O.S. viram milhares de idas ao banco e o botão parece travado.

    As opções abaixo resolvem isso: `joinedload` traz as tabelas de 1-para-1 no mesmo
    SELECT (JOIN), e `selectinload` traz as listas (equipe/itens) numa segunda consulta
    só — em vez de uma por O.S.

    Ordem CRESCENTE (mais antiga primeiro), que é como se lê um relatório na planilha —
    ao contrário da tela de lista, que mostra as mais recentes em cima.
    """
    consulta = db.query(OrdemServico).options(
        joinedload(OrdemServico.operador),
        joinedload(OrdemServico.meio),
        joinedload(OrdemServico.tipo_veiculo),
        joinedload(OrdemServico.classificacao),
        joinedload(OrdemServico.modalidade),
        joinedload(OrdemServico.peso),
        joinedload(OrdemServico.setor_demandante),
        joinedload(OrdemServico.unidade_atendimento),
        selectinload(OrdemServico.equipe).joinedload(OsEquipe.funcionario),
        selectinload(OrdemServico.itens),
    )
    if data_de:
        consulta = consulta.filter(OrdemServico.data_abertura >= data_de)
    if data_ate:
        consulta = consulta.filter(OrdemServico.data_abertura <= data_ate)
    return consulta.order_by(OrdemServico.id).all()


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
#
# Todas aceitam um PERÍODO opcional (data_de/data_ate, sobre a data de ABERTURA).
# Sem período = desde sempre, que era o comportamento antes de o filtro existir.

def _periodo(consulta, data_de, data_ate):
    """Empilha o filtro de período numa consulta, ignorando as datas não informadas."""
    if data_de:
        consulta = consulta.filter(OrdemServico.data_abertura >= data_de)
    if data_ate:
        consulta = consulta.filter(OrdemServico.data_abertura <= data_ate)
    return consulta


def contagem_por_status(db: Session, data_de=None, data_ate=None) -> dict[str, int]:
    """Quantas O.S. há em cada status. SQL: GROUP BY status + COUNT.

    Devolve algo como {"Pendente": 3, "Concluída": 5, "Cancelada": 1}.
    Deixamos o banco contar — é muito mais rápido que trazer tudo e contar em Python.
    """
    consulta = db.query(OrdemServico.status, func.count(OrdemServico.id))
    linhas = _periodo(consulta, data_de, data_ate).group_by(OrdemServico.status).all()
    return {status: total for status, total in linhas}


def contagem_por_modalidade(
    db: Session, data_de=None, data_ate=None, limite: int | None = 8
) -> list[tuple[str, int]]:
    """Quantas O.S. por modalidade, da mais usada para a menos. (Ignora O.S. sem modalidade.)

    `limite` corta nas mais frequentes — o cadastro tem 22 modalidades e o gráfico com
    todas viraria uma lista interminável. Passe limite=None para trazer todas.
    """
    consulta = (
        db.query(Modalidade.nome, func.count(OrdemServico.id))
        .join(OrdemServico, OrdemServico.modalidade_id == Modalidade.id)
    )
    consulta = (
        _periodo(consulta, data_de, data_ate)
        .group_by(Modalidade.nome)
        .order_by(func.count(OrdemServico.id).desc())
    )
    if limite:
        consulta = consulta.limit(limite)
    return consulta.all()


def contagem_por_mes(db: Session, data_de=None, data_ate=None) -> list[tuple[int, int, int]]:
    """Quantas O.S. foram abertas em cada mês: [(ano, mês, quantidade), ...].

    `extract` puxa o ano e o mês da data direto no PostgreSQL, e o GROUP BY agrupa por
    eles. Sai em ordem cronológica — é o gráfico de "como estamos indo ao longo do tempo".
    """
    ano = func.extract("year", OrdemServico.data_abertura)
    mes = func.extract("month", OrdemServico.data_abertura)
    consulta = db.query(ano, mes, func.count(OrdemServico.id))
    linhas = _periodo(consulta, data_de, data_ate).group_by(ano, mes).order_by(ano, mes).all()
    # extract devolve número decimal no PostgreSQL; viramos int para a tela.
    return [(int(a), int(m), int(qtd)) for a, m, qtd in linhas]


def contagem_por_funcionario(
    db: Session, data_de=None, data_ate=None, limite: int = 12
) -> list[tuple[str, int]]:
    """Em quantas O.S. cada funcionário atuou — a carga de trabalho da equipe.

    Uma O.S. com 3 pessoas conta 1 para cada uma; então a soma daqui é MAIOR que o
    total de O.S. Isso é esperado: a pergunta aqui é "quanto cada um trabalhou".
    """
    consulta = (
        db.query(Funcionario.nome, func.count(OsEquipe.id))
        .join(OsEquipe, OsEquipe.funcionario_id == Funcionario.id)
        .join(OrdemServico, OrdemServico.id == OsEquipe.os_id)
    )
    return (
        _periodo(consulta, data_de, data_ate)
        .group_by(Funcionario.nome)
        .order_by(func.count(OsEquipe.id).desc())
        .limit(limite)
        .all()
    )


def tempo_medio_conclusao(db: Session, data_de=None, data_ate=None) -> float | None:
    """Média de dias entre abrir e concluir. None se nenhuma O.S. foi concluída ainda.

    No PostgreSQL, subtrair duas datas dá o número de dias — então o próprio banco
    calcula a média. Conta só o que está Concluída e tem data de conclusão gravada.
    """
    consulta = db.query(
        func.avg(OrdemServico.data_conclusao - OrdemServico.data_abertura)
    ).filter(
        OrdemServico.status == "Concluída",
        OrdemServico.data_conclusao.isnot(None),
    )
    media = _periodo(consulta, data_de, data_ate).scalar()
    return float(media) if media is not None else None


def total_itens(db: Session, data_de=None, data_ate=None) -> int:
    """Quantos bens foram movimentados no período (soma dos itens de todas as O.S.)."""
    consulta = db.query(func.count(OsItem.id)).join(
        OrdemServico, OrdemServico.id == OsItem.os_id
    )
    return _periodo(consulta, data_de, data_ate).scalar() or 0


def pendentes_mais_antigas(db: Session, limite: int = 8) -> list[OrdemServico]:
    """As O.S. Pendentes abertas há mais tempo — o que está parado esperando.

    NÃO respeita o filtro de período de propósito: uma pendência velha continua sendo
    um problema hoje, mesmo que tenha sido aberta fora do período que o chefe está
    olhando. É a lista de "não deixe isso esquecido".
    """
    return (
        db.query(OrdemServico)
        .options(
            joinedload(OrdemServico.modalidade),
            joinedload(OrdemServico.setor_demandante),
        )
        .filter(OrdemServico.status == "Pendente")
        .order_by(OrdemServico.data_abertura)
        .limit(limite)
        .all()
    )
