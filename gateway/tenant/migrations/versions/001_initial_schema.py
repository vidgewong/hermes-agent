"""Initial multi-tenant schema: users, im_identities, user_profiles.

Revision ID: 001
Revises: None
Create Date: 2026-07-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(128), unique=True, nullable=False),
        sa.Column("display_name", sa.String(256), nullable=True),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("wiw_id", sa.String(128), nullable=True),
        sa.Column("roles", JSONB, server_default="{}"),
        sa.Column("responsibilities", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "im_identities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("platform_user_id", sa.String(256), nullable=False),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("linked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("platform", "platform_user_id", name="uq_platform_identity"),
    )
    op.create_index("ix_im_identities_lookup", "im_identities", ["platform", "platform_user_id"])

    op.create_table(
        "user_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("profile_name", sa.String(128), nullable=False),
        sa.Column("is_primary", sa.Boolean, server_default="true"),
        sa.Column("provisioned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "profile_name", name="uq_user_profile"),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
    op.drop_index("ix_im_identities_lookup", table_name="im_identities")
    op.drop_table("im_identities")
    op.drop_table("users")
