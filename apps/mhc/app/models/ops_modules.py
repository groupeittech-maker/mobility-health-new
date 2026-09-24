"""Modules annexes : hôtels (hébergement assurés) et transport médical."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Boolean, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False, index=True)
    adresse = Column(String(500), nullable=True)
    ville = Column(String(100), nullable=True)
    pays = Column(String(100), nullable=True)
    telephone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    categorie = Column(String(50), nullable=True)  # étoiles / standing
    contact_nom = Column(String(200), nullable=True)
    est_actif = Column(Boolean, nullable=False, default=True)

    assignments = relationship("HotelAssignment", back_populates="hotel")


class HotelAssignment(Base):
    """Hébergement organisé pour un assuré dans le cadre d'une alerte."""

    __tablename__ = "hotel_assignments"

    id = Column(Integer, primary_key=True, index=True)
    alerte_id = Column(Integer, ForeignKey("alertes.id", ondelete="CASCADE"), nullable=False, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    date_arrivee = Column(DateTime, nullable=True)
    date_depart = Column(DateTime, nullable=True)
    nb_nuits = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    statut = Column(String(20), nullable=False, default="reserve", index=True)  # reserve | confirme | termine | annule
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    hotel = relationship("Hotel", back_populates="assignments")


class TransportProvider(Base):
    """Prestataire de transport médical (ambulances, VSL, taxis médicalisés)."""

    __tablename__ = "transport_providers"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False, index=True)
    type_vehicule = Column(String(80), nullable=True)  # ambulance | vsl | taxi_medicalise | avion_sanitaire
    ville = Column(String(100), nullable=True)
    pays = Column(String(100), nullable=True)
    telephone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    contact_nom = Column(String(200), nullable=True)
    est_actif = Column(Boolean, nullable=False, default=True)


class TransportMission(Base):
    """Course de transport médical rattachée à un sinistre."""

    __tablename__ = "transport_missions"

    id = Column(Integer, primary_key=True, index=True)
    sinistre_id = Column(Integer, ForeignKey("sinistres.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id = Column(Integer, ForeignKey("transport_providers.id", ondelete="SET NULL"), nullable=True)
    type_transport = Column(String(80), nullable=True)
    depart = Column(String(300), nullable=True)
    arrivee = Column(String(300), nullable=True)
    date_mission = Column(DateTime, nullable=True)
    statut = Column(String(20), nullable=False, default="demandee", index=True)  # demandee | assignee | en_route | terminee | annulee
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
