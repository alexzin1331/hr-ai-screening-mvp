"""email invite and telegram onboarding fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260311_0002"
down_revision = "20260311_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidates", sa.Column("telegram_chat_id", sa.String(length=100), nullable=True))
    op.add_column("candidates", sa.Column("telegram_connected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("candidates", sa.Column("contact_status", sa.String(length=50), nullable=False, server_default="new"))
    op.add_column("candidates", sa.Column("invite_token", sa.String(length=255), nullable=True))
    op.add_column("candidates", sa.Column("invite_token_created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("candidates", sa.Column("email_invite_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("candidates", sa.Column("email_invite_status", sa.String(length=50), nullable=True))
    op.add_column("candidates", sa.Column("telegram_last_error", sa.String(length=500), nullable=True))

    op.create_index(op.f("ix_candidates_telegram_chat_id"), "candidates", ["telegram_chat_id"], unique=False)
    op.create_index(op.f("ix_candidates_contact_status"), "candidates", ["contact_status"], unique=False)
    op.create_index(op.f("ix_candidates_invite_token"), "candidates", ["invite_token"], unique=True)
    op.create_index(op.f("ix_candidates_email_invite_status"), "candidates", ["email_invite_status"], unique=False)

    op.execute(
        """
        UPDATE candidates
        SET contact_status = CASE
            WHEN email IS NULL OR email = '' THEN 'email_missing'
            ELSE 'email_invite_pending'
        END,
        email_invite_status = CASE
            WHEN email IS NULL OR email = '' THEN 'missing'
            ELSE 'pending'
        END
        """
    )

    op.alter_column("candidates", "contact_status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_candidates_email_invite_status"), table_name="candidates")
    op.drop_index(op.f("ix_candidates_invite_token"), table_name="candidates")
    op.drop_index(op.f("ix_candidates_contact_status"), table_name="candidates")
    op.drop_index(op.f("ix_candidates_telegram_chat_id"), table_name="candidates")
    op.drop_column("candidates", "telegram_last_error")
    op.drop_column("candidates", "email_invite_status")
    op.drop_column("candidates", "email_invite_sent_at")
    op.drop_column("candidates", "invite_token_created_at")
    op.drop_column("candidates", "invite_token")
    op.drop_column("candidates", "contact_status")
    op.drop_column("candidates", "telegram_connected_at")
    op.drop_column("candidates", "telegram_chat_id")
