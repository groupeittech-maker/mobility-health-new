from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse
from app.schemas.contact_proche import ContactProcheCreate, ContactProcheUpdate, ContactProcheResponse
from app.schemas.produit_assurance import ProduitAssuranceCreate, ProduitAssuranceUpdate, ProduitAssuranceResponse
from app.schemas.projet_voyage import ProjetVoyageCreate, ProjetVoyageUpdate, ProjetVoyageResponse
from app.schemas.souscription import SouscriptionCreate, SouscriptionUpdate, SouscriptionResponse
from app.schemas.paiement import PaiementCreate, PaiementUpdate, PaiementResponse
from app.schemas.assureur import AssureurCreate, AssureurUpdate, AssureurResponse
from app.schemas.audit import AuditLogResponse

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "ContactProcheCreate",
    "ContactProcheUpdate",
    "ContactProcheResponse",
    "ProduitAssuranceCreate",
    "ProduitAssuranceUpdate",
    "ProduitAssuranceResponse",
    "ProjetVoyageCreate",
    "ProjetVoyageUpdate",
    "ProjetVoyageResponse",
    "SouscriptionCreate",
    "SouscriptionUpdate",
    "SouscriptionResponse",
    "PaiementCreate",
    "PaiementUpdate",
    "PaiementResponse",
    "AssureurCreate",
    "AssureurUpdate",
    "AssureurResponse",
    "AuditLogResponse",
]
