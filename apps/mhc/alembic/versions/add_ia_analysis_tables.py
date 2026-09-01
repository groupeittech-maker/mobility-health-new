"""Add IA analysis tables

Revision ID: add_ia_analysis
Revises: merge_all_heads
Create Date: 2025-01-15 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_ia_analysis'
down_revision = 'merge_all_heads'  # Dernière migration (merge de toutes les branches)
branch_labels = None
depends_on = None


def upgrade():
    # S'assurer que la table questionnaires existe (créée par ad587bb061e5 sur une autre branche)
    op.execute("""
        CREATE TABLE IF NOT EXISTS questionnaires (
            id SERIAL NOT NULL PRIMARY KEY,
            souscription_id INTEGER NOT NULL REFERENCES souscriptions(id) ON DELETE CASCADE,
            type_questionnaire VARCHAR(20) NOT NULL,
            version INTEGER NOT NULL,
            reponses JSON NOT NULL,
            statut VARCHAR(20) NOT NULL,
            notes TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_questionnaires_id ON questionnaires (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_questionnaires_souscription_id ON questionnaires (souscription_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_questionnaires_type_questionnaire ON questionnaires (type_questionnaire)")

    # Créer la table ia_analyses
    op.create_table(
        'ia_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('souscription_id', sa.Integer(), nullable=True),
        sa.Column('questionnaire_id', sa.Integer(), nullable=True),
        sa.Column('demande_id', sa.String(length=100), nullable=False),
        sa.Column('client_nom', sa.String(length=200), nullable=False),
        sa.Column('client_prenom', sa.String(length=200), nullable=False),
        sa.Column('client_pays', sa.String(length=100), nullable=True),
        sa.Column('client_email', sa.String(length=255), nullable=True),
        sa.Column('probabilite_acceptation', sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column('probabilite_fraude', sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column('probabilite_confiance_assureur', sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column('score_coherence', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('score_risque', sa.Numeric(precision=5, scale=3), nullable=False),
        sa.Column('score_confiance', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('avis', sa.String(length=50), nullable=False),
        sa.Column('niveau_risque', sa.String(length=30), nullable=False),
        sa.Column('niveau_fraude', sa.String(length=30), nullable=False),
        sa.Column('niveau_confiance_assureur', sa.String(length=30), nullable=False),
        sa.Column('facteurs_risque', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('signaux_fraude', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('incoherences', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('infos_personnelles', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('infos_sante', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('infos_voyage', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('resultat_complet', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('date_analyse', sa.DateTime(), nullable=False),
        sa.Column('confiance_ocr', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('nb_documents_analyses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('commentaire', sa.Text(), nullable=True),
        sa.Column('message_ia', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['souscription_id'], ['souscriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['questionnaire_id'], ['questionnaires.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('demande_id')
    )
    
    # Index pour ia_analyses
    op.create_index(op.f('ix_ia_analyses_id'), 'ia_analyses', ['id'], unique=False)
    op.create_index(op.f('ix_ia_analyses_demande_id'), 'ia_analyses', ['demande_id'], unique=True)
    op.create_index(op.f('ix_ia_analyses_souscription_id'), 'ia_analyses', ['souscription_id'], unique=False)
    op.create_index(op.f('ix_ia_analyses_questionnaire_id'), 'ia_analyses', ['questionnaire_id'], unique=False)
    op.create_index(op.f('ix_ia_analyses_client_nom'), 'ia_analyses', ['client_nom'], unique=False)
    op.create_index(op.f('ix_ia_analyses_client_prenom'), 'ia_analyses', ['client_prenom'], unique=False)
    op.create_index(op.f('ix_ia_analyses_client_pays'), 'ia_analyses', ['client_pays'], unique=False)
    op.create_index(op.f('ix_ia_analyses_client_email'), 'ia_analyses', ['client_email'], unique=False)
    op.create_index(op.f('ix_ia_analyses_avis'), 'ia_analyses', ['avis'], unique=False)
    op.create_index(op.f('ix_ia_analyses_date_analyse'), 'ia_analyses', ['date_analyse'], unique=False)
    op.create_index('idx_ia_analyses_avis_scores', 'ia_analyses', ['avis', 'probabilite_acceptation', 'probabilite_fraude'], unique=False)
    op.create_index('idx_ia_analyses_date_avis', 'ia_analyses', ['date_analyse', 'avis'], unique=False)
    op.create_index('idx_ia_analyses_client', 'ia_analyses', ['client_nom', 'client_prenom'], unique=False)
    
    # Créer la table ia_analysis_assureurs
    op.create_table(
        'ia_analysis_assureurs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analyse_id', sa.Integer(), nullable=False),
        sa.Column('assureur_id', sa.Integer(), nullable=False),
        sa.Column('notifie', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('date_notification', sa.DateTime(), nullable=True),
        sa.Column('methode_notification', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['analyse_id'], ['ia_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assureur_id'], ['assureurs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Index pour ia_analysis_assureurs
    op.create_index(op.f('ix_ia_analysis_assureurs_id'), 'ia_analysis_assureurs', ['id'], unique=False)
    op.create_index(op.f('ix_ia_analysis_assureurs_analyse_id'), 'ia_analysis_assureurs', ['analyse_id'], unique=False)
    op.create_index(op.f('ix_ia_analysis_assureurs_assureur_id'), 'ia_analysis_assureurs', ['assureur_id'], unique=False)
    op.create_index(op.f('ix_ia_analysis_assureurs_notifie'), 'ia_analysis_assureurs', ['notifie'], unique=False)
    op.create_index('idx_ia_analysis_assureur_unique', 'ia_analysis_assureurs', ['analyse_id', 'assureur_id'], unique=True)
    
    # Créer la table ia_analysis_documents
    op.create_table(
        'ia_analysis_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('analyse_id', sa.Integer(), nullable=False),
        sa.Column('nom_fichier', sa.String(length=255), nullable=False),
        sa.Column('type_document', sa.String(length=100), nullable=True),
        sa.Column('type_fichier', sa.String(length=50), nullable=True),
        sa.Column('confiance_ocr', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('texte_extrait', sa.Text(), nullable=True),
        sa.Column('est_expire', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('qualite_ok', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('est_complet', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('est_coherent', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('message_expiration', sa.Text(), nullable=True),
        sa.Column('message_qualite', sa.Text(), nullable=True),
        sa.Column('message_completude', sa.Text(), nullable=True),
        sa.Column('message_coherence', sa.Text(), nullable=True),
        sa.Column('resultat_document', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['analyse_id'], ['ia_analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Index pour ia_analysis_documents
    op.create_index(op.f('ix_ia_analysis_documents_id'), 'ia_analysis_documents', ['id'], unique=False)
    op.create_index(op.f('ix_ia_analysis_documents_analyse_id'), 'ia_analysis_documents', ['analyse_id'], unique=False)


def downgrade():
    # Supprimer les tables en ordre inverse
    op.drop_index(op.f('ix_ia_analysis_documents_analyse_id'), table_name='ia_analysis_documents')
    op.drop_index(op.f('ix_ia_analysis_documents_id'), table_name='ia_analysis_documents')
    op.drop_table('ia_analysis_documents')
    
    op.drop_index('idx_ia_analysis_assureur_unique', table_name='ia_analysis_assureurs')
    op.drop_index(op.f('ix_ia_analysis_assureurs_notifie'), table_name='ia_analysis_assureurs')
    op.drop_index(op.f('ix_ia_analysis_assureurs_assureur_id'), table_name='ia_analysis_assureurs')
    op.drop_index(op.f('ix_ia_analysis_assureurs_analyse_id'), table_name='ia_analysis_assureurs')
    op.drop_index(op.f('ix_ia_analysis_assureurs_id'), table_name='ia_analysis_assureurs')
    op.drop_table('ia_analysis_assureurs')
    
    op.drop_index('idx_ia_analyses_client', table_name='ia_analyses')
    op.drop_index('idx_ia_analyses_date_avis', table_name='ia_analyses')
    op.drop_index('idx_ia_analyses_avis_scores', table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_date_analyse'), table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_avis'), table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_client_email'), table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_client_pays'), table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_client_prenom'), table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_client_nom'), table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_questionnaire_id'), table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_souscription_id'), table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_demande_id'), table_name='ia_analyses')
    op.drop_index(op.f('ix_ia_analyses_id'), table_name='ia_analyses')
    op.drop_table('ia_analyses')

