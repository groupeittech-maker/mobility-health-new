"""Tables manquantes vs modèles : contacts_proches, historique_prix, failed_tasks, prestations.

Révision : r8a9b0c1d2e3 -> s9b0c1d2e3f4

Constat : pas de comparaison réseau local/prod ici ; audit statique des __tablename__
dans app/models vs create_table dans alembic/versions. Ces 4 tables n’avaient aucune migration.

Idempotent : skip toute table déjà présente (VPS / BDD partiellement migrée).
"""
from alembic import op
import sqlalchemy as sa


revision = "s9b0c1d2e3f4"
down_revision = "r8a9b0c1d2e3"
branch_labels = None
depends_on = None


def _create_contacts_proches() -> None:
    op.create_table(
        "contacts_proches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(length=200), nullable=False),
        sa.Column("prenom", sa.String(length=200), nullable=False),
        sa.Column("telephone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("relation", sa.String(length=100), nullable=True),
        sa.Column("est_contact_urgence", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("adresse", sa.String(length=500), nullable=True),
        sa.Column("pays", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contacts_proches_id"), "contacts_proches", ["id"], unique=False)
    op.create_index(op.f("ix_contacts_proches_user_id"), "contacts_proches", ["user_id"], unique=False)


def _create_historique_prix() -> None:
    op.create_table(
        "historique_prix",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("produit_assurance_id", sa.Integer(), nullable=False),
        sa.Column("ancien_prix", sa.Numeric(10, 2), nullable=True),
        sa.Column("nouveau_prix", sa.Numeric(10, 2), nullable=False),
        sa.Column("raison_modification", sa.Text(), nullable=True),
        sa.Column("modifie_par_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["modifie_par_user_id"],
            ["users.id"],
            name="fk_historique_prix_modifie_par_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["produit_assurance_id"],
            ["produits_assurance.id"],
            name="fk_historique_prix_produit_assurance_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_historique_prix_id"), "historique_prix", ["id"], unique=False)
    op.create_index(
        op.f("ix_historique_prix_produit_assurance_id"),
        "historique_prix",
        ["produit_assurance_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_historique_prix_modifie_par_user_id"),
        "historique_prix",
        ["modifie_par_user_id"],
        unique=False,
    )


def _create_failed_tasks() -> None:
    op.create_table(
        "failed_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(length=255), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("task_args", sa.JSON(), nullable=True),
        sa.Column("task_kwargs", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("queue_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_failed_tasks_id"), "failed_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_failed_tasks_task_id"), "failed_tasks", ["task_id"], unique=True)
    op.create_index(op.f("ix_failed_tasks_task_name"), "failed_tasks", ["task_name"], unique=False)
    op.create_index(op.f("ix_failed_tasks_is_resolved"), "failed_tasks", ["is_resolved"], unique=False)
    op.create_index(op.f("ix_failed_tasks_queue_name"), "failed_tasks", ["queue_name"], unique=False)


def _create_prestations() -> None:
    op.create_table(
        "prestations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hospital_id", sa.Integer(), nullable=False),
        sa.Column("sinistre_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("code_prestation", sa.String(length=50), nullable=False),
        sa.Column("libelle", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("montant_unitaire", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantite", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("montant_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("date_prestation", sa.DateTime(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["hospital_id"],
            ["hospitals.id"],
            name="fk_prestations_hospital_id_hospitals",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sinistre_id"],
            ["sinistres.id"],
            name="fk_prestations_sinistre_id_sinistres",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_prestations_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prestations_id"), "prestations", ["id"], unique=False)
    op.create_index(op.f("ix_prestations_hospital_id"), "prestations", ["hospital_id"], unique=False)
    op.create_index(op.f("ix_prestations_sinistre_id"), "prestations", ["sinistre_id"], unique=False)
    op.create_index(op.f("ix_prestations_user_id"), "prestations", ["user_id"], unique=False)
    op.create_index(op.f("ix_prestations_code_prestation"), "prestations", ["code_prestation"], unique=False)
    op.create_index(op.f("ix_prestations_statut"), "prestations", ["statut"], unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    names = set(insp.get_table_names())

    if "contacts_proches" not in names:
        _create_contacts_proches()
    if "historique_prix" not in names:
        _create_historique_prix()
    if "failed_tasks" not in names:
        _create_failed_tasks()
    if "prestations" not in names:
        _create_prestations()


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    names = set(insp.get_table_names())

    if "prestations" in names:
        op.drop_index(op.f("ix_prestations_statut"), table_name="prestations")
        op.drop_index(op.f("ix_prestations_code_prestation"), table_name="prestations")
        op.drop_index(op.f("ix_prestations_user_id"), table_name="prestations")
        op.drop_index(op.f("ix_prestations_sinistre_id"), table_name="prestations")
        op.drop_index(op.f("ix_prestations_hospital_id"), table_name="prestations")
        op.drop_index(op.f("ix_prestations_id"), table_name="prestations")
        op.drop_table("prestations")

    if "failed_tasks" in names:
        op.drop_index(op.f("ix_failed_tasks_queue_name"), table_name="failed_tasks")
        op.drop_index(op.f("ix_failed_tasks_is_resolved"), table_name="failed_tasks")
        op.drop_index(op.f("ix_failed_tasks_task_name"), table_name="failed_tasks")
        op.drop_index(op.f("ix_failed_tasks_task_id"), table_name="failed_tasks")
        op.drop_index(op.f("ix_failed_tasks_id"), table_name="failed_tasks")
        op.drop_table("failed_tasks")

    if "historique_prix" in names:
        op.drop_index(op.f("ix_historique_prix_modifie_par_user_id"), table_name="historique_prix")
        op.drop_index(op.f("ix_historique_prix_produit_assurance_id"), table_name="historique_prix")
        op.drop_index(op.f("ix_historique_prix_id"), table_name="historique_prix")
        op.drop_table("historique_prix")

    if "contacts_proches" in names:
        op.drop_index(op.f("ix_contacts_proches_user_id"), table_name="contacts_proches")
        op.drop_index(op.f("ix_contacts_proches_id"), table_name="contacts_proches")
        op.drop_table("contacts_proches")
