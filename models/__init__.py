"""Reúne todos os modelos num só lugar.

Importar tudo aqui garante que, ao carregar o pacote `models`, TODAS as tabelas se
registrem em Base.metadata. Sem isso, criar o schema (ou gerar migrations) deixaria
de fora as tabelas que ninguém importou explicitamente.
"""

from models.user import User
from models.funcionario import Funcionario
from models.dominio import (
    Meio,
    Classificacao,
    Peso,
    TipoVeiculo,
    Modalidade,
    Setor,
)
from models.ordem_servico import OrdemServico, OsEquipe, OsItem

__all__ = [
    "User",
    "Funcionario",
    "Meio",
    "Classificacao",
    "Peso",
    "TipoVeiculo",
    "Modalidade",
    "Setor",
    "OrdemServico",
    "OsEquipe",
    "OsItem",
]
