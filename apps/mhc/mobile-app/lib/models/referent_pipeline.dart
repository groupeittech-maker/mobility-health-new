// Aligné sur frontend-simple/js/review-dashboard.js — getReferentStep

/// Étapes du pipeline médecin référent (onglets web).
enum ReferentPipelineStep {
  sinistre,
  sinistreValide,
  rapport,
  rapportValide,
  facture,
  factureValide,
  resolu,
}

/// Sections du pied de page (navigation principale).
enum ReferentFooterSection {
  sinistre,
  rapport,
  facture,
  resolu,
}

/// Alerte + sinistre (optionnel) pour classer un dossier.
class ReferentDossierItem {
  ReferentDossierItem(this.alerte, this.sinistre);

  final Map<String, dynamic> alerte;
  final Map<String, dynamic>? sinistre;

  int get alerteId => (alerte['id'] as num).toInt();

  ReferentPipelineStep get step => getReferentStep(alerte, sinistre);
}

/// Étapes workflow présentes sur l’alerte (GET /sos/) ou sur le détail sinistre.
List<dynamic> _workflowStepsForClassification(
  Map<String, dynamic> alerte,
  Map<String, dynamic>? sinistre,
) {
  if (sinistre != null && sinistre['workflow_steps'] is List) {
    return sinistre['workflow_steps'] as List<dynamic>;
  }
  if (alerte['workflow_steps'] is List) {
    return alerte['workflow_steps'] as List<dynamic>;
  }
  return const [];
}

String? _stepStatut(List<dynamic> steps, String stepKey) {
  for (final s in steps) {
    if (s is Map && s['step_key'] == stepKey) {
      return (s['statut'] as String?)?.toLowerCase() ?? '';
    }
  }
  return null;
}

/// Classement sans GET `/sos/{id}/sinistre` : `workflow_steps`, `is_oriented` sur l’alerte (liste SOS).
ReferentPipelineStep _referentStepFromAlerteOnly(Map<String, dynamic> alerte) {
  final steps = _workflowStepsForClassification(alerte, null);

  final statutUrgence = _stepStatut(steps, 'verification_urgence') ?? '';
  if (statutUrgence.isEmpty ||
      (statutUrgence != 'completed' && statutUrgence != 'cancelled')) {
    return ReferentPipelineStep.sinistre;
  }

  final isOriented = alerte['is_oriented'] == true;
  final factureEmise = _stepStatut(steps, 'facture_emise') ?? '';
  final med = _stepStatut(steps, 'validation_facture_medicale') ?? '';
  final compta = _stepStatut(steps, 'validation_facture_comptable') ?? '';

  if (compta == 'completed') {
    return ReferentPipelineStep.resolu;
  }
  if (med == 'cancelled') {
    return ReferentPipelineStep.resolu;
  }

  if (factureEmise == 'completed') {
    if (med == 'pending' || med == 'in_progress') {
      return ReferentPipelineStep.facture;
    }
    if (med == 'completed' || med == 'approved') {
      return ReferentPipelineStep.factureValide;
    }
  }

  if (!isOriented) {
    return ReferentPipelineStep.sinistreValide;
  }

  if (factureEmise == 'in_progress') {
    return ReferentPipelineStep.rapportValide;
  }

  return ReferentPipelineStep.rapport;
}

/// Détermine l'étape d'affichage (même ordre de priorité que le web).
/// Sans [sinistre] : s’appuie sur les champs de l’alerte API (`workflow_steps`, `is_oriented`, `is_validated`)
/// pour éviter un GET /sos/{id}/sinistre par ligne dans les listes.
ReferentPipelineStep getReferentStep(
  Map<String, dynamic> alerte,
  Map<String, dynamic>? sinistre,
) {
  if (sinistre == null) {
    final st = (alerte['statut'] as String?)?.toLowerCase() ?? '';
    if (st == 'annulee' || st == 'resolue') return ReferentPipelineStep.resolu;
    final sid = alerte['sinistre_id'];
    if (sid == null) {
      return ReferentPipelineStep.sinistre;
    }
    return _referentStepFromAlerteOnly(alerte);
  }

  final stayRaw = sinistre['hospital_stay'];
  Map<String, dynamic>? stay;
  if (stayRaw is Map) {
    stay = Map<String, dynamic>.from(stayRaw);
  }

  Map<String, dynamic>? invoice;
  if (stay != null) {
    final inv = stay['invoice'];
    if (inv is Map) {
      invoice = Map<String, dynamic>.from(inv);
    }
  }

  final stayStatus = stay != null ? (stay['status'] as String?)?.toLowerCase() ?? '' : '';
  final invoiceStatut =
      invoice != null ? (invoice['statut'] as String?)?.toLowerCase() ?? '' : '';

  if (invoiceStatut == 'validated' || invoiceStatut == 'paid') {
    return ReferentPipelineStep.resolu;
  }
  if (invoice != null && invoice['validation_medicale']?.toString() == 'rejected') {
    return ReferentPipelineStep.resolu;
  }

  if (stay != null && stayStatus == 'awaiting_validation') {
    return ReferentPipelineStep.rapport;
  }

  final steps = _workflowStepsForClassification(alerte, sinistre);
  String statutUrgence = '';
  for (final s in steps) {
    if (s is Map && s['step_key'] == 'verification_urgence') {
      statutUrgence = (s['statut'] as String?)?.toLowerCase() ?? '';
      break;
    }
  }

  if (statutUrgence.isEmpty ||
      (statutUrgence != 'completed' && statutUrgence != 'cancelled')) {
    return ReferentPipelineStep.sinistre;
  }

  if (invoice != null && invoice['validation_medicale']?.toString() == 'pending') {
    return ReferentPipelineStep.facture;
  }

  if (invoice != null && invoice['validation_medicale']?.toString() == 'approved') {
    return ReferentPipelineStep.factureValide;
  }

  if (stay != null &&
      stayStatus == 'validated' &&
      (invoice == null || invoice['validation_medicale']?.toString() != 'pending')) {
    return ReferentPipelineStep.rapportValide;
  }

  if (statutUrgence == 'completed' ||
      (sinistre['numero_sinistre'] != null && statutUrgence.isEmpty)) {
    return ReferentPipelineStep.sinistreValide;
  }

  return ReferentPipelineStep.sinistreValide;
}

String referentStepLabel(ReferentPipelineStep step) {
  switch (step) {
    case ReferentPipelineStep.sinistre:
      return 'Sinistre à valider';
    case ReferentPipelineStep.sinistreValide:
      return 'Sinistre validé';
    case ReferentPipelineStep.rapport:
      return 'Rapport à valider';
    case ReferentPipelineStep.rapportValide:
      return 'Rapport validé';
    case ReferentPipelineStep.facture:
      return 'Facture à valider';
    case ReferentPipelineStep.factureValide:
      return 'Facture validée';
    case ReferentPipelineStep.resolu:
      return 'Dossier résolu';
  }
}
