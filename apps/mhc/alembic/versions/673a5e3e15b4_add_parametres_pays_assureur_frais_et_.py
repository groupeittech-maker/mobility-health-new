"""add parametres pays assureur frais et taxes

Revision ID: 673a5e3e15b4
Revises: f225281bd6f1
Create Date: 2026-09-11 12:45:44.002101

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '673a5e3e15b4'
down_revision = 'f225281bd6f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('parametres_pays_assureur',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pays_assureur', sa.String(length=100), nullable=False),
        sa.Column('frais_services_pct', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('actif', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parametres_pays_assureur_id'), 'parametres_pays_assureur', ['id'], unique=False)
    op.create_index(op.f('ix_parametres_pays_assureur_pays_assureur'), 'parametres_pays_assureur', ['pays_assureur'], unique=True)
    op.create_table('taxes_pays_assureur',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parametre_pays_assureur_id', sa.Integer(), nullable=False),
        sa.Column('nom', sa.String(length=100), nullable=False),
        sa.Column('taux_pct', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('actif', sa.Boolean(), nullable=False),
        sa.Column('ordre_affichage', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parametre_pays_assureur_id'], ['parametres_pays_assureur.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_taxes_pays_assureur_id'), 'taxes_pays_assureur', ['id'], unique=False)
    op.create_index(op.f('ix_taxes_pays_assureur_parametre_pays_assureur_id'), 'taxes_pays_assureur', ['parametre_pays_assureur_id'], unique=False)
    op.add_column('souscriptions', sa.Column('taxes', sa.JSON(), nullable=True))
    op.add_column('souscriptions', sa.Column('taxes_total', sa.Numeric(precision=12, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column('souscriptions', 'taxes_total')
    op.drop_column('souscriptions', 'taxes')
    op.drop_index(op.f('ix_taxes_pays_assureur_parametre_pays_assureur_id'), table_name='taxes_pays_assureur')
    op.drop_index(op.f('ix_taxes_pays_assureur_id'), table_name='taxes_pays_assureur')
    op.drop_table('taxes_pays_assureur')
    op.drop_index(op.f('ix_parametres_pays_assureur_pays_assureur'), table_name='parametres_pays_assureur')
    op.drop_index(op.f('ix_parametres_pays_assureur_id'), table_name='parametres_pays_assureur')
    op.drop_table('parametres_pays_assureur')
