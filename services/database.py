"""Fundação da camada de dados.

Aqui ficam os três objetos que todo o resto do sistema usa para falar com o banco:
- engine        -> a "tomada" para o PostgreSQL (sabe a URL, gerencia conexões)
- SessionLocal  -> uma fábrica de sessões (cada operação abre uma, usa e fecha)
- Base          -> a classe-mãe de todos os modelos (o catálogo de tabelas)
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Lê o arquivo .env (que NÃO vai para o git) e injeta as variáveis no ambiente.
load_dotenv()

# A string de conexão fica no .env para não vazar senha no código.
# Formato: postgresql+psycopg2://usuario:senha@host:porta/banco
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não definida. Crie um arquivo .env na raiz do projeto "
        "(use o .env.example como modelo)."
    )

# echo=True faz o SQLAlchemy imprimir o SQL gerado — ótimo para aprender o que ele faz
# por baixo dos panos. Troque para False quando cansar de ver os logs.
engine = create_engine(DATABASE_URL, echo=True)

# Fábrica de sessões. Cada handler do app fará:  db = SessionLocal() ... db.close()
# expire_on_commit=False deixa os objetos utilizáveis depois do commit (prático na UI).
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe-mãe de todos os modelos.

    Todo modelo que herdar de Base é automaticamente registrado em Base.metadata,
    que é o "mapa" de todas as tabelas — usado para criar o schema e nas migrations.
    """

    pass
