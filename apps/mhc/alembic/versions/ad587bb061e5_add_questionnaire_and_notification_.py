"""add_questionnaire_and_notification_tables

Revision ID: ad587bb061e5
Revises: d103085117c7
Create Date: 2025-11-23 13:44:37.358533

Creates questionnaires and notifications. If souscriptions table does not exist
(linear chain without e8f9a0b1c2d3), creates it and its dependencies first.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'ad587bb061e5'
down_revision = 'e8f9a0b1c2d3'  # run after souscriptions (was d103085117c7 to fix fresh DB order)
branch_labels = None
depends_on = None


def _ensure_souscriptions_and_deps(conn, existing):
    """Create souscriptions and dependency tables if missing (PostgreSQL)."""
    enums = [
        ("statutsouscription", ["en_attente", "pending", "active", "suspendue", "resiliee", "expiree"]),
        ("statutprojetvoyage", ["en_planification", "confirme", "en_cours", "termine", "annule"]),
        ("questionnairetype", ["short", "long"]),
        ("clerepartition", ["par_personne", "par_groupe", "par_duree", "par_destination", "fixe"]),
    ]
    for name, values in enums:
        try:
            conn.execute(sa.text("CREATE TYPE {} AS ENUM ({})".format(name, ", ".join("'{}'".format(v) for v in values))))
        except Exception:
            pass
    statutsouscription = postgresql.ENUM("en_attente", "pending", "active", "suspendue", "resiliee", "expiree", name="statutsouscription", create_type=False)
    statutprojetvoyage = postgresql.ENUM("en_planification", "confirme", "en_cours", "termine", "annule", name="statutprojetvoyage", create_type=False)
    questionnairetype = postgresql.ENUM("short", "long", name="questionnairetype", create_type=False)
    clerepartition = postgresql.ENUM("par_personne", "par_groupe", "par_duree", "par_destination", "fixe", name="clerepartition", create_type=False)

    if "assureurs" not in existing:
        op.create_table("assureurs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nom", sa.String(200), nullable=False),
            sa.Column("pays", sa.String(100), nullable=False),
            sa.Column("logo_url", sa.String(500), nullable=True),
            sa.Column("adresse", sa.String(255), nullable=True),
            sa.Column("telephone", sa.String(50), nullable=True),
            sa.Column("agent_comptable_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["agent_comptable_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("nom"),
        )
        op.create_index("ix_assureurs_id", "assureurs", ["id"], unique=False)
        op.create_index("ix_assureurs_nom", "assureurs", ["nom"], unique=True)
        op.create_index("ix_assureurs_agent_comptable_id", "assureurs", ["agent_comptable_id"], unique=False)
        existing.append("assureurs")
    if "destination_countries" not in existing:
        op.create_table("destination_countries",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(10), nullable=False),
            sa.Column("nom", sa.String(200), nullable=False),
            sa.Column("est_actif", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("ordre_affichage", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("notes", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("code"),
        )
        op.create_index("ix_destination_countries_id", "destination_countries", ["id"], unique=False)
        op.create_index("ix_destination_countries_code", "destination_countries", ["code"], unique=True)
        op.create_index("ix_destination_countries_nom", "destination_countries", ["nom"], unique=False)
        existing.append("destination_countries")
    if "destination_cities" not in existing:
        op.create_table("destination_cities",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("pays_id", sa.Integer(), nullable=False),
            sa.Column("nom", sa.String(200), nullable=False),
            sa.Column("est_actif", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("ordre_affichage", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("notes", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["pays_id"], ["destination_countries.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_destination_cities_id", "destination_cities", ["id"], unique=False)
        op.create_index("ix_destination_cities_nom", "destination_cities", ["nom"], unique=False)
        op.create_index("ix_destination_cities_pays_id", "destination_cities", ["pays_id"], unique=False)
        existing.append("destination_cities")
    if "produits_assurance" not in existing:
        op.create_table("produits_assurance",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("nom", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("version", sa.String(20), nullable=True),
            sa.Column("est_actif", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("assureur", sa.String(200), nullable=True),
            sa.Column("assureur_id", sa.Integer(), nullable=True),
            sa.Column("image_url", sa.String(500), nullable=True),
            sa.Column("cout", sa.Numeric(10, 2), nullable=False),
            sa.Column("currency", sa.String(10), nullable=True, server_default="XAF"),
            sa.Column("cle_repartition", clerepartition, nullable=False, server_default="fixe"),
            sa.Column("commission_assureur_pct", sa.Numeric(5, 2), nullable=True, server_default="30"),
            sa.Column("zones_geographiques", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("duree_min_jours", sa.Integer(), nullable=True),
            sa.Column("duree_max_jours", sa.Integer(), nullable=True),
            sa.Column("duree_validite_jours", sa.Integer(), nullable=True),
            sa.Column("reconduction_possible", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("couverture_multi_entrees", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("age_minimum", sa.Integer(), nullable=True),
            sa.Column("age_maximum", sa.Integer(), nullable=True),
            sa.Column("conditions_sante", sa.Text(), nullable=True),
            sa.Column("categories_assures", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("garanties", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("primes_generees", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("exclusions_generales", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column("conditions", sa.Text(), nullable=True),
            sa.Column("conditions_generales_pdf_url", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["assureur_id"], ["assureurs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("code"),
        )
        op.create_index("ix_produits_assurance_id", "produits_assurance", ["id"], unique=False)
        op.create_index("ix_produits_assurance_code", "produits_assurance", ["code"], unique=True)
        op.create_index("ix_produits_assurance_assureur_id", "produits_assurance", ["assureur_id"], unique=False)
        existing.append("produits_assurance")
    if "projets_voyage" not in existing:
        op.create_table("projets_voyage",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("titre", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("destination", sa.String(200), nullable=False),
            sa.Column("destination_country_id", sa.Integer(), nullable=True),
            sa.Column("date_depart", sa.DateTime(), nullable=False),
            sa.Column("date_retour", sa.DateTime(), nullable=True),
            sa.Column("nombre_participants", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("statut", statutprojetvoyage, nullable=False, server_default="en_planification"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("budget_estime", sa.Numeric(10, 2), nullable=True),
            sa.Column("questionnaire_type", questionnairetype, nullable=False, server_default="long"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["destination_country_id"], ["destination_countries.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_projets_voyage_id", "projets_voyage", ["id"], unique=False)
        op.create_index("ix_projets_voyage_user_id", "projets_voyage", ["user_id"], unique=False)
        op.create_index("ix_projets_voyage_destination_country_id", "projets_voyage", ["destination_country_id"], unique=False)
        existing.append("projets_voyage")
    if "souscriptions" not in existing:
        op.create_table("souscriptions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("produit_assurance_id", sa.Integer(), nullable=False),
            sa.Column("projet_voyage_id", sa.Integer(), nullable=True),
            sa.Column("numero_souscription", sa.String(100), nullable=False),
            sa.Column("prix_applique", sa.Numeric(10, 2), nullable=False),
            sa.Column("date_debut", sa.DateTime(), nullable=False),
            sa.Column("date_fin", sa.DateTime(), nullable=True),
            sa.Column("statut", statutsouscription, nullable=False, server_default="en_attente"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("validation_medicale", sa.String(20), nullable=True),
            sa.Column("validation_medicale_par", sa.Integer(), nullable=True),
            sa.Column("validation_medicale_date", sa.DateTime(), nullable=True),
            sa.Column("validation_medicale_notes", sa.Text(), nullable=True),
            sa.Column("validation_technique", sa.String(20), nullable=True),
            sa.Column("validation_technique_par", sa.Integer(), nullable=True),
            sa.Column("validation_technique_date", sa.DateTime(), nullable=True),
            sa.Column("validation_technique_notes", sa.Text(), nullable=True),
            sa.Column("validation_finale", sa.String(20), nullable=True),
            sa.Column("validation_finale_par", sa.Integer(), nullable=True),
            sa.Column("validation_finale_date", sa.DateTime(), nullable=True),
            sa.Column("validation_finale_notes", sa.Text(), nullable=True),
            sa.Column("demande_resiliation", sa.String(20), nullable=True),
            sa.Column("demande_resiliation_date", sa.DateTime(), nullable=True),
            sa.Column("demande_resiliation_notes", sa.Text(), nullable=True),
            sa.Column("demande_resiliation_par_agent", sa.Integer(), nullable=True),
            sa.Column("demande_resiliation_date_traitement", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["produit_assurance_id"], ["produits_assurance.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["projet_voyage_id"], ["projets_voyage.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["validation_medicale_par"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["validation_technique_par"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["validation_finale_par"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["demande_resiliation_par_agent"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("numero_souscription"),
        )
        op.create_index("ix_souscriptions_id", "souscriptions", ["id"], unique=False)
        op.create_index("ix_souscriptions_user_id", "souscriptions", ["user_id"], unique=False)
        op.create_index("ix_souscriptions_produit_assurance_id", "souscriptions", ["produit_assurance_id"], unique=False)
        op.create_index("ix_souscriptions_projet_voyage_id", "souscriptions", ["projet_voyage_id"], unique=False)
        op.create_index("ix_souscriptions_numero_souscription", "souscriptions", ["numero_souscription"], unique=True)
        op.create_index("ix_souscriptions_validation_medicale", "souscriptions", ["validation_medicale"], unique=False)
        op.create_index("ix_souscriptions_validation_technique", "souscriptions", ["validation_technique"], unique=False)
        op.create_index("ix_souscriptions_validation_finale", "souscriptions", ["validation_finale"], unique=False)
        op.create_index("ix_souscriptions_demande_resiliation", "souscriptions", ["demande_resiliation"], unique=False)
        existing.append("souscriptions")


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        inspector = sa.inspect(conn)
        existing = inspector.get_table_names()
        if "souscriptions" not in existing:
            _ensure_souscriptions_and_deps(conn, existing)

    # Create questionnaires table
    op.create_table(
        'questionnaires',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('souscription_id', sa.Integer(), nullable=False),
        sa.Column('type_questionnaire', sa.String(length=20), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('reponses', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('statut', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['souscription_id'], ['souscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questionnaires_id'), 'questionnaires', ['id'], unique=False)
    op.create_index(op.f('ix_questionnaires_souscription_id'), 'questionnaires', ['souscription_id'], unique=False)
    op.create_index(op.f('ix_questionnaires_type_questionnaire'), 'questionnaires', ['type_questionnaire'], unique=False)
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type_notification', sa.String(length=50), nullable=False),
        sa.Column('titre', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('lien_relation_id', sa.Integer(), nullable=True),
        sa.Column('lien_relation_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_is_read'), 'notifications', ['is_read'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_is_read'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    
    op.drop_index(op.f('ix_questionnaires_type_questionnaire'), table_name='questionnaires')
    op.drop_index(op.f('ix_questionnaires_souscription_id'), table_name='questionnaires')
    op.drop_index(op.f('ix_questionnaires_id'), table_name='questionnaires')
    op.drop_table('questionnaires')
