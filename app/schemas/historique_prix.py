from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class HistoriquePrixBase(BaseModel):
    ancien_prix: Optional[Decimal] = None
    nouveau_prix: Decimal
    raison_modification: Optional[str] = None


class HistoriquePrixCreate(HistoriquePrixBase):
    produit_assurance_id: int
    modifie_par_user_id: Optional[int] = None


class HistoriquePrixResponse(HistoriquePrixBase):
    id: int
    produit_assurance_id: int
    modifie_par_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
