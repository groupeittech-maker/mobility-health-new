"""
Module de routage des demandes vers les assureurs concernés
Détermine quels assureurs doivent être notifiés selon les informations client/voyage
"""
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Assureur:
    """Représente un assureur"""
    id: str
    nom: str
    email: str
    zones: List[str]  # Zones géographiques couvertes
    pays: List[str]  # Pays couverts

class RouterAssureur:
    """
    Route les demandes vers les assureurs appropriés
    selon les informations client et voyage
    """
    
    def __init__(self):
        """Initialise le routeur avec la liste des assureurs"""
        # ⚠️ CONFIGURATION : Liste des assureurs
        # À adapter selon vos assureurs réels
        self.assureurs = [
            Assureur(
                id="assureur_france",
                nom="Assureur France",
                email="france@assureur.com",
                zones=["ZONE 1", "ZONE 2"],
                pays=["France", "Belgique", "Suisse"]
            ),
            Assureur(
                id="assureur_afrique",
                nom="Assureur Afrique",
                email="afrique@assureur.com",
                zones=["ZONE 1", "ZONE 3"],
                pays=["Congo", "Cameroun", "Gabon", "Côte d'Ivoire"]
            ),
            Assureur(
                id="assureur_international",
                nom="Assureur International",
                email="international@assureur.com",
                zones=["ZONE 1", "ZONE 2", "ZONE 3", "ZONE 4"],
                pays=[]  # Tous les pays
            )
        ]
        
        logger.info(f"✅ RouterAssureur initialisé avec {len(self.assureurs)} assureur(s)")
    
    def router_demande(
        self,
        infos_personnelles: Dict,
        infos_voyage: Dict
    ) -> List[Assureur]:
        """
        Détermine quels assureurs doivent être notifiés
        
        Args:
            infos_personnelles: Informations personnelles du client
            infos_voyage: Informations de voyage
        
        Returns:
            Liste des assureurs concernés
        """
        assureurs_concernes = []
        
        # Extraire les informations pertinentes
        pays_client = infos_personnelles.get("pays", "").strip()
        pays_residence = infos_personnelles.get("pays_residence", "").strip()
        zone = infos_personnelles.get("zone", "").strip()
        destination = infos_voyage.get("destination", "").strip()
        
        logger.info(f"🔍 Routage demande - Pays: {pays_client}, Zone: {zone}, Destination: {destination}")
        
        # Parcourir tous les assureurs
        for assureur in self.assureurs:
            concerne = False
            
            # Vérifier par zone
            if zone and zone in assureur.zones:
                concerne = True
                logger.info(f"  ✅ {assureur.nom} concerné (zone: {zone})")
            
            # Vérifier par pays de résidence
            elif pays_residence:
                if not assureur.pays or pays_residence in assureur.pays:
                    concerne = True
                    logger.info(f"  ✅ {assureur.nom} concerné (pays résidence: {pays_residence})")
            
            # Vérifier par pays du client
            elif pays_client:
                if not assureur.pays or pays_client in assureur.pays:
                    concerne = True
                    logger.info(f"  ✅ {assureur.nom} concerné (pays client: {pays_client})")
            
            # Vérifier par destination
            elif destination:
                if not assureur.pays or destination in assureur.pays:
                    concerne = True
                    logger.info(f"  ✅ {assureur.nom} concerné (destination: {destination})")
            
            # Si aucun critère ne correspond, utiliser l'assureur international par défaut
            if not assureurs_concernes and assureur.id == "assureur_international":
                concerne = True
                logger.info(f"  ✅ {assureur.nom} concerné (par défaut)")
            
            if concerne:
                assureurs_concernes.append(assureur)
        
        # Si aucun assureur trouvé, utiliser l'international par défaut
        if not assureurs_concernes:
            assureur_default = next(
                (a for a in self.assureurs if a.id == "assureur_international"),
                self.assureurs[0] if self.assureurs else None
            )
            if assureur_default:
                assureurs_concernes.append(assureur_default)
                logger.info(f"  ✅ {assureur_default.nom} concerné (par défaut - aucun critère)")
        
        logger.info(f"📤 {len(assureurs_concernes)} assureur(s) concerné(s)")
        return assureurs_concernes
    
    def notifier_assureurs(
        self,
        assureurs: List[Assureur],
        demande_id: str,
        resultat_analyse: Dict
    ) -> List[Dict]:
        """
        Notifie les assureurs concernés (webhook, email, etc.)
        
        Args:
            assureurs: Liste des assureurs à notifier
            demande_id: ID de la demande
            resultat_analyse: Résultat de l'analyse
        
        Returns:
            Liste des résultats de notification
        """
        notifications = []
        
        for assureur in assureurs:
            try:
                # ⚠️ CONFIGURATION : Ici vous pouvez ajouter l'envoi réel
                # - Webhook HTTP
                # - Email
                # - Message queue (RabbitMQ, Redis, etc.)
                
                # Exemple de webhook (décommenter et configurer si nécessaire)
                # import requests
                # webhook_url = f"https://{assureur.id}.example.com/api/notifications"
                # response = requests.post(webhook_url, json={
                #     "demande_id": demande_id,
                #     "assureur_id": assureur.id,
                #     "resultat": resultat_analyse
                # })
                
                notification_result = {
                    "assureur_id": assureur.id,
                    "assureur_nom": assureur.nom,
                    "status": "notifie",
                    "methode": "api_storage"  # Les assureurs consultent via l'API
                }
                
                notifications.append(notification_result)
                logger.info(f"📧 Notification envoyée à {assureur.nom} ({assureur.email})")
                
            except Exception as e:
                logger.error(f"❌ Erreur notification {assureur.nom}: {e}")
                notifications.append({
                    "assureur_id": assureur.id,
                    "assureur_nom": assureur.nom,
                    "status": "erreur",
                    "error": str(e)
                })
        
        return notifications

# Instance globale
router_assureur = RouterAssureur()
