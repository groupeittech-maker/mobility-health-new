from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SubscriptionDecisionResult(BaseModel):
    souscription_id: int
    numero_souscription: Optional[str] = None
    decision: str  # approve | reject | review
    primary_step: Optional[str] = None  # medical | technical | production
    review_steps: List[str] = []
    reasons: List[str] = []
    risk_score: int = 0
    statut: str

    model_config = ConfigDict(from_attributes=True)


class SubscriptionReviewRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None


class VoyageurInfo(BaseModel):
    """Optionnel : âge du voyageur bénéficiaire (utile pour enfant / tiers)."""
    voyageur_age: Optional[int] = None
    voyageur_date_naissance: Optional[str] = None
