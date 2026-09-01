"""Référentiels de tarification par coefficients (zone, durée, âge)."""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class TarificationZone(Base, TimestampMixin):
    """Zone géographique de destination (pays regroupés). Le prix par durée est dans la grille."""

    __tablename__ = "tarification_zones"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    nom = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    # Conservé pour compatibilité ; non utilisé par le moteur grille + coefficient âge.
    coefficient = Column(Numeric(12, 6), nullable=False, default=1)
    ordre_affichage = Column(Integer, default=0, nullable=False)
    est_actif = Column(Boolean, default=True, nullable=False)

    pays_liens = relationship(
        "TarificationZonePays",
        back_populates="zone",
        cascade="all, delete-orphan",
    )
    grille_cellules = relationship(
        "TarificationGrillePrix",
        back_populates="zone",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    grille_finale_cellules = relationship(
        "TarificationGrilleFinale",
        back_populates="zone",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TarificationZonePays(Base, TimestampMixin):
    """Association pays de destination → zone. Un pays peut être dans plusieurs zones (ex. INTRA + INTER).
    Le moteur de devis retient une zone « canonique » par priorité (RSA > Extra > Intra > Inter)."""

    __tablename__ = "tarification_zone_pays"
    __table_args__ = (
        UniqueConstraint(
            "zone_id",
            "destination_country_id",
            name="uq_tarif_zone_pays_zone_country",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(
        Integer,
        ForeignKey("tarification_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destination_country_id = Column(
        Integer,
        ForeignKey("destination_countries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    zone = relationship("TarificationZone", back_populates="pays_liens")
    pays = relationship("DestinationCountry", backref="tarification_zone_liens")


class TarificationFenetreDuree(Base, TimestampMixin):
    """Fenêtre de durée de séjour (jours). Le montant prime 18–69 est dans tarification_grille_prix."""

    __tablename__ = "tarification_fenetres_duree"

    id = Column(Integer, primary_key=True, index=True)
    libelle = Column(String(200), nullable=True)
    duree_min_jours = Column(Integer, nullable=False)
    duree_max_jours = Column(Integer, nullable=False)
    coefficient = Column(Numeric(12, 6), nullable=False, default=1)  # legacy, ignoré par le moteur
    ordre_priorite = Column(Integer, default=0, nullable=False)
    est_actif = Column(Boolean, default=True, nullable=False)

    grille_cellules = relationship(
        "TarificationGrillePrix",
        back_populates="fenetre",
        passive_deletes=True,
    )
    grille_finale_cellules = relationship(
        "TarificationGrilleFinale",
        back_populates="fenetre",
        passive_deletes=True,
    )


class TarificationGrillePrix(Base, TimestampMixin):
    """Prix de référence (18–69 ans) pour une zone × une fenêtre de durée."""

    __tablename__ = "tarification_grille_prix"
    __table_args__ = (
        UniqueConstraint("zone_id", "fenetre_duree_id", name="uq_tarif_grille_zone_fenetre"),
    )

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(
        Integer,
        ForeignKey("tarification_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fenetre_duree_id = Column(
        Integer,
        ForeignKey("tarification_fenetres_duree.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prix = Column(Numeric(12, 2), nullable=False)

    zone = relationship("TarificationZone", back_populates="grille_cellules")
    fenetre = relationship(
        "TarificationFenetreDuree",
        back_populates="grille_cellules",
        passive_deletes=True,
    )


class TarificationTrancheAge(Base, TimestampMixin):
    """Surprime âge : multiplicateur sur le prix grille (référence 18–69 = coefficient 1)."""

    __tablename__ = "tarification_tranches_age"

    id = Column(Integer, primary_key=True, index=True)
    libelle = Column(String(200), nullable=True)
    age_min = Column(Integer, nullable=True)  # null = pas de borne basse
    age_max = Column(Integer, nullable=True)  # null = pas de borne haute
    coefficient = Column(Numeric(12, 6), nullable=False, default=1)
    ordre_priorite = Column(Integer, default=0, nullable=False)
    est_actif = Column(Boolean, default=True, nullable=False)

    grille_finale_cellules = relationship(
        "TarificationGrilleFinale",
        back_populates="tranche_age",
    )


class TarificationGrilleFinale(Base, TimestampMixin):
    """
    Tarif final explicite : zone × fenêtre de durée × tranche d'âge.
    Si produit_assurance_id est renseigné : tarif pour ce produit uniquement (prioritaire au devis).
    Si NULL : grille globale (repli pour tous les produits sans ligne dédiée).
    Unicité : index partiels en base (voir migration o1p2q3r4s5t6).
    """

    __tablename__ = "tarification_grille_finale"

    id = Column(Integer, primary_key=True, index=True)
    produit_assurance_id = Column(
        Integer,
        ForeignKey("produits_assurance.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    zone_id = Column(
        Integer,
        ForeignKey("tarification_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fenetre_duree_id = Column(
        Integer,
        ForeignKey("tarification_fenetres_duree.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tranche_age_id = Column(
        Integer,
        ForeignKey("tarification_tranches_age.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Coefficient enregistré pour cette ligne (transparence / cohérence avec la tranche au moment de la saisie)
    coefficient_age = Column(Numeric(12, 6), nullable=False, default=1)
    tarif_final = Column(Numeric(12, 2), nullable=False)

    zone = relationship("TarificationZone", back_populates="grille_finale_cellules")
    fenetre = relationship(
        "TarificationFenetreDuree",
        back_populates="grille_finale_cellules",
        passive_deletes=True,
    )
    tranche_age = relationship("TarificationTrancheAge", back_populates="grille_finale_cellules")
    produit_assurance = relationship(
        "ProduitAssurance",
        back_populates="grille_finale_lignes",
    )
