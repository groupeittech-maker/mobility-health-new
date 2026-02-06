# Caractéristiques complètes d'un produit d'assurance voyage

Ce document détaille toutes les caractéristiques qui peuvent être gérées dans la page de gestion des produits d'assurance voyage.

## Structure complète du produit

### 1. Informations générales du produit

- **Code produit** : Identifiant interne unique (ex: VOY-STD-001)
- **Nom du produit** : Nom commercial (ex: Voyage Standard, Premium+, VIP Business)
- **Description rapide** : Objectif et description du produit
- **Version** : Version du produit (pour la gestion des mises à jour)
- **Statut** : Actif / Inactif
- **Assureur** : Nom de l'assureur
- **Image URL** : URL de l'image/miniature du produit
- **Coût** : Coût de base du produit
- **Clé de répartition** : 
  - Par personne
  - Par groupe
  - Par durée
  - Par destination
  - Fixe

### 2. Zone géographique couverte

#### Zones géographiques
- Afrique
- Europe
- Amérique
- Asie
- Océanie
- Monde
- Afrique Centrale
- Afrique de l'Ouest
- Afrique du Nord
- Afrique de l'Est
- Afrique Australe

#### Pays éligibles
- Liste de codes pays (ex: FR, US, CM, etc.)

#### Pays exclus
- Liste de codes pays exclus de la couverture

#### Spécificités
- Pays en guerre
- Sanctions internationales
- Autres spécificités (texte libre)

### 3. Durée du voyage

- **Durée minimale** : Nombre de jours minimum du séjour
- **Durée maximale** : Nombre de jours maximum du séjour
- **Durée de validité** : Durée de validité du produit en jours
- **Reconduction possible** : Oui / Non
- **Couverture multi-entrées** : Oui / Non

### 4. Profil des assurés

- **Âge minimum** : Âge minimum accepté
- **Âge maximum** : Âge maximum accepté
- **Catégories** :
  - Individuel
  - Famille
  - Groupe
  - Entreprise (Corporate)
- **Conditions de santé particulières** : Texte libre (ex: personnes âgées avec supplément)

### 5. Garanties incluses

Chaque garantie contient les éléments suivants :

- **Nom de la garantie** : Type de garantie
- **Description** : Description détaillée
- **Plafond** : Montant maximum couvert
- **Franchise** : Montant à charge du client
- **Délai de carence** : Nombre de jours avant activation
- **Conditions d'activation** : Conditions spécifiques pour activer la garantie
- **Exclusions spécifiques** : Exclusions propres à cette garantie

#### Types de garanties disponibles

1. Assistance médicale / Frais médicaux
2. Hospitalisation
3. Médicaments
4. Soins d'urgence
5. Rapatriement sanitaire
6. Organisation + Transport
7. Responsabilité civile à l'étranger
8. Assurance bagages
9. Perte, vol, retard
10. Annulation / Interruption de voyage
11. Décès / Invalidité accidentelle
12. Assistance juridique
13. Frais de retour anticipé
14. Retour anticipé en cas de décès d'un proche
15. Assistance en cas de perte de documents

### 6. Exclusions générales

Liste des exclusions communes du produit :

- Guerre, terrorisme (sauf extension)
- Activités sportives extrêmes
- Maladies préexistantes
- Suicide ou acte intentionnel
- Autres exclusions (texte libre)

### 7. Conditions générales (texte libre)

Conditions générales supplémentaires du produit en texte libre.

---

## Format de stockage

Les données sont stockées dans la base de données avec la structure suivante :

- **Informations générales** : Champs SQL standards
- **Zones géographiques** : JSON structuré
  ```json
  {
    "zones": ["Afrique", "Europe"],
    "pays_eligibles": ["FR", "US", "CM"],
    "pays_exclus": ["XX"],
    "specificites": ["pays_en_guerre"]
  }
  ```

- **Garanties** : Array JSON de garanties
  ```json
  [
    {
      "nom": "Assistance médicale",
      "description": "...",
      "plafond": 50000,
      "franchise": 100,
      "delai_carence": 3,
      "conditions_activation": "...",
      "exclusions_specifiques": ["..."]
    }
  ]
  ```

- **Exclusions générales** : Array JSON de chaînes
  ```json
  ["Guerre", "Terrorisme", "Activités sportives extrêmes"]
  ```




