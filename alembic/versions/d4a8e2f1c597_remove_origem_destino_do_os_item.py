"""remove origem e destino de os_item

Revision ID: d4a8e2f1c597
Revises: b7e1c4a9d260
Create Date: 2026-10-04

Origem e Destino saíram do formulário, do detalhe e da impressão logo após a criação
dos itens, e nunca mais foram preenchidos. Aqui as colunas saem do banco.
"""
from alembic import op
import sqlalchemy as sa


# identificadores usados pelo Alembic para encadear as migrations
revision = 'd4a8e2f1c597'
down_revision = 'b7e1c4a9d260'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('os_item', 'origem')
    op.drop_column('os_item', 'destino')


def downgrade():
    # Recria as colunas (vazias — o que havia nelas já foi descartado no upgrade).
    op.add_column('os_item', sa.Column('destino', sa.String(), nullable=True))
    op.add_column('os_item', sa.Column('origem', sa.String(), nullable=True))
