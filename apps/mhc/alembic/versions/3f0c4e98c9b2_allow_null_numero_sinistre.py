"""Allow null numero_sinistre until validation

Revision ID: 3f0c4e98c9b2
Revises: 2c3b1a84b0e4
Create Date: 2025-01-24 12:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f0c4e98c9b2"
down_revision: Union[str, None] = "2c3b1a84b0e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "sinistres",
        "numero_sinistre",
        existing_type=sa.String(length=100),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE sinistres
        SET numero_sinistre = concat('SIN-', id, '-', to_char(now(), 'YYYYMMDDHH24MISS'))
        WHERE numero_sinistre IS NULL
        """
    )
    op.alter_column(
        "sinistres",
        "numero_sinistre",
        existing_type=sa.String(length=100),
        nullable=False,
    )


