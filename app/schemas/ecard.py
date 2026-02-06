from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ECardResponse(BaseModel):
    """Payload minimal pour exposer la carte numérique d'une souscription."""

    subscription_id: int
    numero_souscription: str
    holder_name: str
    card_url: str
    card_expires_at: Optional[datetime] = None
    coverage_end_date: Optional[datetime] = None
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


