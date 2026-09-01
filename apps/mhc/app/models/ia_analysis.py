"""
Modèles de base de données pour stocker les analyses IA des demandes de souscription
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Numeric, Index, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class IAAnalysis(Base, TimestampMixin):
    """Modèle pour stocker les analyses IA des demandes de souscription"""
    __tablename__ = "ia_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relations avec les entités existantes
    souscription_id = Column(Integer, ForeignKey("souscriptions.id", ondelete="CASCADE"), nullable=True, index=True)
    questionnaire_id = Column(Integer, ForeignKey("questionnaires.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Identifiants
    demande_id = Column(String(100), unique=True, nullable=False, index=True)  # Ex: "DEM-20250115-001"
    
    # Informations client (pour recherche rapide)
    client_nom = Column(String(200), nullable=False, index=True)
    client_prenom = Column(String(200), nullable=False, index=True)
    client_pays = Column(String(100), nullable=True, index=True)
    client_email = Column(String(255), nullable=True, index=True)
    
    # Scores (pour recherche/filtrage)
    probabilite_acceptation = Column(Numeric(5, 3), nullable=False)  # 0.000 à 1.000
    probabilite_fraude = Column(Numeric(5, 3), nullable=False)
    probabilite_confiance_assureur = Column(Numeric(5, 3), nullable=False)
    score_coherence = Column(Numeric(5, 2), nullable=False)  # 0.00 à 100.00
    score_risque = Column(Numeric(5, 3), nullable=False)
    score_confiance = Column(Numeric(5, 2), nullable=False)
    
    # Évaluation
    avis = Column(String(50), nullable=False, index=True)  # FAVORABLE, RÉSERVÉ, DÉFAVORABLE, REJET
    niveau_risque = Column(String(30), nullable=False)  # Faible, Modéré, Élevé, Très élevé
    niveau_fraude = Column(String(30), nullable=False)  # FAIBLE, MODÉRÉ, ÉLEVÉ, TRÈS ÉLEVÉ
    niveau_confiance_assureur = Column(String(30), nullable=False)
    
    # Données structurées (JSON)
    facteurs_risque = Column(JSON, nullable=True)  # Liste des facteurs de risque
    signaux_fraude = Column(JSON, nullable=True)  # Liste des signaux de fraude
    incoherences = Column(JSON, nullable=True)  # Liste des incohérences
    infos_personnelles = Column(JSON, nullable=True)  # Données personnelles extraites
    infos_sante = Column(JSON, nullable=True)  # Questionnaire médical complet
    infos_voyage = Column(JSON, nullable=True)  # Informations de voyage
    
    # Résultat complet (pour consultation détaillée)
    resultat_complet = Column(JSON, nullable=True)  # Résultat complet de l'analyse
    
    # Métadonnées
    date_analyse = Column(DateTime, nullable=False, index=True)
    confiance_ocr = Column(Numeric(5, 2), nullable=True)  # Confiance moyenne OCR
    nb_documents_analyses = Column(Integer, default=0, nullable=False)
    
    # Commentaire et message IA
    commentaire = Column(Text, nullable=True)
    message_ia = Column(Text, nullable=True)
    
    # Relations
    souscription = relationship("Souscription", back_populates="ia_analyses")
    questionnaire = relationship("Questionnaire", back_populates="ia_analyses")
    assureurs_concernes = relationship("IAAnalysisAssureur", back_populates="analyse", cascade="all, delete-orphan")
    documents = relationship("IAAnalysisDocument", back_populates="analyse", cascade="all, delete-orphan")
    
    # Index pour recherche rapide
    __table_args__ = (
        Index('idx_ia_analyses_avis_scores', 'avis', 'probabilite_acceptation', 'probabilite_fraude'),
        Index('idx_ia_analyses_date_avis', 'date_analyse', 'avis'),
        Index('idx_ia_analyses_client', 'client_nom', 'client_prenom'),
    )


class IAAnalysisAssureur(Base, TimestampMixin):
    """Liaison entre analyses IA et assureurs concernés"""
    __tablename__ = "ia_analysis_assureurs"
    
    id = Column(Integer, primary_key=True, index=True)
    analyse_id = Column(Integer, ForeignKey("ia_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    assureur_id = Column(Integer, ForeignKey("assureurs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Statut de notification
    notifie = Column(String(20), default="pending", nullable=False, index=True)  # pending, sent, failed
    date_notification = Column(DateTime, nullable=True)
    methode_notification = Column(String(50), nullable=True)  # email, webhook, api
    
    # Relations
    analyse = relationship("IAAnalysis", back_populates="assureurs_concernes")
    assureur = relationship("Assureur", back_populates="ia_analyses")
    
    # Index unique pour éviter les doublons
    __table_args__ = (
        Index('idx_ia_analysis_assureur_unique', 'analyse_id', 'assureur_id', unique=True),
    )


class IAAnalysisDocument(Base, TimestampMixin):
    """Détails d'un document analysé dans une analyse IA"""
    __tablename__ = "ia_analysis_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    analyse_id = Column(Integer, ForeignKey("ia_analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Informations du document
    nom_fichier = Column(String(255), nullable=False)
    type_document = Column(String(100), nullable=True)  # Passeport, CNI, Questionnaire, etc.
    type_fichier = Column(String(50), nullable=True)  # PDF, PNG, JPG
    
    # Résultats OCR
    confiance_ocr = Column(Numeric(5, 2), nullable=True)
    texte_extrait = Column(Text, nullable=True)  # Texte extrait (tronqué si trop long)
    
    # Vérifications
    est_expire = Column(Boolean, default=False, nullable=False)
    qualite_ok = Column(Boolean, default=True, nullable=False)
    est_complet = Column(Boolean, default=True, nullable=False)
    est_coherent = Column(Boolean, default=True, nullable=False)
    
    # Messages de vérification
    message_expiration = Column(Text, nullable=True)
    message_qualite = Column(Text, nullable=True)
    message_completude = Column(Text, nullable=True)
    message_coherence = Column(Text, nullable=True)
    
    # Résultat complet du document
    resultat_document = Column(JSON, nullable=True)
    
    # Relations
    analyse = relationship("IAAnalysis", back_populates="documents")

