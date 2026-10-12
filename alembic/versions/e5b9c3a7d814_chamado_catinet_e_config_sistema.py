"""cria chamado_catinet e config_sistema

Revision ID: e5b9c3a7d814
Revises: d4a8e2f1c597
Create Date: 2026-10-12

chamado_catinet guarda os chamados lidos do CATINET até o operador aprovar/declinar.
config_sistema guarda configurações simples (URL da fila do CATINET).
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5b9c3a7d814'
down_revision = 'd4a8e2f1c597'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'chamado_catinet',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('referencia', sa.String(), nullable=False),
        sa.Column('evento_id', sa.Integer(), nullable=False),
        sa.Column('data_registro', sa.DateTime(), nullable=True),
        sa.Column('solicitante', sa.String(), nullable=True),
        sa.Column('telefone', sa.String(), nullable=True),
        sa.Column('departamento', sa.String(), nullable=True),
        sa.Column('item', sa.String(), nullable=True),
        sa.Column('categoria', sa.String(), nullable=True),
        sa.Column('descricao', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('decidido_por_id', sa.Integer(), nullable=True),
        sa.Column('decidido_em', sa.DateTime(), nullable=True),
        sa.Column('os_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['decidido_por_id'], ['user.id']),
        sa.ForeignKeyConstraint(['os_id'], ['ordem_servico.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chamado_catinet_referencia'), 'chamado_catinet', ['referencia'], unique=True)
    op.create_index(op.f('ix_chamado_catinet_status'), 'chamado_catinet', ['status'], unique=False)
    op.create_table(
        'config_sistema',
        sa.Column('chave', sa.String(), nullable=False),
        sa.Column('valor', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('chave'),
    )


def downgrade():
    op.drop_table('config_sistema')
    op.drop_index(op.f('ix_chamado_catinet_status'), table_name='chamado_catinet')
    op.drop_index(op.f('ix_chamado_catinet_referencia'), table_name='chamado_catinet')
    op.drop_table('chamado_catinet')
