import json
import math
import re
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
    def _count_non_russian_cyrillic(value: str) -> int:
        count = 0
        for char in value:
            code = ord(char)
            if 0x0400 <= code <= 0x04FF and not (
                0x0410 <= code <= 0x044F or code in {0x0401, 0x0451}
            ):
                count += 1
        return count

    @classmethod
    def _text_quality(cls, value: str) -> int:
        cyrillic = sum(1 for char in value if "\u0400" <= char <= "\u04FF")
        bad_latin_markers = sum(value.count(marker) for marker in ("Ã", "Â", "Ð", "Ñ", "�"))
        suspicious_pairs = len(re.findall(r"(?:Р.|С.)", value))
        non_russian_cyr = cls._count_non_russian_cyrillic(value)
        return (cyrillic * 2) - (bad_latin_markers * 10) - (suspicious_pairs * 2) - (non_russian_cyr * 5)

    @classmethod
    def _repair_mojibake_text(cls, value: str) -> str:
        if not value:
            return value

        candidates: set[str] = {value}
        frontier = [value]
        for _ in range(3):
            next_frontier: list[str] = []
            for text in frontier:
                for encoding in ("cp1251", "latin1", "cp1252"):
                    try:
                        candidate = text.encode(encoding).decode("utf-8")
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        continue
                    if candidate not in candidates:
                        candidates.add(candidate)
                        next_frontier.append(candidate)
            if not next_frontier:
                break
            frontier = next_frontier

        original_score = cls._text_quality(value)
        best = max(candidates, key=cls._text_quality)
        if best != value and cls._text_quality(best) >= original_score + 3:
            return best
        return value

    @classmethod
    def _serialize_characteristic(cls, item) -> dict[str, Any]:
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
            allowed = {row.option_key: cls._repair_mojibake_text(row.option_value) for row in options}
            normal = item.normal_enum_key or ""

        return {
            "id": item.id,
            "name": cls._repair_mojibake_text(item.name),
            "type": item.type,
            "unit": cls._repair_mojibake_text(item.unit),
            "allowed": allowed,
            "normal": normal,
        }

    @classmethod
    def _serialize_treatment(cls, item) -> dict[str, Any]:
        actions = [cls._repair_mojibake_text(row.action) for row in sorted(item.actions, key=lambda row: row.position)]
        return {
            "id": item.id,
            "name": cls._repair_mojibake_text(item.name),
            "actions": actions,
        }

    @classmethod
    def _serialize_criterion(cls, row) -> dict[str, Any]:
        return {
            "id": row.id,
            "characteristic_id": row.characteristic_id,
            "characteristic_name": cls._repair_mojibake_text(row.characteristic.name),
            "characteristic_type": row.characteristic.type,
            "characteristic_unit": cls._repair_mojibake_text(row.characteristic.unit),
            "expected_enum_key": row.expected_enum_key,
            "expected_min": row.expected_min,
            "expected_max": row.expected_max,
        }

    @classmethod
    def _serialize_diagnosis_summary(cls, item) -> dict[str, Any]:
        return {
            "id": item.id,
            "name": cls._repair_mojibake_text(item.name),
            "icd10": item.icd10,
            "treatment_id": item.treatment_id,
            "treatment_name": cls._repair_mojibake_text(item.treatment.name),
        }

    @classmethod
    def _serialize_body_system(cls, item) -> dict[str, Any]:
        characteristic_ids = [link.characteristic_id for link in item.characteristics]
        characteristic_ids.sort()
        return {
            "id": item.id,
            "name": cls._repair_mojibake_text(item.name),
            "characteristic_ids": characteristic_ids,
        }

    def list_diagnoses(self) -> list[dict[str, Any]]:
        rows = self.repo.list_diagnoses()
        return [self._serialize_diagnosis_summary(row) for row in rows]

    def list_body_systems(self) -> list[dict[str, Any]]:
        rows = self.repo.list_body_systems()
        return [self._serialize_body_system(row) for row in rows]

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

    @staticmethod
    def _parse_float(value: Any, field_name: str) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"\u041f\u043e\u043b\u0435 '{field_name}' \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u0447\u0438\u0441\u043b\u043e\u043c"
            ) from exc
        if not math.isfinite(parsed):
            raise ValueError(
                f"\u041f\u043e\u043b\u0435 '{field_name}' \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u043a\u043e\u043d\u0435\u0447\u043d\u044b\u043c \u0447\u0438\u0441\u043b\u043e\u043c"
            )
        return parsed

    @classmethod
    def _normalize_characteristic_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("Название характеристики обязательно")

        type_name = payload.get("type")
        if type_name not in {"range", "enum"}:
            raise ValueError("type должен быть 'range' или 'enum'")

        unit = str(payload.get("unit", "") or "").strip()
        allowed = payload.get("allowed")
        normal = payload.get("normal")

        if type_name == "range":
            if not isinstance(allowed, list) or len(allowed) != 2:
                raise ValueError("Для range 'allowed' должен быть массивом из двух чисел [min, max]")
            if not isinstance(normal, list) or len(normal) != 2:
                raise ValueError("Для range 'normal' должен быть массивом из двух чисел [min, max]")

            allowed_min = cls._parse_float(allowed[0], "allowed[0]")
            allowed_max = cls._parse_float(allowed[1], "allowed[1]")
            normal_min = cls._parse_float(normal[0], "normal[0]")
            normal_max = cls._parse_float(normal[1], "normal[1]")

            if allowed_min > allowed_max:
                raise ValueError("allowed_min не может быть больше allowed_max")
            if normal_min > normal_max:
                raise ValueError("normal_min не может быть больше normal_max")
            if normal_min < allowed_min or normal_max > allowed_max:
                raise ValueError("normal должен находиться внутри allowed")

            return {
                "name": name,
                "type": "range",
                "unit": unit,
                "allowed": [allowed_min, allowed_max],
                "normal": [normal_min, normal_max],
            }

        if not isinstance(allowed, dict) or not allowed:
            raise ValueError("Для enum 'allowed' должен быть непустым объектом ключ-значение")
        if not isinstance(normal, str):
            raise ValueError("Для enum 'normal' должен быть строковым ключом")

        normalized_allowed: dict[str, str] = {}
        for key, value in allowed.items():
            option_key = str(key).strip()
            option_value = str(value).strip()
            if not option_key:
                raise ValueError("Ключ enum не может быть пустым")
            if not option_value:
                raise ValueError("Значение enum не может быть пустым")
            normalized_allowed[option_key] = option_value

        normal_key = normal.strip()
        if normal_key not in normalized_allowed:
            raise ValueError("normal должен быть одним из ключей allowed")

        return {
            "name": name,
            "type": "enum",
            "unit": unit,
            "allowed": normalized_allowed,
            "normal": normal_key,
        }

    def _characteristic_usage(self, characteristic_id: int) -> tuple[list[str], list[str]]:
        diagnoses = self.repo.list_diagnoses_using_characteristic(characteristic_id)
        systems = self.repo.list_body_systems_using_characteristic(characteristic_id)
        diagnosis_names = sorted(item.name for item in diagnoses)
        system_names = sorted(item.name for item in systems)
        return diagnosis_names, system_names

    def get_characteristic_detail(self, characteristic_id: int) -> dict[str, Any] | None:
        row = self.repo.get_characteristic(characteristic_id)
        if not row:
            return None
        return self._serialize_characteristic(row)

    def get_characteristic_usage(self, characteristic_id: int) -> dict[str, Any]:
        row = self.repo.get_characteristic(characteristic_id)
        if not row:
            raise ValueError("Характеристика не найдена")
        used_in_diagnoses, used_in_body_systems = self._characteristic_usage(characteristic_id)
        return {
            "diagnosis_count": len(used_in_diagnoses),
            "body_system_count": len(used_in_body_systems),
            "used_in_diagnoses": used_in_diagnoses,
            "used_in_body_systems": used_in_body_systems,
        }

    def create_characteristic(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_characteristic_payload(payload)
        if self.repo.get_characteristic_by_name(normalized["name"]):
            raise ValueError("Характеристика с таким названием уже существует")

        if normalized["type"] == "range":
            item = self.repo.create_characteristic(
                name=normalized["name"],
                type_name="range",
                unit=normalized["unit"],
                allowed_min=normalized["allowed"][0],
                allowed_max=normalized["allowed"][1],
                normal_min=normalized["normal"][0],
                normal_max=normalized["normal"][1],
                normal_enum_key=None,
            )
        else:
            item = self.repo.create_characteristic(
                name=normalized["name"],
                type_name="enum",
                unit=normalized["unit"],
                allowed_min=None,
                allowed_max=None,
                normal_min=None,
                normal_max=None,
                normal_enum_key=normalized["normal"],
            )
            for key, value in normalized["allowed"].items():
                self.repo.add_characteristic_enum_option(
                    characteristic_id=item.id,
                    option_key=key,
                    option_value=value,
                )

        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось создать характеристику")

        created = self.repo.get_characteristic(item.id)
        if not created:
            raise ValueError("Не удалось загрузить созданную характеристику")
        return self._serialize_characteristic(created)

    def update_characteristic(
        self,
        characteristic_id: int,
        payload: dict[str, Any],
        force: bool = False,
    ) -> dict[str, Any] | None:
        characteristic = self.repo.get_characteristic(characteristic_id)
        if not characteristic:
            return None

        normalized = self._normalize_characteristic_payload(payload)
        duplicate = self.repo.get_characteristic_by_name(normalized["name"])
        if duplicate and duplicate.id != characteristic_id:
            raise ValueError("Характеристика с таким названием уже существует")

        diagnosis_names, _ = self._characteristic_usage(characteristic_id)
        in_use = bool(diagnosis_names)

        if characteristic.type != normalized["type"] and in_use and not force:
            raise ValueError(
                "Нельзя изменить тип характеристики, которая используется в диагнозах. "
                "Удалите связи или используйте force=true."
            )

        if normalized["type"] == "range":
            if characteristic.type == "range":
                if in_use:
                    criteria_rows = self.repo.list_diagnosis_characteristics_by_characteristic(characteristic_id)
                    allowed_min, allowed_max = normalized["allowed"]
                    for row in criteria_rows:
                        if row.expected_min is None or row.expected_max is None:
                            continue
                        if row.expected_min < allowed_min or row.expected_max > allowed_max:
                            raise ValueError(
                                "Новый диапазон allowed конфликтует с существующими критериями диагнозов"
                            )
            elif in_use and not force:
                raise ValueError("Смена enum -> range запрещена для используемой характеристики без force=true")

            characteristic.type = "range"
            characteristic.name = normalized["name"]
            characteristic.unit = normalized["unit"]
            characteristic.allowed_min = normalized["allowed"][0]
            characteristic.allowed_max = normalized["allowed"][1]
            characteristic.normal_min = normalized["normal"][0]
            characteristic.normal_max = normalized["normal"][1]
            characteristic.normal_enum_key = None
            self.repo.clear_characteristic_enum_options(characteristic_id)
        else:
            new_allowed = normalized["allowed"]
            if characteristic.type == "enum" and in_use:
                criteria_rows = self.repo.list_diagnosis_characteristics_by_characteristic(characteristic_id)
                used_keys = {
                    str(row.expected_enum_key)
                    for row in criteria_rows
                    if row.expected_enum_key is not None
                }
                removed_keys = [key for key in used_keys if key not in new_allowed]
                if removed_keys and not force:
                    raise ValueError(
                        "Нельзя удалить enum-ключи, используемые в критериях диагнозов: "
                        + ", ".join(sorted(removed_keys))
                    )

            if characteristic.type != "enum" and in_use and not force:
                raise ValueError("Смена range -> enum запрещена для используемой характеристики без force=true")

            characteristic.type = "enum"
            characteristic.name = normalized["name"]
            characteristic.unit = normalized["unit"]
            characteristic.allowed_min = None
            characteristic.allowed_max = None
            characteristic.normal_min = None
            characteristic.normal_max = None
            characteristic.normal_enum_key = normalized["normal"]
            self.repo.clear_characteristic_enum_options(characteristic_id)
            for key, value in new_allowed.items():
                self.repo.add_characteristic_enum_option(
                    characteristic_id=characteristic_id,
                    option_key=key,
                    option_value=value,
                )

        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось обновить характеристику")

        updated = self.repo.get_characteristic(characteristic_id)
        if not updated:
            return None
        return self._serialize_characteristic(updated)

    def delete_characteristic(self, characteristic_id: int, force: bool = False) -> bool:
        characteristic = self.repo.get_characteristic(characteristic_id)
        if not characteristic:
            return False

        diagnosis_names, system_names = self._characteristic_usage(characteristic_id)
        if (diagnosis_names or system_names) and not force:
            raise ValueError(
                "Характеристика используется и не может быть удалена. "
                f"Диагнозы: {', '.join(diagnosis_names) or '-'}; "
                f"Системы: {', '.join(system_names) or '-'}"
            )

        self.repo.delete_characteristic(characteristic)
        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось удалить характеристику")
        return True

    def get_treatment_detail(self, treatment_id: int) -> dict[str, Any] | None:
        row = self.repo.get_treatment(treatment_id)
        if not row:
            return None
        return self._serialize_treatment(row)

    def _validate_body_system_characteristics(self, characteristic_ids: list[int]) -> None:
        if not characteristic_ids:
            return
        mapped = self.repo.get_characteristics_by_ids(characteristic_ids)
        if len(mapped) != len(set(characteristic_ids)):
            raise ValueError("Одна или несколько характеристик не найдены")

    def create_body_system(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.repo.get_body_system_by_name(payload["name"]):
            raise ValueError("Система организма с таким названием уже существует")

        characteristic_ids = payload.get("characteristic_ids", [])
        self._validate_body_system_characteristics(characteristic_ids)

        body_system = self.repo.create_body_system(payload["name"])
        for characteristic_id in characteristic_ids:
            self.repo.add_body_system_characteristic(
                body_system_id=body_system.id,
                characteristic_id=characteristic_id,
            )

        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось сохранить систему организма")

        created = self.repo.get_body_system(body_system.id)
        if not created:
            raise ValueError("Не удалось загрузить созданную систему организма")
        return self._serialize_body_system(created)

    def update_body_system(self, body_system_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        body_system = self.repo.get_body_system(body_system_id)
        if not body_system:
            return None

        duplicate = self.repo.get_body_system_by_name(payload["name"])
        if duplicate and duplicate.id != body_system_id:
            raise ValueError("Система организма с таким названием уже существует")

        characteristic_ids = payload.get("characteristic_ids", [])
        self._validate_body_system_characteristics(characteristic_ids)

        body_system.name = payload["name"]
        self.repo.clear_body_system_characteristics(body_system.id)
        for characteristic_id in characteristic_ids:
            self.repo.add_body_system_characteristic(
                body_system_id=body_system.id,
                characteristic_id=characteristic_id,
            )

        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось обновить систему организма")

        updated = self.repo.get_body_system(body_system.id)
        if not updated:
            return None
        return self._serialize_body_system(updated)

    def delete_body_system(self, body_system_id: int) -> bool:
        body_system = self.repo.get_body_system(body_system_id)
        if not body_system:
            return False

        self.repo.delete_body_system(body_system)
        self.repo.commit()
        return True

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
                expected_min_f = self._parse_float(expected_min, "expected_min")
                expected_max_f = self._parse_float(expected_max, "expected_max")
                if expected_min_f > expected_max_f:
                    raise ValueError(
                        f"Для характеристики '{characteristic.name}' expected_min не может быть больше expected_max"
                    )
                if characteristic.allowed_min is not None and expected_min_f < float(characteristic.allowed_min):
                    raise ValueError(
                        f"expected_min для '{characteristic.name}' выходит за пределы allowed"
                    )
                if characteristic.allowed_max is not None and expected_max_f > float(characteristic.allowed_max):
                    raise ValueError(
                        f"expected_max для '{characteristic.name}' выходит за пределы allowed"
                    )
            elif characteristic.type == "enum":
                if expected_enum_key is None:
                    raise ValueError(
                        f"Для характеристики '{characteristic.name}' требуется expected_enum_key"
                    )
                allowed = {row.option_key for row in characteristic.enum_options}
                if str(expected_enum_key) not in allowed:
                    raise ValueError(
                        f"Для характеристики '{characteristic.name}' неизвестный expected_enum_key='{expected_enum_key}'"
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

    def create_treatment(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("Название лечения обязательно")
        actions = [str(item).strip() for item in payload.get("actions", []) if str(item).strip()]

        if self.repo.get_treatment_by_name(name):
            raise ValueError("Лечение с таким названием уже существует")

        treatment = self.repo.create_treatment(name)
        for position, action in enumerate(actions):
            self.repo.create_treatment_action(treatment_id=treatment.id, position=position, action=action)

        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось создать лечение")

        created = self.repo.get_treatment(treatment.id)
        if not created:
            raise ValueError("Не удалось загрузить созданное лечение")
        return self._serialize_treatment(created)

    def update_treatment(self, treatment_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        treatment = self.repo.get_treatment(treatment_id)
        if not treatment:
            return None

        name = str(payload.get("name", "")).strip()
        if not name:
            raise ValueError("Название лечения обязательно")
        actions = [str(item).strip() for item in payload.get("actions", []) if str(item).strip()]

        duplicate = self.repo.get_treatment_by_name(name)
        if duplicate and duplicate.id != treatment_id:
            raise ValueError("Лечение с таким названием уже существует")

        treatment.name = name
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

    def delete_treatment(self, treatment_id: int) -> bool:
        treatment = self.repo.get_treatment(treatment_id)
        if not treatment:
            return False

        linked_diagnoses = self.repo.list_diagnoses_using_treatment(treatment_id)
        if linked_diagnoses:
            names = ", ".join(item.name for item in linked_diagnoses)
            raise ValueError(
                f"Лечение используется в диагнозах: {names}. Сначала назначьте другое лечение."
            )

        self.repo.delete_treatment(treatment)
        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise ValueError("Не удалось удалить лечение")
        return True


    def repair_mojibake_in_db(self) -> int:
        changed = 0

        for body_system in self.repo.list_body_systems():
            fixed_name = self._repair_mojibake_text(body_system.name)
            if fixed_name != body_system.name:
                body_system.name = fixed_name
                changed += 1

        for characteristic in self.repo.list_characteristics():
            fixed_name = self._repair_mojibake_text(characteristic.name)
            if fixed_name != characteristic.name:
                characteristic.name = fixed_name
                changed += 1

            fixed_unit = self._repair_mojibake_text(characteristic.unit or "")
            if fixed_unit != (characteristic.unit or ""):
                characteristic.unit = fixed_unit
                changed += 1

            for option in characteristic.enum_options:
                fixed_option_value = self._repair_mojibake_text(option.option_value)
                if fixed_option_value != option.option_value:
                    option.option_value = fixed_option_value
                    changed += 1

        for treatment in self.repo.list_treatments():
            fixed_name = self._repair_mojibake_text(treatment.name)
            if fixed_name != treatment.name:
                treatment.name = fixed_name
                changed += 1

            for action in treatment.actions:
                fixed_action = self._repair_mojibake_text(action.action)
                if fixed_action != action.action:
                    action.action = fixed_action
                    changed += 1

        for diagnosis in self.repo.list_diagnoses():
            fixed_name = self._repair_mojibake_text(diagnosis.name)
            if fixed_name != diagnosis.name:
                diagnosis.name = fixed_name
                changed += 1

        if not changed:
            return 0

        try:
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            return 0
        return changed

    def get_solver_payload(self, diagnosis_id: int) -> dict[str, Any] | None:
        diagnosis = self.repo.get_diagnosis(diagnosis_id)
        if not diagnosis:
            return None

        return {
            "id": diagnosis.id,
            "name": self._repair_mojibake_text(diagnosis.name),
            "icd10": diagnosis.icd10,
            "treatment_name": self._repair_mojibake_text(diagnosis.treatment.name),
            "actions": [
                self._repair_mojibake_text(row.action)
                for row in sorted(diagnosis.treatment.actions, key=lambda row: row.position)
            ],
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
