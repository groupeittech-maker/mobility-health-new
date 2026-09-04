import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/utils/json_value.dart';

/// Affichage du dossier patient (civil + questionnaire médical) aligné web.
class ReferentPatientDossierSection extends StatelessWidget {
  const ReferentPatientDossierSection({
    super.key,
    required this.alerte,
    required this.sinistre,
  });

  final Map<String, dynamic>? alerte;
  final Map<String, dynamic>? sinistre;

  @override
  Widget build(BuildContext context) {
    final patient = sinistre?['patient'];
    final patientMap = patient is Map ? Map<String, dynamic>.from(patient) : <String, dynamic>{};
    final questionnaire = sinistre?['medical_questionnaire'];
    final civilRows = _buildCivilRows(patientMap);
    final medicalRows = _buildMedicalRows(questionnaire);

    if (civilRows.isEmpty && medicalRows.isEmpty) {
      return const SizedBox.shrink();
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Dossier patient',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            if (questionnaire is Map && questionnaire['version'] != null) ...[
              const SizedBox(height: 4),
              Text(
                'Questionnaire v${questionnaire['version']}',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
            ],
            const Divider(height: 20),
            if (civilRows.isNotEmpty) ...[
              const Text('Informations civiles', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              ...civilRows,
              if (medicalRows.isNotEmpty) const SizedBox(height: 16),
            ],
            if (medicalRows.isNotEmpty) ...[
              const Text('Questionnaire médical', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              ...medicalRows,
            ],
          ],
        ),
      ),
    );
  }

  List<Widget> _buildCivilRows(Map<String, dynamic> patient) {
    final name = patient['full_name']?.toString() ??
        (alerte?['user_full_name']?.toString()) ??
        'Utilisateur #${patient['id'] ?? alerte?['user_id'] ?? '—'}';
    final email = patient['email']?.toString() ?? alerte?['user_email']?.toString();
    final numSin = sinistre?['numero_sinistre']?.toString();
    final numAlert = alerte?['numero_alerte']?.toString() ?? '#${alerte?['id'] ?? '—'}';
    final sous = sinistre?['numero_souscription']?.toString() ??
        (sinistre?['souscription_id'] != null ? 'Souscription #${sinistre!['souscription_id']}' : null);
    final priorite = alerte?['priorite']?.toString();
    final adresse = alerte?['adresse']?.toString();
    final latStr = formatJsonCoord(alerte?['latitude']);
    final lngStr = formatJsonCoord(alerte?['longitude']);
    final gps = latStr != null && lngStr != null ? '$latStr, $lngStr' : null;

    return [
      _kv('Patient', name),
      if (email != null && email.isNotEmpty) _kv('Email', email),
      if (numSin != null && numSin.isNotEmpty) _kv('N° sinistre', numSin),
      _kv("N° alerte", numAlert),
      if (sous != null) _kv('Souscription', sous),
      if (priorite != null) _kv('Priorité', priorite),
      if (adresse != null && adresse.isNotEmpty) _kv('Adresse', adresse),
      if (gps != null) _kv('Coordonnées GPS', gps),
    ];
  }

  List<Widget> _buildMedicalRows(dynamic questionnaire) {
    if (questionnaire is! Map) return [];
    final reponses = questionnaire['reponses'];
    if (reponses is! Map) return [];

    const skipKeys = {'mode', 'consentement', 'consent', 'accepte_conditions'};
    const labelMap = {
      'maladies_chroniques': 'Maladies chroniques',
      'traitements_en_cours': 'Traitements en cours',
      'enceinte': 'Grossesse',
      'antecedents_recents': 'Antécédents récents',
      'allergies': 'Allergies',
      'groupe_sanguin': 'Groupe sanguin',
      'poids': 'Poids',
      'taille': 'Taille',
      'fumeur': 'Fumeur',
      'alcool': 'Consommation alcool',
      'sport': 'Activité sportive',
      'hospitalisations_recentes': 'Hospitalisations récentes',
      'chirurgies_recentes': 'Chirurgies récentes',
      'medicaments': 'Médicaments',
      'symptomes': 'Symptômes',
      'diagnostic': 'Diagnostic déclaré',
    };

    final rows = <Widget>[];
    for (final entry in reponses.entries) {
      final key = entry.key.toString();
      if (skipKeys.contains(key)) continue;
      if (key.startsWith('photo_') || key.contains('photo')) continue;
      final value = _formatMedicalValue(entry.value);
      if (value == null || value.isEmpty) continue;
      final label = labelMap[key] ?? _humanizeKey(key);
      rows.add(_kv(label, value));
    }
    return rows;
  }

  String? _formatMedicalValue(dynamic value) {
    if (value == null) return null;
    if (value is bool) return value ? 'Oui' : 'Non';
    if (value is List) {
      if (value.isEmpty) return null;
      return value.map((e) => e.toString()).join(', ');
    }
    if (value is Map) {
      return value.entries.map((e) => '${e.key}: ${e.value}').join('\n');
    }
    final s = value.toString().trim();
    return s.isEmpty ? null : s;
  }

  String _humanizeKey(String key) {
    return key.replaceAll('_', ' ').replaceFirstMapped(RegExp(r'^\w'), (m) => m.group(0)!.toUpperCase());
  }

  Widget _kv(String k, String v) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(k, style: TextStyle(color: Colors.grey.shade700, fontSize: 13)),
          ),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 14))),
        ],
      ),
    );
  }
}

/// Timeline workflow sinistre (aligné web).
class ReferentWorkflowSection extends StatelessWidget {
  const ReferentWorkflowSection({super.key, required this.workflowSteps});

  final List<dynamic> workflowSteps;

  @override
  Widget build(BuildContext context) {
    if (workflowSteps.isEmpty) return const SizedBox.shrink();

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Étapes du dossier',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const Divider(height: 20),
            ...workflowSteps.map((step) {
              if (step is! Map) return const SizedBox.shrink();
              final m = Map<String, dynamic>.from(step);
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(m['titre']?.toString() ?? m['step_key']?.toString() ?? 'Étape',
                        style: const TextStyle(fontWeight: FontWeight.w600)),
                    if (m['description'] != null)
                      Text(m['description'].toString(), style: TextStyle(fontSize: 13, color: Colors.grey.shade700)),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        _statusChip(m['statut']?.toString()),
                        if (m['completed_at'] != null) ...[
                          const SizedBox(width: 8),
                          Text(_formatDate(m['completed_at']), style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                        ],
                      ],
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _statusChip(String? statut) {
    final s = (statut ?? '').toLowerCase();
    Color bg;
    String label;
    switch (s) {
      case 'completed':
        bg = Colors.green.shade100;
        label = 'Terminé';
        break;
      case 'cancelled':
        bg = Colors.red.shade100;
        label = 'Annulé';
        break;
      case 'in_progress':
        bg = Colors.blue.shade100;
        label = 'En cours';
        break;
      default:
        bg = Colors.grey.shade200;
        label = statut ?? '—';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12)),
      child: Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
    );
  }

  String _formatDate(dynamic value) {
    if (value == null) return '';
    final d = DateTime.tryParse(value.toString());
    if (d == null) return value.toString();
    return DateFormat('dd/MM/yyyy HH:mm').format(d.toLocal());
  }
}

/// Statut décision médicale urgence (aligné web).
class ReferentMedicalDecisionBanner extends StatelessWidget {
  const ReferentMedicalDecisionBanner({super.key, required this.workflowSteps});

  final List<dynamic> workflowSteps;

  Map<String, dynamic>? get _urgenceStep {
    for (final step in workflowSteps) {
      if (step is Map && step['step_key'] == 'verification_urgence') {
        return Map<String, dynamic>.from(step);
      }
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final step = _urgenceStep;
    if (step == null) return const SizedBox.shrink();

    final statut = step['statut']?.toString();
    final notes = step['details'] is Map ? step['details']['notes']?.toString() : null;
    String message;
    Color color;
    IconData icon;

    switch (statut) {
      case 'completed':
        message = 'Alerte confirmée par un médecin${notes != null && notes.isNotEmpty ? ' • $notes' : ''}';
        color = Colors.green.shade50;
        icon = Icons.check_circle_outline;
        break;
      case 'cancelled':
        message = 'Alerte refusée${notes != null && notes.isNotEmpty ? ' • $notes' : ''}';
        color = Colors.orange.shade50;
        icon = Icons.cancel_outlined;
        break;
      default:
        message = 'Décision médicale attendue : confirmez ou refusez la véracité de l\'urgence.';
        color = Colors.blue.shade50;
        icon = Icons.medical_information_outlined;
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: color,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 22),
            const SizedBox(width: 12),
            Expanded(child: Text(message, style: const TextStyle(fontSize: 14))),
          ],
        ),
      ),
    );
  }
}
