"""Usuários do sistema — operadores e chefe(admin). Estes FAZEM login.

Decisão de modelagem: "operador" não é uma tabela separada. Operador é um User com
role="operador". O chefe é um User com role="admin".
"""

from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column

from services.database import Base
from models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)  # CPF (login)
    # Guardamos o HASH da senha (bcrypt), nunca a senha em texto puro.
    password_hash: Mapped[str]
    nome: Mapped[str]
    role: Mapped[str] = mapped_column(default="operador")  # "operador" | "admin"
    ativo: Mapped[bool] = mapped_column(default=True)
    # True = senha provisória (definida pelo admin); o usuário deve trocá-la no 1º acesso.
    #   default=True   -> todo usuário criado pelo admin nasce provisório.
    #   server_default=false -> as linhas que JÁ existem (você) recebem False na migration,
    #                           ou seja, não são forçadas a trocar.
    senha_provisoria: Mapped[bool] = mapped_column(default=True, server_default=text("false"))
