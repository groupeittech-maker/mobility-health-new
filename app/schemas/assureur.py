from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


class AgentComptableSummary(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AgentSummary(BaseModel):
    """Résumé d'un agent (comptable, production, sinistre)"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    type_agent: str  # 'comptable', 'production', 'sinistre'

    model_config = ConfigDict(from_attributes=True)


class AssureurBase(BaseModel):
    nom: str
    pays: str
    logo_url: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    agent_comptable_id: Optional[int] = None  # Rétrocompatibilité
    # Nouveaux champs pour les listes d'agents
    agents_comptables_ids: Optional[List[int]] = None
    agents_production_ids: Optional[List[int]] = None
    agents_sinistre_ids: Optional[List[int]] = None


class AssureurCreate(AssureurBase):
    pass


class AssureurUpdate(BaseModel):
    nom: Optional[str] = None
    pays: Optional[str] = None
    logo_url: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    agent_comptable_id: Optional[int] = None  # Rétrocompatibilité
    # Nouveaux champs pour les listes d'agents
    agents_comptables_ids: Optional[List[int]] = None
    agents_production_ids: Optional[List[int]] = None
    agents_sinistre_ids: Optional[List[int]] = None


class AssureurResponse(AssureurBase):
    id: int
    agent_comptable: Optional[AgentComptableSummary] = None  # Rétrocompatibilité
    agents: Optional[List[AgentSummary]] = None  # Nouveaux agents
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssureurSummaryForProduct(BaseModel):
    """
    Résumé assureur pour l'embed dans la réponse produit (liste produits, sélection produit).
    Sans agents ni agent_comptable pour éviter la sérialisation d'objets AssureurAgent.
    """
    id: int
    nom: str
    pays: str
    logo_url: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


