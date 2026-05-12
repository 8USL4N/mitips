from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.orm import (
    BodySystem,
    BodySystemCharacteristic,
    Characteristic,
    CharacteristicEnumOption,
    Diagnosis,
    DiagnosisCharacteristic,
    Treatment,
    TreatmentAction,
)


class KnowledgeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def count_diagnoses(self) -> int:
        return int(self.session.scalar(select(func.count(Diagnosis.id))) or 0)

    def list_diagnoses(self) -> list[Diagnosis]:
        statement = (
            select(Diagnosis)
            .options(joinedload(Diagnosis.treatment))
            .order_by(Diagnosis.name)
        )
        return list(self.session.scalars(statement).unique().all())

    def get_diagnosis(self, diagnosis_id: int) -> Diagnosis | None:
        statement = (
            select(Diagnosis)
            .where(Diagnosis.id == diagnosis_id)
            .options(
                joinedload(Diagnosis.treatment).joinedload(Treatment.actions),
                joinedload(Diagnosis.criteria)
                .joinedload(DiagnosisCharacteristic.characteristic)
                .joinedload(Characteristic.enum_options),
            )
        )
        return self.session.scalar(statement)

    def get_diagnosis_by_name(self, name: str) -> Diagnosis | None:
        return self.session.scalar(select(Diagnosis).where(Diagnosis.name == name))

    def list_diagnoses_using_characteristic(self, characteristic_id: int) -> list[Diagnosis]:
        statement = (
            select(Diagnosis)
            .join(DiagnosisCharacteristic, DiagnosisCharacteristic.diagnosis_id == Diagnosis.id)
            .where(DiagnosisCharacteristic.characteristic_id == characteristic_id)
            .order_by(Diagnosis.name)
        )
        return list(self.session.scalars(statement).unique().all())

    def list_diagnoses_using_treatment(self, treatment_id: int) -> list[Diagnosis]:
        statement = select(Diagnosis).where(Diagnosis.treatment_id == treatment_id).order_by(Diagnosis.name)
        return list(self.session.scalars(statement).unique().all())

    def list_diagnosis_characteristics_by_characteristic(self, characteristic_id: int) -> list[DiagnosisCharacteristic]:
        statement = select(DiagnosisCharacteristic).where(DiagnosisCharacteristic.characteristic_id == characteristic_id)
        return list(self.session.scalars(statement).all())

    def list_characteristics(self) -> list[Characteristic]:
        statement = (
            select(Characteristic)
            .options(joinedload(Characteristic.enum_options))
            .order_by(Characteristic.name)
        )
        return list(self.session.scalars(statement).unique().all())

    def get_characteristic(self, characteristic_id: int) -> Characteristic | None:
        statement = (
            select(Characteristic)
            .where(Characteristic.id == characteristic_id)
            .options(
                joinedload(Characteristic.enum_options),
                joinedload(Characteristic.diagnosis_links).joinedload(DiagnosisCharacteristic.diagnosis),
                joinedload(Characteristic.body_system_links).joinedload(BodySystemCharacteristic.body_system),
            )
        )
        return self.session.scalar(statement)

    def get_characteristic_by_name(self, name: str) -> Characteristic | None:
        return self.session.scalar(select(Characteristic).where(Characteristic.name == name))

    def list_body_systems(self) -> list[BodySystem]:
        statement = (
            select(BodySystem)
            .options(joinedload(BodySystem.characteristics).joinedload(BodySystemCharacteristic.characteristic))
            .order_by(BodySystem.name)
        )
        return list(self.session.scalars(statement).unique().all())

    def get_body_system(self, body_system_id: int) -> BodySystem | None:
        statement = (
            select(BodySystem)
            .where(BodySystem.id == body_system_id)
            .options(joinedload(BodySystem.characteristics).joinedload(BodySystemCharacteristic.characteristic))
        )
        return self.session.scalar(statement)

    def get_body_system_by_name(self, name: str) -> BodySystem | None:
        return self.session.scalar(select(BodySystem).where(BodySystem.name == name))

    def get_characteristics_by_ids(self, ids: list[int]) -> dict[int, Characteristic]:
        if not ids:
            return {}
        statement = (
            select(Characteristic)
            .where(Characteristic.id.in_(ids))
            .options(joinedload(Characteristic.enum_options))
        )
        rows = self.session.scalars(statement).unique().all()
        return {row.id: row for row in rows}

    def list_body_systems_using_characteristic(self, characteristic_id: int) -> list[BodySystem]:
        statement = (
            select(BodySystem)
            .join(BodySystemCharacteristic, BodySystemCharacteristic.body_system_id == BodySystem.id)
            .where(BodySystemCharacteristic.characteristic_id == characteristic_id)
            .order_by(BodySystem.name)
        )
        return list(self.session.scalars(statement).unique().all())

    def list_treatments(self) -> list[Treatment]:
        statement = (
            select(Treatment)
            .options(joinedload(Treatment.actions), joinedload(Treatment.diagnoses))
            .order_by(Treatment.name)
        )
        return list(self.session.scalars(statement).unique().all())

    def get_treatment(self, treatment_id: int) -> Treatment | None:
        statement = (
            select(Treatment)
            .where(Treatment.id == treatment_id)
            .options(joinedload(Treatment.actions), joinedload(Treatment.diagnoses))
        )
        return self.session.scalars(statement).unique().first()

    def get_treatment_by_name(self, name: str) -> Treatment | None:
        return self.session.scalar(select(Treatment).where(Treatment.name == name))

    def create_body_system(self, name: str) -> BodySystem:
        system = BodySystem(name=name)
        self.session.add(system)
        self.session.flush()
        return system

    def create_characteristic(
        self,
        *,
        name: str,
        type_name: str,
        unit: str,
        allowed_min: float | None,
        allowed_max: float | None,
        normal_min: float | None,
        normal_max: float | None,
        normal_enum_key: str | None,
    ) -> Characteristic:
        item = Characteristic(
            name=name,
            type=type_name,
            unit=unit,
            allowed_min=allowed_min,
            allowed_max=allowed_max,
            normal_min=normal_min,
            normal_max=normal_max,
            normal_enum_key=normal_enum_key,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def add_characteristic_enum_option(
        self,
        *,
        characteristic_id: int,
        option_key: str,
        option_value: str,
    ) -> CharacteristicEnumOption:
        option = CharacteristicEnumOption(
            characteristic_id=characteristic_id,
            option_key=option_key,
            option_value=option_value,
        )
        self.session.add(option)
        self.session.flush()
        return option

    def clear_characteristic_enum_options(self, characteristic_id: int) -> None:
        self.session.execute(
            delete(CharacteristicEnumOption).where(CharacteristicEnumOption.characteristic_id == characteristic_id)
        )

    def add_body_system_characteristic(
        self,
        *,
        body_system_id: int,
        characteristic_id: int,
    ) -> BodySystemCharacteristic:
        relation = BodySystemCharacteristic(
            body_system_id=body_system_id,
            characteristic_id=characteristic_id,
        )
        self.session.add(relation)
        self.session.flush()
        return relation

    def clear_body_system_characteristics(self, body_system_id: int) -> None:
        self.session.execute(
            delete(BodySystemCharacteristic).where(BodySystemCharacteristic.body_system_id == body_system_id)
        )

    def create_treatment(self, name: str) -> Treatment:
        treatment = Treatment(name=name)
        self.session.add(treatment)
        self.session.flush()
        return treatment

    def delete_treatment(self, treatment: Treatment) -> None:
        self.session.delete(treatment)

    def create_treatment_action(self, *, treatment_id: int, position: int, action: str) -> TreatmentAction:
        row = TreatmentAction(treatment_id=treatment_id, position=position, action=action)
        self.session.add(row)
        self.session.flush()
        return row

    def clear_treatment_actions(self, treatment_id: int) -> None:
        self.session.execute(delete(TreatmentAction).where(TreatmentAction.treatment_id == treatment_id))

    def create_diagnosis(self, *, name: str, icd10: str | None, treatment_id: int) -> Diagnosis:
        diagnosis = Diagnosis(name=name, icd10=icd10, treatment_id=treatment_id)
        self.session.add(diagnosis)
        self.session.flush()
        return diagnosis

    def clear_diagnosis_criteria(self, diagnosis_id: int) -> None:
        self.session.execute(delete(DiagnosisCharacteristic).where(DiagnosisCharacteristic.diagnosis_id == diagnosis_id))

    def create_diagnosis_criterion(
        self,
        *,
        diagnosis_id: int,
        characteristic_id: int,
        expected_enum_key: str | None,
        expected_min: float | None,
        expected_max: float | None,
    ) -> DiagnosisCharacteristic:
        row = DiagnosisCharacteristic(
            diagnosis_id=diagnosis_id,
            characteristic_id=characteristic_id,
            expected_enum_key=expected_enum_key,
            expected_min=expected_min,
            expected_max=expected_max,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def delete_diagnosis(self, diagnosis: Diagnosis) -> None:
        self.session.delete(diagnosis)

    def delete_body_system(self, body_system: BodySystem) -> None:
        self.session.delete(body_system)

    def delete_characteristic(self, characteristic: Characteristic) -> None:
        self.session.delete(characteristic)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
