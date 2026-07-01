"""Tabelas de domínio — listas que o admin/chefe edita (CRUD).

Todas têm a mesma forma (id, nome, ativo), então cada uma é só duas linhas: herda de
Base (para virar tabela de verdade) e de DomainTableMixin (que traz as colunas comuns).
"""

from services.database import Base
from models.mixins import DomainTableMixin


class Meio(Base, DomainTableMixin):
    """Como a demanda chegou (ex.: Chamado)."""

    __tablename__ = "meio"


class Classificacao(Base, DomainTableMixin):
    """Normal, Urgente..."""

    __tablename__ = "classificacao"


class Peso(Base, DomainTableMixin):
    """Escala de peso/prioridade (1, 2, 3, 5, Normal — a confirmar com o cliente)."""

    __tablename__ = "peso"


class TipoVeiculo(Base, DomainTableMixin):
    """Grande, Médio, Pequeno."""

    __tablename__ = "tipo_veiculo"


class Modalidade(Base, DomainTableMixin):
    """Recolhimento, Entrega, Reparo, Movimentação... (~22 valores)."""

    __tablename__ = "modalidade"


class Setor(Base, DomainTableMixin):
    """Serve tanto para o setor que pediu quanto para a unidade que atendeu."""

    __tablename__ = "setor"
