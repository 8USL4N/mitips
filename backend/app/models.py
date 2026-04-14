from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CharacteristicSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["range", "enum"]
    allowed: list[float] | dict[str, str]
    normal: list[float] | str
    unit: str = ""

    @model_validator(mode="after")
    def validate_consistency(self) -> "CharacteristicSchema":
        if self.type == "range":
            if not isinstance(self.allowed, list) or len(self.allowed) != 2:
                raise ValueError("For range type, 'allowed' must contain [min, max]")
            if not isinstance(self.normal, list) or len(self.normal) != 2:
                raise ValueError("For range type, 'normal' must contain [min, max]")
        if self.type == "enum":
            if not isinstance(self.allowed, dict):
                raise ValueError("For enum type, 'allowed' must be a dictionary")
            if not isinstance(self.normal, str):
                raise ValueError("For enum type, 'normal' must be a string key")
        return self


class DiagnosisSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    icd10: str | None
    characteristics: dict[str, str | list[float]]
    treatment: str


class KnowledgeBaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body_systems: dict[str, list[str]]
    characteristics: dict[str, CharacteristicSchema]
    diagnoses: dict[str, DiagnosisSchema]
    treatments: dict[str, list[str]]


class SolveRequest(BaseModel):
    diagnosis: str
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


class DiagnosisUpsertRequest(BaseModel):
    icd10: str | None = None
    characteristics: dict[str, str | list[float]] = Field(default_factory=dict)
    treatment: str


class TreatmentUpdateRequest(BaseModel):
    actions: list[str] = Field(default_factory=list)

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned
