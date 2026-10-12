"""Chamados capturados do CATINET, à espera da decisão do operador.

O scraper (services/catinet_scraper.py) lê a fila do CATINET e grava aqui, uma linha por
chamado, como "Pendente". O operador então APROVA (vira uma O.S.) ou DECLINA. A linha
fica guardada mesmo depois de decidida: é ela que impede o mesmo chamado de voltar na
próxima busca.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.database import Base
from models.mixins import TimestampMixin

if TYPE_CHECKING:
    from models.ordem_servico import OrdemServico

STATUS_PENDENTE = "Pendente"
STATUS_APROVADO = "Aprovado"
STATUS_DECLINADO = "Declinado"


class ChamadoCatinet(Base, TimestampMixin):
    __tablename__ = "chamado_catinet"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Referência que o humano lê no CATINET (ex.: R2484749). Única: é a chave de
    # "este chamado já foi capturado?".
    referencia: Mapped[str] = mapped_column(unique=True, index=True)
    evento_id: Mapped[int]  # id interno do CATINET (ex.: 7484749), usado na API
    data_registro: Mapped[datetime | None]
    solicitante: Mapped[str | None]
    telefone: Mapped[str | None]
    departamento: Mapped[str | None]
    item: Mapped[str | None]
    categoria: Mapped[str | None]
    descricao: Mapped[str | None]  # as "Notas" do chamado (texto livre)

    status: Mapped[str] = mapped_column(default=STATUS_PENDENTE, index=True)
    decidido_por_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    decidido_em: Mapped[datetime | None]
    os_id: Mapped[int | None] = mapped_column(ForeignKey("ordem_servico.id"))

    ordem: Mapped["OrdemServico | None"] = relationship()


class ConfigSistema(Base):
    """Configurações simples chave/valor (ex.: a URL da fila do CATINET).

    A SENHA nunca vem para cá: fica no cofre do Windows (keyring)."""

    __tablename__ = "config_sistema"

    chave: Mapped[str] = mapped_column(primary_key=True)
    valor: Mapped[str | None]
