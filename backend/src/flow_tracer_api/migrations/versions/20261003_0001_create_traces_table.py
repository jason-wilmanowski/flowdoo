"""create traces table

Revision ID: 0001
Revises:
Create Date: 2026-10-03 13:58:17.552444

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "traces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=True),
        sa.Column("odoo_version", sa.String(length=32), nullable=True),
        sa.Column("entrypoint_model", sa.String(length=128), nullable=False),
        sa.Column("entrypoint_method", sa.String(length=128), nullable=False),
        sa.Column("dry_run", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed')",
            name=op.f("ck_traces_trace_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_traces")),
    )
    op.create_index("ix_traces_created_at", "traces", ["created_at"], unique=False)
    op.create_index(
        "ix_traces_entrypoint", "traces", ["entrypoint_model", "entrypoint_method"], unique=False
    )
    op.create_index("ix_traces_status", "traces", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_traces_status", table_name="traces")
    op.drop_index("ix_traces_entrypoint", table_name="traces")
    op.drop_index("ix_traces_created_at", table_name="traces")
    op.drop_table("traces")
