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

/// Détermine l'étape d'affichage (même ordre de priorité que le web).
ReferentPipelineStep getReferentStep(
  Map<String, dynamic> alerte,
  Map<String, dynamic>? sinistre,
) {
  if (sinistre == null) {
    final st = (alerte['statut'] as String?)?.toLowerCase() ?? '';
    return st == 'annulee' ? ReferentPipelineStep.resolu : ReferentPipelineStep.sinistre;
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

  final steps = sinistre['workflow_steps'];
  String statutUrgence = '';
  if (steps is List) {
    for (final s in steps) {
      if (s is Map && s['step_key'] == 'verification_urgence') {
        statutUrgence = (s['statut'] as String?)?.toLowerCase() ?? '';
        break;
      }
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
