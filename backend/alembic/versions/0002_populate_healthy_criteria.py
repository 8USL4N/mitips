"""populate healthy diagnosis criteria

Revision ID: 0002_populate_healthy_criteria
Revises: 0001_create_schema
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_populate_healthy_criteria"
down_revision = "0001_create_schema"
branch_labels = None
depends_on = None


HEALTHY_NAME = "Здоров"
HEALTHY_CRITERIA = [
    ("Температура тела", None, 36.6, 37.0),
    ("Характер стула", "0", None, None),
    ("Наличие и характер сыпи", "0", None, None),
    ("Кашель", "0", None, None),
    ("Цвет кожных покровов и склер", "0", None, None),
    ("Боль в животе", "0", None, None),
    ("Увеличение лимфоузлов", "0", None, None),
]


def _table(table_name: str, bind: sa.Connection) -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(table_name, metadata, autoload_with=bind)


def _healthy_id(bind: sa.Connection, diagnoses: sa.Table) -> int | None:
    query = sa.select(diagnoses.c.id).where(diagnoses.c.name == HEALTHY_NAME)
    return bind.execute(query).scalar_one_or_none()


def upgrade() -> None:
    bind = op.get_bind()

    diagnoses = _table("diagnoses", bind)
    characteristics = _table("characteristics", bind)
    diagnosis_characteristics = _table("diagnosis_characteristics", bind)

    healthy_id = _healthy_id(bind, diagnoses)
    if healthy_id is None:
        return

    for characteristic_name, expected_enum_key, expected_min, expected_max in HEALTHY_CRITERIA:
        characteristic_id = bind.execute(
            sa.select(characteristics.c.id).where(characteristics.c.name == characteristic_name)
        ).scalar_one_or_none()
        if characteristic_id is None:
            continue

        exists = bind.execute(
            sa.select(diagnosis_characteristics.c.id).where(
                diagnosis_characteristics.c.diagnosis_id == healthy_id,
                diagnosis_characteristics.c.characteristic_id == characteristic_id,
            )
        ).scalar_one_or_none()
        if exists is not None:
            continue

        bind.execute(
            diagnosis_characteristics.insert().values(
                diagnosis_id=healthy_id,
                characteristic_id=characteristic_id,
                expected_enum_key=expected_enum_key,
                expected_min=expected_min,
                expected_max=expected_max,
            )
        )


def downgrade() -> None:
    bind = op.get_bind()

    diagnoses = _table("diagnoses", bind)
    characteristics = _table("characteristics", bind)
    diagnosis_characteristics = _table("diagnosis_characteristics", bind)

    healthy_id = _healthy_id(bind, diagnoses)
    if healthy_id is None:
        return

    characteristic_names = [item[0] for item in HEALTHY_CRITERIA]
    characteristic_ids = [
        row[0]
        for row in bind.execute(
            sa.select(characteristics.c.id).where(characteristics.c.name.in_(characteristic_names))
        ).all()
    ]
    if not characteristic_ids:
        return

    bind.execute(
        sa.delete(diagnosis_characteristics).where(
            diagnosis_characteristics.c.diagnosis_id == healthy_id,
            diagnosis_characteristics.c.characteristic_id.in_(characteristic_ids),
        )
    )
