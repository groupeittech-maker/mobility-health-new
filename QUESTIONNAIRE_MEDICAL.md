# Questionnaire Médical - Documentation

## Vue d'ensemble

Le questionnaire médical a été créé pour déterminer si une personne n'a pas de maladie grave non déclarée et évaluer les risques avant de valider l'attestation définitive d'assurance voyage.

## Structure du Questionnaire

Le questionnaire est organisé en 4 sections principales (A à D) :

### A. Antécédents médicaux généraux

- **Maladies chroniques** : Sélection multiple parmi :
  - Hypertension
  - Diabète
  - Asthme
  - Maladie cardiaque
  - Maladie rénale
  - Maladie hépatique
  - Autre (avec champ de précision)

- **Traitement médical régulier** : Oui/Non (avec détails si Oui)

- **Hospitalisation dans les 12 derniers mois** : Oui/Non (avec précision si Oui)

- **Opération chirurgicale dans les 5 dernières années** : Oui/Non (avec précision si Oui)

### B. Symptômes récents

Sélection multiple parmi :
- Douleurs thoraciques
- Essoufflement inhabituel
- Vertiges fréquents
- Perte de connaissance
- Fièvre persistante
- Saignements anormaux
- Réactions allergiques sévères

- **Êtes-vous enceinte ?** (Pour femmes) : Oui/Non/Ne s'applique pas

- **Avez-vous subi une opération chirurgicale dans les 6 derniers mois ?** : Oui/Non. Si oui, **Donnez des précisions** (champ texte obligatoire).

### C. Maladies contagieuses ou risques infectieux

Sélection multiple parmi :
- Paludisme
- Tuberculose
- Hépatite
- Infections respiratoires sévères
- Autre maladie infectieuse (avec champ de précision)

- **Contact avec une personne gravement malade** : Oui/Non (avec détails si Oui)

### D. Déclaration

Deux déclarations obligatoires (checkboxes) :

1. **Je déclare n'avoir rien omis dans ce questionnaire**
2. **Je reconnais que toute fausse déclaration entraînera la nullité des garanties**

## Implémentation technique

### Backend

**Fichiers modifiés/créés :**

1. **`app/schemas/questionnaire.py`**
   - Ajout du type `'medical'` au pattern de validation

2. **`app/api/v1/questionnaires.py`**
   - Nouveau endpoint : `POST /subscriptions/{subscription_id}/questionnaire/medical`
   - Gestion de la version et archivage automatique des anciennes versions
   - Création automatique d'une notification après enregistrement

### Frontend

**Fichiers créés/modifiés :**

1. **`frontend/src/pages/QuestionnaireMedical.tsx`**
   - Composant React complet avec Formik et Yup
   - Validation conditionnelle selon les réponses
   - Gestion des champs conditionnels (affichage selon les réponses)
   - Interface utilisateur organisée en sections

2. **`frontend/src/api/questionnaires.ts`**
   - Ajout de la méthode `createMedical()`
   - Mise à jour des types TypeScript pour inclure `'medical'`

3. **`frontend/src/App.tsx`**
   - Ajout de la route : `/subscriptions/:subscriptionId/questionnaire/medical`

4. **`frontend/src/pages/Questionnaire.css`**
   - Styles réutilisés depuis les autres questionnaires

## Utilisation

### Accès au questionnaire

Le questionnaire médical est accessible via l'URL :
```
/subscriptions/{subscriptionId}/questionnaire/medical
```

### Structure des données stockées

Les réponses sont stockées en JSON dans la base de données avec la structure suivante :

```json
{
  "antecedents_medicaux": {
    "maladies_chroniques": ["hypertension", "diabete"],
    "maladie_chronique_autre": "",
    "traitement_medical": "oui",
    "traitement_medical_details": "Médicaments pour l'hypertension",
    "hospitalisation_12mois": "non",
    "hospitalisation_12mois_details": "",
    "operation_5ans": "oui",
    "operation_5ans_details": "Appendicectomie"
  },
  "symptomes_recents": {
    "douleurs_thoraciques": false,
    "essoufflement": false,
    "vertiges": true,
    "perte_connaissance": false,
    "fievre_persistante": false,
    "saignements_anormaux": false,
    "reactions_allergiques": false,
    "enceinte": "non"
  },
  "maladies_contagieuses": {
    "paludisme": false,
    "tuberculose": false,
    "hepatite": false,
    "infections_respiratoires": false,
    "autre_maladie_infectieuse": "",
    "contact_personne_malade": "non",
    "contact_personne_malade_details": ""
  },
  "declaration": {
    "rien_omis": true,
    "fausse_declaration": true
  }
}
```

## Validation

Le formulaire inclut une validation complète :

- **Champs obligatoires** : Tous les champs marqués d'un astérisque (*) sont obligatoires
- **Validation conditionnelle** : Si une réponse nécessite des précisions (ex: "Oui" à "Traitement médical"), le champ de détail devient obligatoire
- **Validation des déclarations** : Les deux déclarations (Section E) sont obligatoires pour soumettre le formulaire

## Notification

Après l'enregistrement réussi du questionnaire, une notification est automatiquement créée pour l'utilisateur avec le message :
> "Votre questionnaire médical pour la souscription #{subscriptionId} a été enregistré avec succès."

## Versioning

Le système gère automatiquement le versioning :
- Chaque nouvelle soumission crée une nouvelle version du questionnaire
- L'ancienne version est automatiquement archivée (`statut = "archive"`)
- La nouvelle version est marquée comme complète (`statut = "complete"`)

## Intégration avec le workflow de souscription

Le questionnaire médical fait partie du processus de validation d'une souscription. Il doit être complété avant la validation médicale finale de l'attestation.















