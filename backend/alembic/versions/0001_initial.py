"""Initial database schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# ---------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------

def upgrade() -> None:

    # ================================================================
    # Users
    # ================================================================

    op.create_table(
        "users",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "hashed_password",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "full_name",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_users_id",
        "users",
        ["id"],
    )

    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
    )

    # ================================================================
    # Documents
    # ================================================================

    op.create_table(
        "documents",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),

        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "nin",
            sa.String(length=32),
            nullable=True,
        ),

        sa.Column(
            "nom",
            sa.String(length=128),
            nullable=True,
        ),

        sa.Column(
            "prenom",
            sa.String(length=128),
            nullable=True,
        ),

        sa.Column(
            "raw_text",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "face_encoding",
            sa.LargeBinary(),
            nullable=True,
        ),

        sa.Column(
            "document_image",
            sa.LargeBinary(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_documents_id",
        "documents",
        ["id"],
    )

    op.create_index(
        "ix_documents_nin",
        "documents",
        ["nin"],
    )

    op.create_index(
        "ix_documents_user_id",
        "documents",
        ["user_id"],
    )

    # ================================================================
    # Verifications
    # ================================================================

    op.create_table(
        "verifications",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey(
                "documents.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),

        sa.Column(
            "match",
            sa.String(length=16),
            nullable=True,
        ),

        sa.Column(
            "distance",
            sa.Float(),
            nullable=True,
        ),

        sa.Column(
            "confidence",
            sa.Float(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_verifications_id",
        "verifications",
        ["id"],
    )

    op.create_index(
        "ix_verifications_document_id",
        "verifications",
        ["document_id"],
    )


# ---------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------

def downgrade() -> None:

    # Verifications
    op.drop_index(
        "ix_verifications_document_id",
        table_name="verifications",
    )

    op.drop_index(
        "ix_verifications_id",
        table_name="verifications",
    )

    op.drop_table("verifications")

    # Documents
    op.drop_index(
        "ix_documents_user_id",
        table_name="documents",
    )

    op.drop_index(
        "ix_documents_nin",
        table_name="documents",
    )

    op.drop_index(
        "ix_documents_id",
        table_name="documents",
    )

    op.drop_table("documents")

    # Users
    op.drop_index(
        "ix_users_email",
        table_name="users",
    )

    op.drop_index(
        "ix_users_id",
        table_name="users",
    )

    op.drop_table("users")