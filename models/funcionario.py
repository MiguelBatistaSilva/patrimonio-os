"""Funcionários — a equipe que carrega/executa o serviço em campo.

Diferente de User: o funcionário NÃO acessa o sistema, não tem login. Ele só existe
para ser registrado na equipe de uma O.S. (ver tabela de junção os_equipe).
"""

from sqlalchemy.orm import Mapped, mapped_column

from services.database import Base


class Funcionario(Base):
    __tablename__ = "funcionario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str]
    ativo: Mapped[bool] = mapped_column(default=True)
