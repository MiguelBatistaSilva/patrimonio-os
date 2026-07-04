"""remove coluna causa e cria tabela os_item

Revision ID: b7e1c4a9d260
Revises: 3c477cc2169d
Create Date: 2026-07-04

Escrita à mão (não pelo autogenerate) para ficar legível. Faz duas coisas:
  1. Cria a tabela os_item (os itens que antes eram preenchidos à mão no papel).
  2. Remove a coluna 'causa' de ordem_servico (não é mais usada — o texto antigo é
     descartado, conforme combinado com o cliente).
"""
from alembic import op
import sqlalchemy as sa


# identificadores usados pelo Alembic para encadear as migrations
revision = 'b7e1c4a9d260'
down_revision = '3c477cc2169d'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Nova tabela de itens (1:N com ordem_servico). Cada linha = um bem.
    op.create_table(
        'os_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('os_id', sa.Integer(), nullable=False),
        sa.Column('tombo_ns', sa.String(), nullable=True),
        sa.Column('descricao', sa.String(), nullable=True),
        sa.Column('origem', sa.String(), nullable=True),
        sa.Column('destino', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['os_id'], ['ordem_servico.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2) A coluna 'causa' deixou de ser usada. Removê-la apaga o texto antigo — o cliente
    #    confirmou que pode. (Se um dia precisar preservar, faça um backup ANTES de subir.)
    op.drop_column('ordem_servico', 'causa')


def downgrade():
    # Desfaz na ordem inversa: recria a coluna 'causa' (vazia — os dados antigos já foram)
    # e remove a tabela os_item.
    op.add_column('ordem_servico', sa.Column('causa', sa.String(), nullable=True))
    op.drop_table('os_item')
