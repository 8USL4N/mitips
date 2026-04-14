from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class BodySystem(Base):
    __tablename__ = "body_systems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    characteristics: Mapped[list["BodySystemCharacteristic"]] = relationship(
        back_populates="body_system", cascade="all, delete-orphan"
    )


class Characteristic(Base):
    __tablename__ = "characteristics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    allowed_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    allowed_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    normal_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    normal_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    normal_enum_key: Mapped[str | None] = mapped_column(String(32), nullable=True)

    enum_options: Mapped[list["CharacteristicEnumOption"]] = relationship(
        back_populates="characteristic", cascade="all, delete-orphan"
    )
    body_system_links: Mapped[list["BodySystemCharacteristic"]] = relationship(
        back_populates="characteristic", cascade="all, delete-orphan"
    )
    diagnosis_links: Mapped[list["DiagnosisCharacteristic"]] = relationship(
        back_populates="characteristic", cascade="all, delete-orphan"
    )


class CharacteristicEnumOption(Base):
    __tablename__ = "characteristic_enum_options"
    __table_args__ = (UniqueConstraint("characteristic_id", "option_key", name="uq_char_option_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    characteristic_id: Mapped[int] = mapped_column(ForeignKey("characteristics.id", ondelete="CASCADE"), nullable=False)
    option_key: Mapped[str] = mapped_column(String(32), nullable=False)
    option_value: Mapped[str] = mapped_column(String(255), nullable=False)

    characteristic: Mapped[Characteristic] = relationship(back_populates="enum_options")


class BodySystemCharacteristic(Base):
    __tablename__ = "body_system_characteristics"
    __table_args__ = (
        UniqueConstraint("body_system_id", "characteristic_id", name="uq_body_system_characteristic"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    body_system_id: Mapped[int] = mapped_column(ForeignKey("body_systems.id", ondelete="CASCADE"), nullable=False)
    characteristic_id: Mapped[int] = mapped_column(ForeignKey("characteristics.id", ondelete="CASCADE"), nullable=False)

    body_system: Mapped[BodySystem] = relationship(back_populates="characteristics")
    characteristic: Mapped[Characteristic] = relationship(back_populates="body_system_links")


class Treatment(Base):
    __tablename__ = "treatments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    actions: Mapped[list["TreatmentAction"]] = relationship(
        back_populates="treatment", cascade="all, delete-orphan", order_by="TreatmentAction.position"
    )
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="treatment")


class TreatmentAction(Base):
    __tablename__ = "treatment_actions"
    __table_args__ = (UniqueConstraint("treatment_id", "position", name="uq_treatment_action_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    treatment_id: Mapped[int] = mapped_column(ForeignKey("treatments.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)

    treatment: Mapped[Treatment] = relationship(back_populates="actions")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    icd10: Mapped[str | None] = mapped_column(String(32), nullable=True)
    treatment_id: Mapped[int] = mapped_column(ForeignKey("treatments.id", ondelete="RESTRICT"), nullable=False)

    treatment: Mapped[Treatment] = relationship(back_populates="diagnoses")
    criteria: Mapped[list["DiagnosisCharacteristic"]] = relationship(
        back_populates="diagnosis", cascade="all, delete-orphan"
    )


class DiagnosisCharacteristic(Base):
    __tablename__ = "diagnosis_characteristics"
    __table_args__ = (UniqueConstraint("diagnosis_id", "characteristic_id", name="uq_diagnosis_characteristic"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diagnosis_id: Mapped[int] = mapped_column(ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False)
    characteristic_id: Mapped[int] = mapped_column(ForeignKey("characteristics.id", ondelete="CASCADE"), nullable=False)
    expected_enum_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    expected_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    diagnosis: Mapped[Diagnosis] = relationship(back_populates="criteria")
    characteristic: Mapped[Characteristic] = relationship(back_populates="diagnosis_links")
