from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class DocumentReviewInline(BaseModel):
    """Pièce jointe du projet de voyage, pour consultation depuis le modal de révision."""
    id: int
    doc_type: str
    display_name: str
    content_type: Optional[str] = None
    file_size: int
    uploaded_at: Optional[datetime] = None
    download_url: Optional[str] = None


class AttestationBase(BaseModel):
    type_attestation: str  # 'provisoire' ou 'definitive'
    numero_attestation: str
    chemin_fichier_minio: str
    bucket_minio: str = "attestations"
    est_valide: bool = True
    notes: Optional[str] = None


class AttestationCreate(AttestationBase):
    souscription_id: int
    paiement_id: Optional[int] = None


class AttestationResponse(AttestationBase):
    id: int
    souscription_id: int
    paiement_id: Optional[int]
    url_signee: Optional[str]
    date_expiration_url: Optional[datetime]
    carte_numerique_path: Optional[str] = None
    carte_numerique_bucket: Optional[str] = None
    carte_numerique_url: Optional[str] = None
    carte_numerique_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AttestationWithURLResponse(BaseModel):
    id: int
    type_attestation: str
    numero_attestation: str
    url_signee: str
    date_expiration_url: Optional[datetime] = None
    carte_numerique_url: Optional[str] = None
    carte_numerique_expires_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AttestationVerificationResponse(BaseModel):
    numero_attestation: str
    type_attestation: str
    est_valide: bool
    souscription_numero: str
    statut_souscription: str
    message: str
    created_at: datetime


class QuestionnaireInline(BaseModel):
    id: int
    type_questionnaire: str
    version: int
    statut: str
    reponses: Dict[str, Any]
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValidationState(BaseModel):
    status: str
    notes: Optional[str] = None
    reviewer_id: Optional[int] = None
    decided_at: Optional[datetime] = None


class AttestationReviewItem(BaseModel):
    attestation_id: int
    attestation_type: str
    numero_attestation: str
    attestation_created_at: datetime
    souscription_id: int
    numero_souscription: str
    souscription_status: str
    prix_applique: Optional[float] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    # Informations personnelles de l'utilisateur depuis l'inscription
    client_date_naissance: Optional[date] = None
    client_telephone: Optional[str] = None
    client_sexe: Optional[str] = None  # 'M', 'F', 'Autre'
    client_nationalite: Optional[str] = None
    client_numero_passeport: Optional[str] = None
    client_validite_passeport: Optional[date] = None
    client_pays_residence: Optional[str] = None
    client_contact_urgence: Optional[str] = None
    # Données médicales depuis l'inscription (complétées par le questionnaire médical)
    client_maladies_chroniques: Optional[str] = None
    client_traitements_en_cours: Optional[str] = None
    client_antecedents_recents: Optional[str] = None
    client_grossesse: Optional[bool] = None
    produit_nom: Optional[str] = None
    # Informations du tiers (bénéficiaire) si la souscription est pour un tiers
    is_tier_subscription: Optional[bool] = False
    tier_full_name: Optional[str] = None
    tier_birth_date: Optional[str] = None
    tier_gender: Optional[str] = None
    tier_nationality: Optional[str] = None
    tier_passport_number: Optional[str] = None
    tier_passport_expiry_date: Optional[str] = None
    tier_phone: Optional[str] = None
    tier_email: Optional[str] = None
    tier_address: Optional[str] = None
    validation_type: str
    validation_status: str
    validations: Dict[str, ValidationState]
    questionnaires: Dict[str, QuestionnaireInline | None]
    documents_projet_voyage: Optional[List[DocumentReviewInline]] = None
    # Enfants mineurs à charge (extraits des notes souscription / projet)
    minors_info: Optional[List[Dict[str, str]]] = None  # [{"nom_complet": "...", "date_naissance": "..."}]