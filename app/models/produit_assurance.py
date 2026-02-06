from sqlalchemy import Column, Integer, String, Numeric, Text, Boolean, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.enums import CleRepartition
from app.models.base import TimestampMixin


class ProduitAssurance(Base, TimestampMixin):
    """Modèle pour les produits d'assurance"""
    __tablename__ = "produits_assurance"
    
    # 1. Informations générales du produit
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    nom = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), nullable=True)  # Version du produit
    est_actif = Column(Boolean, default=True, nullable=False)
    assureur = Column(String(200), nullable=True)  # Nom de l'assureur (legacy string)
    assureur_id = Column(Integer, ForeignKey("assureurs.id", ondelete="SET NULL"), nullable=True, index=True)
    image_url = Column(String(500), nullable=True)  # URL de l'image/miniature du produit
    
    # Coût et répartition
    cout = Column(Numeric(10, 2), nullable=False)  # Coût de base du produit
    currency = Column(String(10), nullable=True, default="XAF")  # Devise (XAF pour franc CFA d'Afrique centrale)
    cle_repartition = Column(SQLEnum(CleRepartition), nullable=False, default=CleRepartition.FIXE)
    # Pourcentage de commission reversé à l'assureur (souscription payée). Dépend du produit et du type de transaction.
    commission_assureur_pct = Column(Numeric(5, 2), nullable=True, default=30)
    
    # 2. Zone géographique couverte (JSON)
    zones_geographiques = Column(JSON, nullable=True)  # {zones: [], pays_eligibles: [], pays_exclus: [], specificites: []}
    
    # 3. Durée du voyage
    duree_min_jours = Column(Integer, nullable=True)  # Durée minimale du séjour
    duree_max_jours = Column(Integer, nullable=True)  # Durée maximale du séjour
    duree_validite_jours = Column(Integer, nullable=True)  # Durée de validité en jours
    reconduction_possible = Column(Boolean, default=False, nullable=False)
    couverture_multi_entrees = Column(Boolean, default=False, nullable=False)
    
    # 4. Profil des assurés
    age_minimum = Column(Integer, nullable=True)
    age_maximum = Column(Integer, nullable=True)
    conditions_sante = Column(Text, nullable=True)  # Conditions de santé particulières
    categories_assures = Column(JSON, nullable=True)  # Liste des catégories: ["individuel", "famille", etc.]
    
    # 5. Garanties incluses (JSON structuré)
    garanties = Column(JSON, nullable=True)  # Liste structurée de garanties avec détails

    # Primes générées (JSON) : { prime_nette, accessoire, taxes, prime_total }
    primes_generees = Column(JSON, nullable=True)
    
    # 6. Exclusions générales
    exclusions_generales = Column(JSON, nullable=True)  # Liste des exclusions générales
    
    # Champs legacy (conservés pour compatibilité)
    conditions = Column(Text, nullable=True)  # Conditions générales (texte libre)
    conditions_generales_pdf_url = Column(String(500), nullable=True)  # URL du PDF des conditions générales
    
    # Relations
    souscriptions = relationship("Souscription", back_populates="produit_assurance")
    historique_prix = relationship("HistoriquePrix", back_populates="produit_assurance", cascade="all, delete-orphan")
    assureur_obj = relationship("Assureur", back_populates="produits_assurance")
    prime_tarifs = relationship(
        "ProduitPrimeTarif",
        back_populates="produit_assurance",
        cascade="all, delete-orphan",
    )

    @property
    def assureur_details(self):
        return self.assureur_obj
