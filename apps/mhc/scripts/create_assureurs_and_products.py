#!/usr/bin/env python3
"""
Script pour créer 3 assureurs et 6 produits d'assurance (2 par assureur)
avec toutes les informations des modèles.
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.enums import CleRepartition
from app.models.assureur import Assureur
from app.models.produit_assurance import ProduitAssurance
from app.models.historique_prix import HistoriquePrix
from app.models.audit import AuditLog
from datetime import datetime

# Devise : XAF (Franc CFA d'Afrique centrale)
# Montants réalistes directement en XAF


def create_assureurs_and_products():
    """Crée 3 assureurs et 6 produits d'assurance"""
    db: Session = SessionLocal()
    
    try:
        # ============================================
        # 1. CRÉATION DES ASSUREURS
        # ============================================
        
        assureurs_data = [
            {
                "nom": "Assurance Voyage International (AVI)",
                "pays": "France",
                "logo_url": "https://example.com/logos/avi.png",
                "adresse": "15 Avenue des Champs-Élysées, 75008 Paris, France",
                "telephone": "+33 1 42 36 70 00",
            },
            {
                "nom": "Global Travel Insurance (GTI)",
                "pays": "Côte d'Ivoire",
                "logo_url": "https://example.com/logos/gti.png",
                "adresse": "Boulevard de la République, Cocody, Abidjan, Côte d'Ivoire",
                "telephone": "+225 27 22 44 12 34",
            },
            {
                "nom": "Mobility Health Assurance (MHA)",
                "pays": "Sénégal",
                "logo_url": "https://example.com/logos/mha.png",
                "adresse": "Avenue Cheikh Anta Diop, Dakar, Sénégal",
                "telephone": "+221 33 849 50 00",
            },
        ]
        
        assureurs_created = []
        for assureur_data in assureurs_data:
            # Vérifier si l'assureur existe déjà
            existing = db.query(Assureur).filter(
                Assureur.nom == assureur_data["nom"]
            ).first()
            
            if existing:
                print(f"⚠️  Assureur '{assureur_data['nom']}' existe déjà (ID: {existing.id})")
                assureurs_created.append(existing)
            else:
                assureur = Assureur(**assureur_data)
                db.add(assureur)
                db.commit()
                db.refresh(assureur)
                print(f"✅ Assureur créé: {assureur.nom} (ID: {assureur.id})")
                assureurs_created.append(assureur)
        
        # ============================================
        # 2. CRÉATION DES PRODUITS D'ASSURANCE
        # ============================================
        
        produits_data = [
            # Produits pour AVI (Assurance Voyage International)
            {
                "assureur_index": 0,
                "code": "AVI-BASIC-2024",
                "nom": "AVI Basic - Assurance Voyage Essentielle",
                "description": "Assurance voyage de base couvrant les frais médicaux d'urgence, rapatriement et responsabilité civile à l'étranger. Idéale pour les voyages courts en Europe et Afrique.",
                "version": "2024.1",
                "est_actif": True,
                "cout": Decimal("65000.00"),  # 65 000 XAF - Assurance basique
                "currency": "XAF",
                "cle_repartition": CleRepartition.FIXE,
                "zones_geographiques": {
                    "zones": ["Europe", "Afrique de l'Ouest", "Afrique Centrale"],
                    "pays_eligibles": [
                        "France", "Belgique", "Suisse", "Espagne", "Italie",
                        "Côte d'Ivoire", "Sénégal", "Bénin", "Togo", "Burkina Faso",
                        "Cameroun", "Gabon", "Congo"
                    ],
                    "pays_exclus": [],
                    "specificites": ["Couverture limitée aux pays listés"]
                },
                "duree_min_jours": 1,
                "duree_max_jours": 90,
                "duree_validite_jours": 365,
                "reconduction_possible": True,
                "couverture_multi_entrees": True,
                "age_minimum": 18,
                "age_maximum": 75,
                "conditions_sante": "Aucune condition préexistante non déclarée. Questionnaire médical requis pour les plus de 65 ans.",
                "categories_assures": ["individuel", "famille"],
                "garanties": [
                    {
                        "nom": "Frais médicaux d'urgence",
                        "montant_max": "50 000 FCFA",
                        "franchise": "50 FCFA",
                        "description": "Remboursement des frais médicaux en cas d'accident ou maladie à l'étranger"
                    },
                    {
                        "nom": "Rapatriement sanitaire",
                        "montant_max": "Illimité",
                        "franchise": "0 FCFA",
                        "description": "Prise en charge du rapatriement médical en cas de nécessité"
                    },
                    {
                        "nom": "Responsabilité civile à l'étranger",
                        "montant_max": "100 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Couverture des dommages causés à des tiers"
                    },
                    {
                        "nom": "Assistance 24/7",
                        "montant_max": "Inclus",
                        "franchise": "0 FCFA",
                        "description": "Service d'assistance téléphonique disponible 24h/24 et 7j/7"
                    }
                ],
                "exclusions_generales": [
                    "Sports à risque (plongée, alpinisme, etc.)",
                    "Maladies préexistantes non déclarées",
                    "Grossesse après le 3ème mois",
                    "Voyages dans des zones de guerre",
                    "Consommation excessive d'alcool ou de drogues"
                ],
                "conditions": "Conditions générales disponibles sur demande. Validité du contrat sous réserve de paiement de la prime.",
                "conditions_generales_pdf_url": "https://example.com/cg/avi-basic-2024.pdf",
                "image_url": "https://example.com/images/avi-basic.jpg"
            },
            {
                "assureur_index": 0,
                "code": "AVI-PREMIUM-2024",
                "nom": "AVI Premium - Assurance Voyage Complète",
                "description": "Assurance voyage premium avec couverture étendue incluant annulation, bagages, retard de vol et garanties médicales renforcées. Parfaite pour les voyages d'affaires et longs séjours.",
                "version": "2024.1",
                "est_actif": True,
                "cout": Decimal("180000.00"),  # 180 000 XAF - Assurance premium
                "currency": "XAF",
                "cle_repartition": CleRepartition.PAR_PERSONNE,
                "zones_geographiques": {
                    "zones": ["Monde entier"],
                    "pays_eligibles": [],
                    "pays_exclus": ["Corée du Nord", "Syrie", "Afghanistan"],
                    "specificites": ["Couverture mondiale sauf pays exclus"]
                },
                "duree_min_jours": 1,
                "duree_max_jours": 365,
                "duree_validite_jours": 365,
                "reconduction_possible": True,
                "couverture_multi_entrees": True,
                "age_minimum": 0,
                "age_maximum": 85,
                "conditions_sante": "Questionnaire médical détaillé requis. Certaines conditions préexistantes peuvent être couvertes sous conditions.",
                "categories_assures": ["individuel", "famille", "groupe", "entreprise"],
                "garanties": [
                    {
                        "nom": "Frais médicaux d'urgence",
                        "montant_max": "500 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Remboursement complet des frais médicaux d'urgence"
                    },
                    {
                        "nom": "Rapatriement sanitaire",
                        "montant_max": "Illimité",
                        "franchise": "0 FCFA",
                        "description": "Rapatriement médical et accompagnement"
                    },
                    {
                        "nom": "Annulation / Interruption de séjour",
                        "montant_max": "10 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Remboursement en cas d'annulation pour motif valable"
                    },
                    {
                        "nom": "Bagages",
                        "montant_max": "3 000 FCFA",
                        "franchise": "100 FCFA",
                        "description": "Vol, perte ou détérioration des bagages"
                    },
                    {
                        "nom": "Retard de vol",
                        "montant_max": "500 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Indemnisation en cas de retard de vol supérieur à 4h"
                    },
                    {
                        "nom": "Responsabilité civile",
                        "montant_max": "1 000 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Couverture responsabilité civile étendue"
                    },
                    {
                        "nom": "Assistance 24/7 Premium",
                        "montant_max": "Inclus",
                        "franchise": "0 FCFA",
                        "description": "Assistance complète avec service conciergerie"
                    }
                ],
                "exclusions_generales": [
                    "Sports extrêmes non déclarés",
                    "Maladies préexistantes non couvertes",
                    "Grossesse complications après le 6ème mois",
                    "Zones de guerre ou d'instabilité politique",
                    "Actes de terrorisme dans certaines zones"
                ],
                "conditions": "Conditions générales premium. Consultation médicale préalable recommandée pour les plus de 70 ans.",
                "conditions_generales_pdf_url": "https://example.com/cg/avi-premium-2024.pdf",
                "image_url": "https://example.com/images/avi-premium.jpg"
            },
            
            # Produits pour GTI (Global Travel Insurance)
            {
                "assureur_index": 1,
                "code": "GTI-AFRIQUE-2024",
                "nom": "GTI Afrique - Assurance Voyage Régionale",
                "description": "Assurance spécialement conçue pour les voyages en Afrique. Couverture adaptée aux spécificités du continent avec réseau de partenaires locaux.",
                "version": "2024.2",
                "est_actif": True,
                "cout": Decimal("95000.00"),  # 95 000 XAF - Assurance régionale Afrique
                "currency": "XAF",
                "cle_repartition": CleRepartition.PAR_DESTINATION,
                "zones_geographiques": {
                    "zones": ["Afrique de l'Ouest", "Afrique Centrale", "Afrique de l'Est", "Afrique Australe"],
                    "pays_eligibles": [
                        "Côte d'Ivoire", "Sénégal", "Bénin", "Togo", "Burkina Faso", "Mali", "Niger",
                        "Cameroun", "Gabon", "Congo", "RDC", "Rwanda", "Kenya", "Tanzanie",
                        "Afrique du Sud", "Botswana", "Namibie", "Zimbabwe"
                    ],
                    "pays_exclus": [],
                    "specificites": [
                        "Réseau de partenaires médicaux en Afrique",
                        "Prise en charge des frais de consultation dans les cliniques partenaires",
                        "Assistance en français et langues locales"
                    ]
                },
                "duree_min_jours": 3,
                "duree_max_jours": 180,
                "duree_validite_jours": 365,
                "reconduction_possible": True,
                "couverture_multi_entrees": True,
                "age_minimum": 0,
                "age_maximum": 80,
                "conditions_sante": "Questionnaire médical simplifié. Couverture des maladies tropicales courantes.",
                "categories_assures": ["individuel", "famille"],
                "garanties": [
                    {
                        "nom": "Frais médicaux d'urgence",
                        "montant_max": "100 000 FCFA",
                        "franchise": "50 FCFA",
                        "description": "Frais médicaux et hospitalisation en Afrique"
                    },
                    {
                        "nom": "Rapatriement sanitaire",
                        "montant_max": "Illimité",
                        "franchise": "0 FCFA",
                        "description": "Rapatriement depuis l'Afrique vers le pays d'origine"
                    },
                    {
                        "nom": "Consultation médicale préventive",
                        "montant_max": "500 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Consultations dans les cliniques partenaires du réseau GTI"
                    },
                    {
                        "nom": "Vaccination et prévention",
                        "montant_max": "300 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Remboursement partiel des vaccins obligatoires"
                    },
                    {
                        "nom": "Responsabilité civile",
                        "montant_max": "200 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Couverture responsabilité civile"
                    },
                    {
                        "nom": "Assistance 24/7",
                        "montant_max": "Inclus",
                        "franchise": "0 FCFA",
                        "description": "Assistance multilingue (français, anglais, langues locales)"
                    }
                ],
                "exclusions_generales": [
                    "Maladies nécessitant une évacuation médicale complexe",
                    "Sports nautiques en eaux non surveillées",
                    "Voyages dans des zones non sécurisées",
                    "Maladies préexistantes non déclarées"
                ],
                "conditions": "Conditions adaptées aux voyages en Afrique. Consultation préalable recommandée pour les vaccinations.",
                "conditions_generales_pdf_url": "https://example.com/cg/gti-afrique-2024.pdf",
                "image_url": "https://example.com/images/gti-afrique.jpg"
            },
            {
                "assureur_index": 1,
                "code": "GTI-MONDE-2024",
                "nom": "GTI Monde - Assurance Voyage Internationale",
                "description": "Assurance voyage mondiale avec couverture étendue pour tous types de voyages. Idéale pour les expatriés et voyageurs fréquents.",
                "version": "2024.2",
                "est_actif": True,
                "cout": Decimal("220000.00"),  # 220 000 XAF - Assurance mondiale
                "currency": "XAF",
                "cle_repartition": CleRepartition.PAR_DUREE,
                "zones_geographiques": {
                    "zones": ["Monde entier"],
                    "pays_eligibles": [],
                    "pays_exclus": ["Corée du Nord"],
                    "specificites": ["Couverture mondiale complète"]
                },
                "duree_min_jours": 1,
                "duree_max_jours": 730,
                "duree_validite_jours": 730,
                "reconduction_possible": True,
                "couverture_multi_entrees": True,
                "age_minimum": 0,
                "age_maximum": 99,
                "conditions_sante": "Questionnaire médical détaillé. Couverture possible pour certaines conditions préexistantes après évaluation.",
                "categories_assures": ["individuel", "famille", "groupe", "entreprise"],
                "garanties": [
                    {
                        "nom": "Frais médicaux d'urgence",
                        "montant_max": "1 000 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Couverture médicale complète mondiale"
                    },
                    {
                        "nom": "Rapatriement sanitaire",
                        "montant_max": "Illimité",
                        "franchise": "0 FCFA",
                        "description": "Rapatriement depuis n'importe où dans le monde"
                    },
                    {
                        "nom": "Annulation / Interruption",
                        "montant_max": "15 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Remboursement en cas d'annulation ou interruption"
                    },
                    {
                        "nom": "Bagages et effets personnels",
                        "montant_max": "5 000 FCFA",
                        "franchise": "100 FCFA",
                        "description": "Vol, perte, détérioration des bagages"
                    },
                    {
                        "nom": "Retard de vol / Perte de connexion",
                        "montant_max": "1 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Indemnisation retards et pertes de connexion"
                    },
                    {
                        "nom": "Responsabilité civile mondiale",
                        "montant_max": "2 000 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Couverture responsabilité civile étendue"
                    },
                    {
                        "nom": "Assistance Premium 24/7",
                        "montant_max": "Inclus",
                        "franchise": "0 FCFA",
                        "description": "Assistance complète avec service VIP"
                    },
                    {
                        "nom": "Couverture expatriation",
                        "montant_max": "Inclus",
                        "franchise": "0 FCFA",
                        "description": "Couverture pour séjours longue durée à l'étranger"
                    }
                ],
                "exclusions_generales": [
                    "Sports extrêmes non déclarés",
                    "Zones de guerre actives",
                    "Maladies préexistantes non couvertes après évaluation",
                    "Actes de terrorisme dans certaines zones spécifiques"
                ],
                "conditions": "Conditions générales monde. Validité étendue pour expatriation. Consultation médicale préalable pour séjours > 1 an.",
                "conditions_generales_pdf_url": "https://example.com/cg/gti-monde-2024.pdf",
                "image_url": "https://example.com/images/gti-monde.jpg"
            },
            
            # Produits pour MHA (Mobility Health Assurance)
            {
                "assureur_index": 2,
                "code": "MHA-STANDARD-2024",
                "nom": "MHA Standard - Assurance Mobilité Standard",
                "description": "Assurance standard pour les déplacements professionnels et personnels. Couverture équilibrée entre garanties et prix.",
                "version": "2024.3",
                "est_actif": True,
                "cout": Decimal("120000.00"),  # 120 000 XAF - Assurance standard
                "currency": "XAF",
                "cle_repartition": CleRepartition.PAR_GROUPE,
                "zones_geographiques": {
                    "zones": ["Europe", "Afrique", "Amérique du Nord"],
                    "pays_eligibles": [
                        "France", "Belgique", "Suisse", "Espagne", "Italie", "Allemagne",
                        "Côte d'Ivoire", "Sénégal", "Bénin", "Togo", "Cameroun",
                        "Canada", "États-Unis", "Mexique"
                    ],
                    "pays_exclus": [],
                    "specificites": ["Couverture optimisée pour les zones principales"]
                },
                "duree_min_jours": 1,
                "duree_max_jours": 180,
                "duree_validite_jours": 365,
                "reconduction_possible": True,
                "couverture_multi_entrees": True,
                "age_minimum": 18,
                "age_maximum": 70,
                "conditions_sante": "Questionnaire médical standard. Pas de couverture pour conditions préexistantes graves.",
                "categories_assures": ["individuel", "famille"],
                "garanties": [
                    {
                        "nom": "Frais médicaux d'urgence",
                        "montant_max": "200 000 FCFA",
                        "franchise": "50 FCFA",
                        "description": "Frais médicaux et hospitalisation"
                    },
                    {
                        "nom": "Rapatriement sanitaire",
                        "montant_max": "Illimité",
                        "franchise": "0 FCFA",
                        "description": "Rapatriement médical"
                    },
                    {
                        "nom": "Annulation",
                        "montant_max": "5 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Remboursement en cas d'annulation"
                    },
                    {
                        "nom": "Bagages",
                        "montant_max": "2 000 FCFA",
                        "franchise": "100 FCFA",
                        "description": "Vol et perte de bagages"
                    },
                    {
                        "nom": "Responsabilité civile",
                        "montant_max": "500 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Couverture responsabilité civile"
                    },
                    {
                        "nom": "Assistance 24/7",
                        "montant_max": "Inclus",
                        "franchise": "0 FCFA",
                        "description": "Service d'assistance"
                    }
                ],
                "exclusions_generales": [
                    "Sports à risque",
                    "Maladies préexistantes graves",
                    "Voyages dans zones dangereuses",
                    "Grossesse complications"
                ],
                "conditions": "Conditions générales standard. Couverture adaptée aux besoins courants.",
                "conditions_generales_pdf_url": "https://example.com/cg/mha-standard-2024.pdf",
                "image_url": "https://example.com/images/mha-standard.jpg"
            },
            {
                "assureur_index": 2,
                "code": "MHA-ENTERPRISE-2024",
                "nom": "MHA Enterprise - Assurance Mobilité Entreprise",
                "description": "Solution d'assurance complète pour les entreprises et leurs collaborateurs en déplacement. Tarification dégressive selon le nombre d'assurés.",
                "version": "2024.3",
                "est_actif": True,
                "cout": Decimal("160000.00"),  # 160 000 XAF - Assurance entreprise
                "currency": "XAF",
                "cle_repartition": CleRepartition.PAR_GROUPE,
                "zones_geographiques": {
                    "zones": ["Monde entier"],
                    "pays_eligibles": [],
                    "pays_exclus": ["Corée du Nord", "Syrie"],
                    "specificites": [
                        "Couverture mondiale pour entreprises",
                        "Gestion centralisée des souscriptions",
                        "Rapports dédiés pour les RH"
                    ]
                },
                "duree_min_jours": 1,
                "duree_max_jours": 365,
                "duree_validite_jours": 365,
                "reconduction_possible": True,
                "couverture_multi_entrees": True,
                "age_minimum": 0,
                "age_maximum": 80,
                "conditions_sante": "Questionnaire médical simplifié pour groupes. Gestion centralisée des dossiers médicaux.",
                "categories_assures": ["groupe", "entreprise"],
                "garanties": [
                    {
                        "nom": "Frais médicaux d'urgence",
                        "montant_max": "500 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Couverture médicale complète pour collaborateurs"
                    },
                    {
                        "nom": "Rapatriement sanitaire",
                        "montant_max": "Illimité",
                        "franchise": "0 FCFA",
                        "description": "Rapatriement et évacuation médicale"
                    },
                    {
                        "nom": "Annulation / Interruption professionnelle",
                        "montant_max": "20 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "Remboursement annulations professionnelles"
                    },
                    {
                        "nom": "Bagages professionnels",
                        "montant_max": "5 000 FCFA",
                        "franchise": "100 FCFA",
                        "description": "Protection équipements professionnels et bagages"
                    },
                    {
                        "nom": "Responsabilité civile professionnelle",
                        "montant_max": "2 000 000 FCFA",
                        "franchise": "0 FCFA",
                        "description": "RC professionnelle étendue"
                    },
                    {
                        "nom": "Assistance entreprise 24/7",
                        "montant_max": "Inclus",
                        "franchise": "0 FCFA",
                        "description": "Assistance dédiée avec contact privilégié"
                    },
                    {
                        "nom": "Gestion centralisée",
                        "montant_max": "Inclus",
                        "franchise": "0 FCFA",
                        "description": "Plateforme de gestion pour les RH"
                    },
                    {
                        "nom": "Rapports et analytics",
                        "montant_max": "Inclus",
                        "franchise": "0 FCFA",
                        "description": "Tableaux de bord et statistiques de déplacements"
                    }
                ],
                "exclusions_generales": [
                    "Sports extrêmes non professionnels",
                    "Zones de guerre",
                    "Actes de terrorisme dans zones spécifiques",
                    "Maladies préexistantes non déclarées"
                ],
                "conditions": "Conditions générales entreprise. Tarification dégressive à partir de 5 assurés. Gestion centralisée incluse.",
                "conditions_generales_pdf_url": "https://example.com/cg/mha-enterprise-2024.pdf",
                "image_url": "https://example.com/images/mha-enterprise.jpg"
            },
        ]
        
        produits_created = []
        for produit_data in produits_data:
            assureur_index = produit_data.pop("assureur_index")
            assureur = assureurs_created[assureur_index]
            
            # Vérifier si le produit existe déjà
            existing = db.query(ProduitAssurance).filter(
                ProduitAssurance.code == produit_data["code"]
            ).first()
            
            if existing:
                print(f"⚠️  Produit '{produit_data['code']}' existe déjà (ID: {existing.id})")
                produits_created.append(existing)
            else:
                # Ajouter l'assureur_id et le nom de l'assureur
                produit_data["assureur_id"] = assureur.id
                produit_data["assureur"] = assureur.nom
                
                # Créer le produit
                produit = ProduitAssurance(**produit_data)
                db.add(produit)
                db.commit()
                db.refresh(produit)
                
                # Créer l'entrée d'historique de prix
                historique = HistoriquePrix(
                    produit_assurance_id=produit.id,
                    ancien_prix=None,
                    nouveau_prix=produit.cout,
                    raison_modification="Création du produit",
                    modifie_par_user_id=None  # Script système
                )
                db.add(historique)
                db.commit()
                
                print(f"✅ Produit créé: {produit.nom} ({produit.code}) - {produit.cout:,.0f} {produit.currency}")
                produits_created.append(produit)
        
        print("\n" + "="*60)
        print("📊 RÉSUMÉ")
        print("="*60)
        print(f"✅ {len(assureurs_created)} assureur(s) créé(s) ou existant(s)")
        print(f"✅ {len(produits_created)} produit(s) créé(s) ou existant(s)")
        print("\nAssureurs:")
        for assureur in assureurs_created:
            produits_count = len([p for p in produits_created if p.assureur_id == assureur.id])
            print(f"  - {assureur.nom} ({assureur.pays}): {produits_count} produit(s)")
        print("\nProduits:")
        for produit in produits_created:
            print(f"  - {produit.code}: {produit.nom} - {produit.cout:,.0f} {produit.currency}")
        print("="*60)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de la création: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Création des assureurs et produits d'assurance...")
    print("="*60)
    create_assureurs_and_products()
    print("\n✅ Script terminé avec succès!")

