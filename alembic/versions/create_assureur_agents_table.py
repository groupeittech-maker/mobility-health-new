"""create_assureur_agents_table

Revision ID: create_assureur_agents
Revises: b6c21f3b0c8d
Create Date: 2025-12-04 20:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'create_assureur_agents'
down_revision = 'b6c21f3b0c8d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Créer la table assureur_agents
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS assureur_agents (
            id SERIAL NOT NULL,
            assureur_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            type_agent VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY(assureur_id) REFERENCES assureurs (id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            CONSTRAINT uq_assureur_agent_user UNIQUE (user_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_assureur_agents_id ON assureur_agents (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_assureur_agents_assureur_id ON assureur_agents (assureur_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_assureur_agents_user_id ON assureur_agents (user_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_assureur_agents_user_id")
    op.execute("DROP INDEX IF EXISTS ix_assureur_agents_assureur_id")
    op.execute("DROP INDEX IF EXISTS ix_assureur_agents_id")
    op.execute("DROP TABLE IF EXISTS assureur_agents")

