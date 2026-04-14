import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_seed_path
from app.orm import BodySystem
from app.repositories.knowledge import KnowledgeRepository


class KnowledgeService:
    def __init__(self, session: Session) -> None:
        self.repo = KnowledgeRepository(session)
        self.session = session

    @staticmethod
    def _serialize_characteristic(item) -> dict[str, Any]:
        if item.type == "range":
            allowed: list[float] | dict[str, str] = [
                float(item.allowed_min or 0.0),
                float(item.allowed_max or 0.0),
            ]
            normal: list[float] | str = [
                float(item.normal_min or 0.0),
                float(item.normal_max or 0.0),
            ]
        else:
            options = sorted(item.enum_options, key=lambda row: row.option_key)
            allowed = {row.option_key: row.option_value for row in options}
            normal = item.normal_enum_key or ""

        return {
            "id": item.id,
            "name": item.name,
            "type": item.type,
            "unit": item.unit,
            "allowed": allowed,
            "normal": normal,
        }

    @staticmethod
    def _serialize_treatment(item) -> dict[str, Any]:
        actions = [row.action for row in sorted(item.actions, key=lambda row: row.position)]
        return {
            "id": item.id,
            "name": item.name,
            "actions": actions,
        }

    @staticmethod
    def _serialize_criterion(row) -> dict[str, Any]:
        return {
            "id": row.id,
            "characteristic_id": row.characteristic_id,
            "characteristic_name": row.characteristic.name,
            "characteristic_type": row.characteristic.type,
            "characteristic_unit": row.characteristic.unit,
            "expected_enum_key": row.expected_enum_key,
            "expected_min": row.expected_min,
            "expected_max": row.expected_max,
        }

    @staticmethod
    def _serialize_diagnosis_summary(item) -> dict[str, Any]:
        return {
            "id": item.id,
            "name": item.name,
            "icd10": item.icd10,
            "treatment_id": item.treatment_id,
            "treatment_name": item.treatment.name,
        }

    def list_diagnoses(self) -> list[dict[str, Any]]:
        rows = self.repo.list_diagnoses()
        return [self._serialize_diagnosis_summary(row) for row in rows]

    def get_diagnosis_detail(self, diagnosis_id: int) -> dict[str, Any] | None:
        row = self.repo.get_diagnosis(diagnosis_id)
        if not row:
            return None

        data = self._serialize_diagnosis_summary(row)
        criteria = [self._serialize_criterion(item) for item in row.criteria]
        criteria.sort(key=lambda item: item["characteristic_name"])
        data["criteria"] = criteria
        return data

    def list_characteristics(self) -> list[dict[str, Any]]:
        rows = self.repo.list_characteristics()
        return [self._serialize_characteristic(row) for row in rows]

    def list_treatments(self) -> list[dict[str, Any]]:
        rows = self.repo.list_treatments()
        return [self._serialize_treatment(row) for row in rows]

    def _validate_criteria_payload(self, criteria: list[dict[str, Any]]) -> None:
        if not criteria:
            return

        characteristic_ids = [item["characteristic_id"] for item in criteria]
        items_by_id = self.repo.get_characteristics_by_ids(characteristic_ids)

        if len(items_by_id) != len(set(characteristic_ids)):
            raise ValueError("Одна или несколько характеристик не найдены")

        for item in criteria:
            characteristic = items_by_id[item["characteristic_id"]]
            expected_enum_key = item.get("expected_enum_key")
            expected_min = item.get("expected_min")
            expected_max = item.get("expected_max")

            if characteristic.type == "range":
                if expected_min is None or expected_max is None:
                    raise ValueError(
                        f"Для характеристики '{characteristic.name}' требуется expected_min и expected_max"
                    )
            elif characteristic.type == "enum":
                if expected_enum_key is None:
                    raise ValueError(
                        f"Для характеристики '{characteristic.name}' требуется expected_enum_key"
                    )

    def create_diagnosis(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.repo.get_diagnosis_by_name(payload["name"]):
            raise ValueError("Диагноз с таким названием уже существует")

        treatment = self.repo.get_treatment(payload["treatment_id"])
        if not treatment:
            raise ValueError("Лечение не найдено")

        criteria = payload.get("criteria", [])
        self._validate_criteria_payload(criteria)

        diagnosis = self.repo.create_diagnosis(
            name=payload["name"],
            icd10=payload.get("icd10"),
            treatment_id=payload["treatment_id"],
        )

        for item in criteria:
            self.repo.create_diagnosis_criterion(
                diagnosis_id=diagnosis.id,
                characteristic_id=item["characteristic_id"],
                expected_enum_key=item.get("expected_enum_key"),
                expected_min=item.get("expected_min"),
                expected_max=item.get("expected_max"),
            )

        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось сохранить диагноз")
        detail = self.get_diagnosis_detail(diagnosis.id)
        if detail is None:
            raise ValueError("Не удалось загрузить созданный диагноз")
        return detail

    def update_diagnosis(self, diagnosis_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        diagnosis = self.repo.get_diagnosis(diagnosis_id)
        if not diagnosis:
            return None

        duplicate = self.repo.get_diagnosis_by_name(payload["name"])
        if duplicate and duplicate.id != diagnosis_id:
            raise ValueError("Диагноз с таким названием уже существует")

        treatment = self.repo.get_treatment(payload["treatment_id"])
        if not treatment:
            raise ValueError("Лечение не найдено")

        criteria = payload.get("criteria", [])
        self._validate_criteria_payload(criteria)

        diagnosis.name = payload["name"]
        diagnosis.icd10 = payload.get("icd10")
        diagnosis.treatment_id = payload["treatment_id"]

        self.repo.clear_diagnosis_criteria(diagnosis.id)
        for item in criteria:
            self.repo.create_diagnosis_criterion(
                diagnosis_id=diagnosis.id,
                characteristic_id=item["characteristic_id"],
                expected_enum_key=item.get("expected_enum_key"),
                expected_min=item.get("expected_min"),
                expected_max=item.get("expected_max"),
            )

        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось обновить диагноз")
        return self.get_diagnosis_detail(diagnosis.id)

    def delete_diagnosis(self, diagnosis_id: int) -> bool:
        diagnosis = self.repo.get_diagnosis(diagnosis_id)
        if not diagnosis:
            return False

        self.repo.delete_diagnosis(diagnosis)
        self.repo.commit()
        return True

    def update_treatment_actions(self, treatment_id: int, actions: list[str]) -> dict[str, Any] | None:
        treatment = self.repo.get_treatment(treatment_id)
        if not treatment:
            return None

        self.repo.clear_treatment_actions(treatment_id)
        for position, action in enumerate(actions):
            self.repo.create_treatment_action(treatment_id=treatment_id, position=position, action=action)

        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось обновить лечение")
        updated = self.repo.get_treatment(treatment_id)
        if not updated:
            return None
        return self._serialize_treatment(updated)

    def get_solver_payload(self, diagnosis_id: int) -> dict[str, Any] | None:
        diagnosis = self.repo.get_diagnosis(diagnosis_id)
        if not diagnosis:
            return None

        return {
            "id": diagnosis.id,
            "name": diagnosis.name,
            "icd10": diagnosis.icd10,
            "treatment_name": diagnosis.treatment.name,
            "actions": [row.action for row in sorted(diagnosis.treatment.actions, key=lambda row: row.position)],
            "criteria": [self._serialize_criterion(item) for item in diagnosis.criteria],
        }

    def seed_from_json_if_empty(self, seed_path: Path | None = None) -> bool:
        if self.repo.count_diagnoses() > 0:
            return False

        source = seed_path or get_seed_path()
        if not source.exists():
            return False

        raw = source.read_text(encoding="utf-8")
        if raw.startswith("\ufeff"):
            raw = raw.lstrip("\ufeff")
        kb = json.loads(raw)

        body_system_ids: dict[str, int] = {}
        characteristic_ids: dict[str, int] = {}
        treatment_ids: dict[str, int] = {}

        try:
            for name in kb["body_systems"].keys():
                body_system_ids[name] = self.repo.create_body_system(name).id

            for char_name, char_data in kb["characteristics"].items():
                if char_data["type"] == "range":
                    item = self.repo.create_characteristic(
                        name=char_name,
                        type_name="range",
                        unit=char_data.get("unit", ""),
                        allowed_min=float(char_data["allowed"][0]),
                        allowed_max=float(char_data["allowed"][1]),
                        normal_min=float(char_data["normal"][0]),
                        normal_max=float(char_data["normal"][1]),
                        normal_enum_key=None,
                    )
                else:
                    item = self.repo.create_characteristic(
                        name=char_name,
                        type_name="enum",
                        unit=char_data.get("unit", ""),
                        allowed_min=None,
                        allowed_max=None,
                        normal_min=None,
                        normal_max=None,
                        normal_enum_key=str(char_data["normal"]),
                    )
                    for key, value in char_data["allowed"].items():
                        self.repo.add_characteristic_enum_option(
                            characteristic_id=item.id,
                            option_key=str(key),
                            option_value=str(value),
                        )

                characteristic_ids[char_name] = item.id

            for system_name, characteristic_names in kb["body_systems"].items():
                for characteristic_name in characteristic_names:
                    self.repo.add_body_system_characteristic(
                        body_system_id=body_system_ids[system_name],
                        characteristic_id=characteristic_ids[characteristic_name],
                    )

            for treatment_name, actions in kb["treatments"].items():
                treatment = self.repo.create_treatment(treatment_name)
                treatment_ids[treatment_name] = treatment.id
                for position, action in enumerate(actions):
                    self.repo.create_treatment_action(
                        treatment_id=treatment.id,
                        position=position,
                        action=action,
                    )

            for diagnosis_name, diagnosis_data in kb["diagnoses"].items():
                diagnosis = self.repo.create_diagnosis(
                    name=diagnosis_name,
                    icd10=diagnosis_data.get("icd10"),
                    treatment_id=treatment_ids[diagnosis_data["treatment"]],
                )

                for characteristic_name, expected in diagnosis_data.get("characteristics", {}).items():
                    if isinstance(expected, list):
                        self.repo.create_diagnosis_criterion(
                            diagnosis_id=diagnosis.id,
                            characteristic_id=characteristic_ids[characteristic_name],
                            expected_enum_key=None,
                            expected_min=float(expected[0]),
                            expected_max=float(expected[1]),
                        )
                    else:
                        self.repo.create_diagnosis_criterion(
                            diagnosis_id=diagnosis.id,
                            characteristic_id=characteristic_ids[characteristic_name],
                            expected_enum_key=str(expected),
                            expected_min=None,
                            expected_max=None,
                        )

            self.repo.commit()
            return True
        except Exception:
            self.repo.rollback()
            raise

    def export_snapshot(self, path: Path) -> None:
        body_system_map: dict[str, list[str]] = {}
        systems = self.session.query(BodySystem).all()
        for system in systems:
            names = sorted(link.characteristic.name for link in system.characteristics)
            body_system_map[system.name] = names

        characteristics = {}
        for item in self.repo.list_characteristics():
            serialized = self._serialize_characteristic(item)
            characteristics[item.name] = {
                "type": serialized["type"],
                "allowed": serialized["allowed"],
                "normal": serialized["normal"],
                "unit": serialized["unit"],
            }

        treatments = {}
        treatment_by_id = {}
        for treatment in self.repo.list_treatments():
            actions = [item.action for item in sorted(treatment.actions, key=lambda item: item.position)]
            treatments[treatment.name] = actions
            treatment_by_id[treatment.id] = treatment.name

        diagnoses = {}
        for diagnosis in self.repo.list_diagnoses():
            details = self.get_diagnosis_detail(diagnosis.id)
            if not details:
                continue
            diagnosis_chars: dict[str, Any] = {}
            for criterion in details["criteria"]:
                if criterion["characteristic_type"] == "range":
                    diagnosis_chars[criterion["characteristic_name"]] = [
                        criterion["expected_min"],
                        criterion["expected_max"],
                    ]
                else:
                    diagnosis_chars[criterion["characteristic_name"]] = criterion["expected_enum_key"]

            diagnoses[diagnosis.name] = {
                "icd10": diagnosis.icd10,
                "characteristics": diagnosis_chars,
                "treatment": treatment_by_id[diagnosis.treatment_id],
            }

        payload = {
            "body_systems": body_system_map,
            "characteristics": characteristics,
            "diagnoses": diagnoses,
            "treatments": treatments,
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
