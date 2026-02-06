"""Initial migration

Revision ID: 994235826591
Revises: 
Create Date: 2025-11-23 13:33:19.430914

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '994235826591'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Détecter le type de base de données
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == 'sqlite'
    
    # Pour PostgreSQL : créer le type ENUM
    # Pour SQLite : utiliser String avec CHECK constraint
    if not is_sqlite:
        # Create role enum type if it doesn't exist (PostgreSQL only)
        try:
            conn.execute(sa.text("""
                DO $$ BEGIN
                    CREATE TYPE role AS ENUM ('admin', 'user', 'doctor', 'hospital_admin', 'finance_manager', 'sos_operator');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
        except Exception:
            pass  # Le type existe peut-être déjà
        
        # Create role enum object for use in table definition (PostgreSQL)
        role_enum = postgresql.ENUM('admin', 'user', 'doctor', 'hospital_admin', 'finance_manager', 'sos_operator', name='role', create_type=False)
        role_column = sa.Column('role', role_enum, nullable=False)
    else:
        # Pour SQLite : utiliser String avec CHECK constraint
        role_column = sa.Column('role', sa.String(), nullable=False, 
                               server_default='user',
                               comment="Role: admin, user, doctor, hospital_admin, finance_manager, sos_operator")
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        role_column,
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Pour SQLite : ajouter la contrainte CHECK après création de la table
    if is_sqlite:
        op.execute(sa.text("""
            CREATE TRIGGER IF NOT EXISTS check_role_before_insert_users
            BEFORE INSERT ON users
            BEGIN
                SELECT CASE
                    WHEN NEW.role NOT IN ('admin', 'user', 'doctor', 'hospital_admin', 'finance_manager', 'sos_operator')
                    THEN RAISE(ABORT, 'Invalid role value')
                END;
            END;
        """))
        op.execute(sa.text("""
            CREATE TRIGGER IF NOT EXISTS check_role_before_update_users
            BEFORE UPDATE ON users
            BEGIN
                SELECT CASE
                    WHEN NEW.role NOT IN ('admin', 'user', 'doctor', 'hospital_admin', 'finance_manager', 'sos_operator')
                    THEN RAISE(ABORT, 'Invalid role value')
                END;
            END;
        """))
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('method', sa.String(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('query_params', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_role', sa.String(), nullable=True),
        sa.Column('client_ip', sa.String(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    postgresql.ENUM(name='role').drop(op.get_bind(), checkfirst=True)

