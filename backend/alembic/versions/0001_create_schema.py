"""create normalized knowledge base schema

Revision ID: 0001_create_schema
Revises:
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "body_systems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
    )

    op.create_table(
        "characteristics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("allowed_min", sa.Float(), nullable=True),
        sa.Column("allowed_max", sa.Float(), nullable=True),
        sa.Column("normal_min", sa.Float(), nullable=True),
        sa.Column("normal_max", sa.Float(), nullable=True),
        sa.Column("normal_enum_key", sa.String(length=32), nullable=True),
    )

    op.create_table(
        "characteristic_enum_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("characteristic_id", sa.Integer(), sa.ForeignKey("characteristics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("option_key", sa.String(length=32), nullable=False),
        sa.Column("option_value", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("characteristic_id", "option_key", name="uq_char_option_key"),
    )

    op.create_table(
        "body_system_characteristics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("body_system_id", sa.Integer(), sa.ForeignKey("body_systems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("characteristic_id", sa.Integer(), sa.ForeignKey("characteristics.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("body_system_id", "characteristic_id", name="uq_body_system_characteristic"),
    )

    op.create_table(
        "treatments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
    )

    op.create_table(
        "treatment_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("treatment_id", sa.Integer(), sa.ForeignKey("treatments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.UniqueConstraint("treatment_id", "position", name="uq_treatment_action_position"),
    )

    op.create_table(
        "diagnoses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("icd10", sa.String(length=32), nullable=True),
        sa.Column("treatment_id", sa.Integer(), sa.ForeignKey("treatments.id", ondelete="RESTRICT"), nullable=False),
    )

    op.create_table(
        "diagnosis_characteristics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("diagnosis_id", sa.Integer(), sa.ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("characteristic_id", sa.Integer(), sa.ForeignKey("characteristics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expected_enum_key", sa.String(length=32), nullable=True),
        sa.Column("expected_min", sa.Float(), nullable=True),
        sa.Column("expected_max", sa.Float(), nullable=True),
        sa.UniqueConstraint("diagnosis_id", "characteristic_id", name="uq_diagnosis_characteristic"),
    )


def downgrade() -> None:
    op.drop_table("diagnosis_characteristics")
    op.drop_table("diagnoses")
    op.drop_table("treatment_actions")
    op.drop_table("treatments")
    op.drop_table("body_system_characteristics")
    op.drop_table("characteristic_enum_options")
    op.drop_table("characteristics")
    op.drop_table("body_systems")
