from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, AliasChoices


class HospitalStayBase(BaseModel):
    doctor_id: int
    orientation_notes: Optional[str] = None


class HospitalStayCreate(HospitalStayBase):
    pass


class HospitalStayReportUpdate(BaseModel):
    motif_consultation: Optional[str] = None
    motif_hospitalisation: Optional[str] = None
    duree_sejour_heures: Optional[int] = Field(default=None, ge=0)
    actes_effectues: List[str] = Field(default_factory=list)
    examens_effectues: List[str] = Field(default_factory=list)
    resume: Optional[str] = None
    observations: Optional[str] = None
    terminer_sejour: bool = False


class HospitalStayValidationRequest(BaseModel):
    approve: bool
    notes: Optional[str] = None


class HospitalStayInvoiceLine(BaseModel):
    libelle: str = Field(..., min_length=1, max_length=200)
    quantite: int = Field(default=1, ge=1, le=10000)
    prix_unitaire: Decimal = Field(..., ge=0)

    @field_validator("libelle")
    @classmethod
    def _strip_label(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Le libellé de la ligne est requis.")
        return trimmed

    @field_validator("prix_unitaire")
    @classmethod
    def _normalize_amount(cls, value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))


class HospitalStayInvoiceRequest(BaseModel):
    taux_tva: Decimal = Field(default=Decimal("0.18"), ge=0, le=1)
    notes: Optional[str] = None
    lines: List[HospitalStayInvoiceLine] = Field(
        default_factory=list,
        validation_alias=AliasChoices("lines", "invoice_lines"),
    )

    model_config = ConfigDict(populate_by_name=True)


class HospitalStayDoctorSummary(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None

    model_config = {"from_attributes": True}


class HospitalStayPatientSummary(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None

    model_config = {"from_attributes": True}


class HospitalStaySinistreSummary(BaseModel):
    id: int
    numero_sinistre: Optional[str] = None
    statut: Optional[str] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class HospitalStayInvoiceSummary(BaseModel):
    id: int
    numero_facture: str
    statut: str
    montant_ttc: Decimal
    created_at: datetime
    validation_medicale: Optional[str] = None
    validation_sinistre: Optional[str] = None
    validation_compta: Optional[str] = None

    model_config = {"from_attributes": True}


class HospitalSummaryForStay(BaseModel):
    """Résumé hôpital (nom, ville) pour l'historique mobile."""

    id: int
    nom: Optional[str] = None
    ville: Optional[str] = None
    adresse: Optional[str] = None

    model_config = {"from_attributes": True}


class HospitalStayResponse(BaseModel):
    id: int
    sinistre_id: int
    hospital_id: int
    hospital: Optional[HospitalSummaryForStay] = None
    patient_id: Optional[int] = None
    patient: Optional[HospitalStayPatientSummary] = None
    doctor_id: Optional[int] = Field(default=None, validation_alias=AliasChoices("doctor_id", "assigned_doctor_id"))
    assigned_doctor: Optional[HospitalStayDoctorSummary] = None
    sinistre: Optional[HospitalStaySinistreSummary] = None
    created_by_id: Optional[int] = None
    status: str
    report_status: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    orientation_notes: Optional[str] = None
    report_motif_consultation: Optional[str] = None
    report_motif_hospitalisation: Optional[str] = None
    report_duree_sejour_heures: Optional[int] = None
    report_actes: List[str] = Field(default_factory=list)
    report_examens: List[str] = Field(default_factory=list)
    report_resume: Optional[str] = None
    report_observations: Optional[str] = None
    report_submitted_at: Optional[datetime] = None
    validated_by_id: Optional[int] = None
    validated_at: Optional[datetime] = None
    validation_notes: Optional[str] = None
    invoice: Optional[HospitalStayInvoiceSummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("report_actes", "report_examens", mode="before")
    @classmethod
    def _coerce_lists(cls, value):
        if value is None:
            return []
        return value


class HospitalStayOptionsResponse(BaseModel):
    actes: List[str]
    examens: List[str]