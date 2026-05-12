from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CharacteristicPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["range", "enum"]
    allowed: list[float] | dict[str, str]
    normal: list[float] | str
    unit: str = ""

    @model_validator(mode="after")
    def validate_consistency(self) -> "CharacteristicPayload":
        if self.type == "range":
            if not isinstance(self.allowed, list) or len(self.allowed) != 2:
                raise ValueError("For range type, 'allowed' must contain [min, max]")
            if not isinstance(self.normal, list) or len(self.normal) != 2:
                raise ValueError("For range type, 'normal' must contain [min, max]")
        else:
            if not isinstance(self.allowed, dict):
                raise ValueError("For enum type, 'allowed' must be a dictionary")
            if not isinstance(self.normal, str):
                raise ValueError("For enum type, 'normal' must be a string key")
        return self


class CharacteristicRead(CharacteristicPayload):
    id: int
    name: str


class CharacteristicCreateRequest(CharacteristicPayload):
    name: str


class CharacteristicUpdateRequest(CharacteristicPayload):
    name: str


class CharacteristicUsageRead(BaseModel):
    diagnosis_count: int
    body_system_count: int
    used_in_diagnoses: list[str] = Field(default_factory=list)
    used_in_body_systems: list[str] = Field(default_factory=list)


class BodySystemRead(BaseModel):
    id: int
    name: str
    characteristic_ids: list[int] = Field(default_factory=list)


class BodySystemUpsertRequest(BaseModel):
    name: str
    characteristic_ids: list[int] = Field(default_factory=list)

    @field_validator("characteristic_ids")
    @classmethod
    def validate_characteristic_ids(cls, value: list[int]) -> list[int]:
        seen = set()
        unique_values: list[int] = []
        for item in value:
            if item in seen:
                continue
            seen.add(item)
            unique_values.append(item)
        return unique_values


class DiagnosisCriterionInput(BaseModel):
    characteristic_id: int
    expected_enum_key: str | None = None
    expected_min: float | None = None
    expected_max: float | None = None


class DiagnosisCriterionRead(DiagnosisCriterionInput):
    id: int
    characteristic_name: str
    characteristic_type: str


class DiagnosisSummaryRead(BaseModel):
    id: int
    name: str
    icd10: str | None
    treatment_id: int
    treatment_name: str


class DiagnosisDetailRead(DiagnosisSummaryRead):
    criteria: list[DiagnosisCriterionRead]


class DiagnosisUpsertRequest(BaseModel):
    name: str
    icd10: str | None = None
    treatment_id: int | None = None
    criteria: list[DiagnosisCriterionInput] = Field(default_factory=list)


class TreatmentRead(BaseModel):
    id: int
    name: str
    actions: list[str]
    diagnosis_id: int | None = None
    diagnosis_name: str | None = None


class TreatmentActionsUpdateRequest(BaseModel):
    actions: list[str] = Field(default_factory=list)

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned


class TreatmentUpsertRequest(BaseModel):
    name: str
    actions: list[str] = Field(default_factory=list)
    diagnosis_id: int | None = None

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned


class SolveRequest(BaseModel):
    diagnosis_id: int
    patient_values: dict[str, Any] = Field(default_factory=dict)


class ExplanationRow(BaseModel):
    characteristic: str
    expected: str | float
    actual: str | float | None
    match: bool


class SolveResponse(BaseModel):
    diagnosis: str
    icd10: str | None
    treatment_name: str
    actions: list[str]
    explanation: list[ExplanationRow]
    matched_count: int
    total_count: int


class SolveBySymptomsRequest(BaseModel):
    patient_values: dict[str, Any] = Field(default_factory=dict)


class RankedCandidate(BaseModel):
    diagnosis_id: int
    diagnosis: str
    score: float
    source: Literal["hypothesis_refutation", "neural"]


class DiagnosisHypothesis(BaseModel):
    diagnosis_id: int
    diagnosis: str
    icd10: str | None
    treatment_name: str
    actions: list[str]
    explanation: list[ExplanationRow]
    rejection_reasons: list[ExplanationRow] = Field(default_factory=list)
    matched_count: int
    answered_count: int
    total_count: int
    missing_characteristics: list[str]


class SolveBySymptomsResponse(BaseModel):
    status: Literal["determined", "likely", "neural_selected", "not_determined"]
    message: str
    primary: DiagnosisHypothesis | None
    alternatives: list[DiagnosisHypothesis] = Field(default_factory=list)
    rejected_hypotheses: list[DiagnosisHypothesis] = Field(default_factory=list)
    selection_method: Literal["hypothesis_refutation", "neural", "fallback"]
    confidence: float | None = None
    ranked_candidates: list[RankedCandidate] = Field(default_factory=list)
