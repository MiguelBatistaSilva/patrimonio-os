"""Ambiente do Alembic — diz a ele COMO se conectar e QUAL é o esquema-alvo.

- DATABASE_URL vem do .env (mesma do app), com o ?sslmode=disable já embutido.
- target_metadata = Base.metadata: o "mapa" de todas as tabelas. Importamos o pacote
  models inteiro para que TODAS as tabelas se registrem nesse mapa antes da comparação
  do autogenerate.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine
from alembic import context

from services.database import Base, DATABASE_URL
import models  # noqa: F401  -> registra todos os models em Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline: gera o SQL sem conectar (não usamos no dia a dia, mas o Alembic pede)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online: conecta de verdade e aplica as migrations."""
    connectable = create_engine(DATABASE_URL)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
