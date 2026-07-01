"""CRUD genérico das tabelas de domínio.

As 6 tabelas de domínio (Meio, Classificacao, Peso, TipoVeiculo, Modalidade, Setor)
têm EXATAMENTE a mesma forma — id + nome único + ativo —, herdada do DomainTableMixin.
Como a forma é idêntica, UMA função serve para todas: passamos a classe do model
(Model) como argumento. Isso é só possível porque a operação não depende do "o que é",
só do formato comum — mais um motivo para crud/ ser separado de models/.

C-R-U-D, cada letra vira uma função:
- Create -> criar
- Read   -> listar
- Update -> editar
- Delete -> desativar  (soft delete: marca ativo=False; NÃO apaga de verdade, para não
            quebrar O.S. antigas que apontam para este valor)

Erros previsíveis (nome vazio, nome duplicado) viram ValueError com mensagem amigável,
para a tela apenas mostrar o texto ao usuário.
"""

from sqlalchemy.orm import Session

from models.dominio import (
    Meio,
    Classificacao,
    Peso,
    TipoVeiculo,
    Modalidade,
    Setor,
)
from models.funcionario import Funcionario

# Registro das listas que o admin mantém: chave -> (rótulo exibido, classe do model).
# A ordem aqui é a ordem em que as abas aparecem na tela. É a única "lista mestra":
# para ter uma nova aba de cadastro, basta acrescentar uma linha aqui.
#
# Nota: "funcionario" NÃO é uma tabela de domínio (é gente que executa o serviço, não
# loga no sistema). Mas como tem a MESMA forma (id + nome + ativo), o CRUD genérico,
# o state e a tela funcionam para ele sem alterações — um ganho do design genérico.
DOMINIOS: dict[str, tuple] = {
    "modalidade": ("Modalidade", Modalidade),
    "setor": ("Setor", Setor),
    "tipo_veiculo": ("Tipo de Veículo", TipoVeiculo),
    "peso": ("Peso", Peso),
    "classificacao": ("Classificação", Classificacao),
    "meio": ("Meio", Meio),
    "funcionario": ("Funcionários", Funcionario),
}


def listar(db: Session, Model, incluir_inativos: bool = False) -> list:
    """READ — devolve os registros, em ordem alfabética. Por padrão, só os ativos."""
    consulta = db.query(Model)
    if not incluir_inativos:
        consulta = consulta.filter(Model.ativo.is_(True))
    return consulta.order_by(Model.nome).all()


def criar(db: Session, Model, nome: str):
    """CREATE — cria um registro novo. Se já existir um inativo com esse nome, reativa."""
    nome = nome.strip()
    if not nome:
        raise ValueError("O nome não pode ficar vazio.")

    existente = db.query(Model).filter(Model.nome == nome).first()
    if existente is not None:
        if existente.ativo:
            raise ValueError(f"Já existe '{nome}'.")
        existente.ativo = True  # estava desativado -> reativa em vez de duplicar
        db.commit()
        return existente

    novo = Model(nome=nome)
    db.add(novo)
    db.commit()
    return novo


def editar(db: Session, Model, item_id: int, novo_nome: str):
    """UPDATE — renomeia um registro existente."""
    novo_nome = novo_nome.strip()
    if not novo_nome:
        raise ValueError("O nome não pode ficar vazio.")

    item = db.get(Model, item_id)
    if item is None:
        raise ValueError("Registro não encontrado.")

    # Não deixa dois registros com o mesmo nome (a coluna é única no banco também).
    colisao = db.query(Model).filter(Model.nome == novo_nome, Model.id != item_id).first()
    if colisao is not None:
        raise ValueError(f"Já existe outro registro chamado '{novo_nome}'.")

    item.nome = novo_nome
    db.commit()
    return item


def desativar(db: Session, Model, item_id: int):
    """DELETE (soft) — marca ativo=False. Some dos formulários novos; histórico intacto."""
    item = db.get(Model, item_id)
    if item is None:
        raise ValueError("Registro não encontrado.")
    item.ativo = False
    db.commit()
    return item


def reativar(db: Session, Model, item_id: int):
    """Volta um registro desativado para ativo (par do desativar)."""
    item = db.get(Model, item_id)
    if item is None:
        raise ValueError("Registro não encontrado.")
    item.ativo = True
    db.commit()
    return item
