// Aligné sur app/services/referent_pipeline_service.py et review-dashboard.js

import '../core/utils/json_value.dart';

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

  int get alerteId => parseJsonInt(alerte['id']) ?? 0;

  ReferentPipelineStep get step {
    final apiStep = alerte['referent_pipeline_step']?.toString();
    if (apiStep != null && apiStep.isNotEmpty) {
      return referentPipelineStepFromApi(apiStep);
    }
    return getReferentStep(alerte, sinistre);
  }
}

ReferentPipelineStep referentPipelineStepFromApi(String value) {
  switch (value) {
    case 'sinistre_valide':
      return ReferentPipelineStep.sinistreValide;
    case 'rapport':
      return ReferentPipelineStep.rapport;
    case 'rapport_valide':
      return ReferentPipelineStep.rapportValide;
    case 'facture':
      return ReferentPipelineStep.facture;
    case 'facture_valide':
      return ReferentPipelineStep.factureValide;
    case 'resolu':
      return ReferentPipelineStep.resolu;
    case 'sinistre':
    default:
      return ReferentPipelineStep.sinistre;
  }
}

String referentPipelineStepToApi(ReferentPipelineStep step) {
  switch (step) {
    case ReferentPipelineStep.sinistre:
      return 'sinistre';
    case ReferentPipelineStep.sinistreValide:
      return 'sinistre_valide';
    case ReferentPipelineStep.rapport:
      return 'rapport';
    case ReferentPipelineStep.rapportValide:
      return 'rapport_valide';
    case ReferentPipelineStep.facture:
      return 'facture';
    case ReferentPipelineStep.factureValide:
      return 'facture_valide';
    case ReferentPipelineStep.resolu:
      return 'resolu';
  }
}

/// Fallback client si l'API n'a pas encore renvoyé referent_pipeline_step.
ReferentPipelineStep getReferentStep(
  Map<String, dynamic> alerte,
  Map<String, dynamic>? sinistre,
) {
  if (sinistre == null) {
    final st = (alerte['statut'] as String?)?.toLowerCase() ?? '';
    if (st == 'annulee') return ReferentPipelineStep.resolu;
    return ReferentPipelineStep.sinistre;
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

/// Compteurs serveur → sous-onglets mobile (À valider / Validé).
(int, int) referentSubTabCountsFromServer(
  ReferentFooterSection section,
  Map<String, int> counts,
) {
  switch (section) {
    case ReferentFooterSection.sinistre:
      return (counts['sinistre'] ?? 0, counts['sinistre_valide'] ?? 0);
    case ReferentFooterSection.rapport:
      return (counts['rapport'] ?? 0, counts['rapport_valide'] ?? 0);
    case ReferentFooterSection.facture:
      return (counts['facture'] ?? 0, counts['facture_valide'] ?? 0);
    case ReferentFooterSection.resolu:
      return (counts['resolu'] ?? 0, 0);
  }
}
