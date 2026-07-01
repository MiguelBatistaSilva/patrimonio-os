"""Pedaços reutilizáveis de modelo (mixins).

Um "mixin" é uma classe que NÃO vira tabela sozinha — ela só empresta colunas/comportamento
para os modelos que a herdam. Serve para não repetir as mesmas colunas em vários lugares.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adiciona created_at / updated_at a qualquer modelo.

    server_default=func.now() -> o PRÓPRIO banco preenche a data na inserção.
    onupdate=func.now()       -> atualiza a data sozinho a cada UPDATE.
    """

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class DomainTableMixin:
    """Forma comum das tabelas de domínio: id + nome único + ativo (soft delete).

    Em vez de apagar um registro já usado (o que quebraria O.S. antigas), marcamos
    ativo=False: ele some dos formulários novos, mas o histórico continua íntegro.
    """

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(unique=True)
    ativo: Mapped[bool] = mapped_column(default=True)
