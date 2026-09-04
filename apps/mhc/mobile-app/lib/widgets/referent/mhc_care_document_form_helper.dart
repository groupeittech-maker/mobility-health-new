import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../models/mhc_care_document.dart';

/// Préremplissage et collecte des champs d'émission (aligné web).
class MhcCareDocumentFormHelper {
  static String? _str(dynamic v) {
    if (v == null) return null;
    final s = v.toString().trim();
    return s.isEmpty ? null : s;
  }

  static String? toDatetimeLocalValue(dynamic value) {
    if (value == null) return null;
    DateTime? date;
    if (value is DateTime) {
      date = value;
    } else {
      date = DateTime.tryParse(value.toString());
    }
    if (date == null) return null;
    return DateFormat("yyyy-MM-dd'T'HH:mm").format(date.toLocal());
  }

  static Map<String, String> buildPrefill({
    Map<String, dynamic>? alerte,
    Map<String, dynamic>? sinistre,
    Map<String, dynamic>? stay,
  }) {
    final motif = _str(stay?['report_motif_hospitalisation']) ??
        _str(stay?['report_motif_consultation']) ??
        _str(alerte?['description']);
    final doctor = stay?['assigned_doctor'];
    String? doctorName;
    if (doctor is Map) {
      doctorName = _str(doctor['full_name']) ?? _str(doctor['email']);
    }
    return {
      'medecin_traitant': doctorName ?? '',
      'medecin_referent': _str(sinistre?['medecin_referent_nom']) ?? '',
      'service': _str(stay?['service_concerne']) ?? '',
      'chambre': _str(stay?['chambre']) ?? '',
      'motif_medical': motif ?? '',
      'admission_prevue': toDatetimeLocalValue(stay?['started_at']) ?? '',
      'date_entree': toDatetimeLocalValue(stay?['started_at']) ?? '',
      'date_sortie': toDatetimeLocalValue(stay?['ended_at']) ?? '',
      'duree_jours': stay?['report_duree_sejour_heures'] != null
          ? ((stay!['report_duree_sejour_heures'] as num) / 24).toStringAsFixed(1)
          : '',
      'resume_rapport': _str(stay?['report_resume']) ?? '',
      'examens_prevus': stay?['report_examens'] is List
          ? (stay!['report_examens'] as List).map((e) => e.toString()).join(', ')
          : '',
      'devise': 'XAF',
    };
  }

  static Map<String, dynamic> collectPayload(
    String type,
    Map<String, TextEditingController> controllers,
    Set<String> selectedRefusalMotifs,
  ) {
    String? val(String key) {
      final c = controllers[key];
      if (c == null) return null;
      final v = c.text.trim();
      return v.isEmpty ? null : v;
    }

    final payload = <String, dynamic>{};
    final motif = val('mhcMotif');

    switch (type) {
      case 'bpcu':
        if (motif != null) {
          payload['motif_medical'] = motif;
          payload['diagnostic'] = motif;
        }
        payload['service'] = val('mhcService');
        payload['montant_max'] = val('mhcMontant');
        payload['devise'] = val('mhcDevise');
        payload['medecin_referent'] = val('mhcMedecinReferent');
        break;
      case 'brpcu':
        if (selectedRefusalMotifs.isNotEmpty) {
          payload['motifs_refus'] = selectedRefusalMotifs.toList();
        }
        if (motif != null) {
          payload['autres_motifs'] = motif;
          if (selectedRefusalMotifs.isEmpty) payload['motif_refus'] = motif;
        }
        break;
      case 'bh':
        payload['admission_prevue'] = val('mhcAdmission');
        payload['service'] = val('mhcService');
        payload['medecin_traitant'] = val('mhcMedecinTraitant');
        payload['chambre'] = val('mhcChambre');
        if (motif != null) {
          payload['motif_medical'] = motif;
          payload['diagnostic'] = motif;
        }
        break;
      case 'bph':
        if (motif != null) payload['motif_prolongation'] = motif;
        payload['examens_prevus'] = val('mhcExamens');
        payload['cout_additionnel'] = val('mhcCoutAdd');
        payload['cout_total'] = val('mhcCoutTotal');
        payload['devise'] = val('mhcDevise');
        break;
      case 'bs':
        payload['date_entree'] = val('mhcDateEntree');
        payload['date_sortie'] = val('mhcDateSortie');
        payload['duree_jours'] = val('mhcDureeJours');
        payload['mode_sortie'] = val('mhcExitMode');
        payload['resume_rapport'] = val('mhcResume');
        final docs = val('mhcDocsRemis');
        if (docs != null) {
          payload['documents_remis'] =
              docs.split(',').map((s) => s.trim()).where((s) => s.isNotEmpty).toList();
        }
        break;
      case 'brs':
        payload['depart_prevu'] = val('mhcDepart');
        payload['destination'] = val('mhcDestination');
        payload['moyen_transport'] = val('mhcTransport');
        payload['transporteur'] = val('mhcTransporteur');
        payload['escorte_medicale'] = val('mhcEscorte');
        if (motif != null) {
          payload['motif_medical'] = motif;
          payload['diagnostic'] = motif;
        }
        payload['cout_rapatriement'] = val('mhcCoutRapat');
        payload['devise'] = val('mhcDevise');
        break;
      case 'ars':
        payload['lieu_depart'] = val('mhcLieuDepart');
        payload['structure_depart'] = val('mhcStructureDepart');
        payload['destination'] = val('mhcDestination');
        payload['structure_arrivee'] = val('mhcStructureArrivee');
        payload['date_depart'] = val('mhcDateDepart');
        payload['date_arrivee'] = val('mhcDateArrivee');
        payload['etat_arrivee'] = val('mhcEtatArrivee');
        payload['bonne_reception'] = val('mhcBonneReception');
        payload['observations'] = val('mhcObservations');
        break;
      case 'brf':
        payload['date_deces'] = val('mhcDateDeces');
        if (motif != null) payload['cause_deces'] = motif;
        payload['pays_depart'] = val('mhcPaysDepart');
        payload['pays_destination'] = val('mhcDestination');
        payload['moyen_transport'] = val('mhcTransport');
        payload['transporteur'] = val('mhcTransporteur');
        payload['contact_famille'] = val('mhcContactFamille');
        payload['cout_rapatriement'] = val('mhcCoutRapat');
        payload['devise'] = val('mhcDevise');
        break;
      case 'arf':
        payload['date_deces'] = val('mhcDateDeces');
        payload['numero_acte_deces'] = val('mhcNumActe');
        payload['lieu_depart'] = val('mhcLieuDepart');
        payload['destination'] = val('mhcDestination');
        payload['receptionnaire'] = val('mhcReceptionnaire');
        payload['date_remise'] = val('mhcDateRemise');
        payload['bonne_reception'] = val('mhcBonneReception');
        payload['observations'] = val('mhcObservations');
        break;
    }

    payload.removeWhere((_, v) => v == null);
    return payload;
  }

  static List<Widget> buildFieldsForType(
    String type,
    Map<String, TextEditingController> controllers,
    Map<String, String> prefill,
    Set<String> selectedRefusalMotifs,
    void Function(void Function()) setState,
  ) {
    void bind(String key, {String? initial}) {
      controllers.putIfAbsent(key, () => TextEditingController(text: initial ?? prefill[_prefillKey(key)] ?? ''));
    }

    String? p(String k) => prefill[k]?.isNotEmpty == true ? prefill[k] : null;

    switch (type) {
      case 'bpcu':
        bind('mhcMotif', initial: p('motif_medical'));
        bind('mhcService', initial: p('service'));
        bind('mhcMontant');
        bind('mhcDevise', initial: p('devise'));
        bind('mhcMedecinReferent', initial: p('medecin_referent'));
        return [
          _field('Motif médical / diagnostic', controllers['mhcMotif']!, maxLines: 2, required: true),
          _field('Service concerné', controllers['mhcService']!),
          _field('Montant maximum autorisé', controllers['mhcMontant']!),
          _field('Devise', controllers['mhcDevise']!),
          _field('Médecin référent MHC', controllers['mhcMedecinReferent']!),
        ];
      case 'brpcu':
        bind('mhcMotif');
        return [
          const Text('Motifs de refus contractuels', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          ...MhcCareDocumentLabels.refusalMotifs.map((motif) => CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(motif, style: const TextStyle(fontSize: 13)),
                value: selectedRefusalMotifs.contains(motif),
                onChanged: (v) {
                  setState(() {
                    if (v == true) {
                      selectedRefusalMotifs.add(motif);
                    } else {
                      selectedRefusalMotifs.remove(motif);
                    }
                  });
                },
              )),
          _field('Autres motifs / précisions', controllers['mhcMotif']!, maxLines: 2),
        ];
      case 'bh':
        bind('mhcAdmission', initial: p('admission_prevue'));
        bind('mhcService', initial: p('service'));
        bind('mhcMedecinTraitant', initial: p('medecin_traitant'));
        bind('mhcChambre', initial: p('chambre'));
        bind('mhcMotif', initial: p('motif_medical'));
        return [
          _field("Date / heure d'admission prévue", controllers['mhcAdmission']!, hint: '2026-09-04T14:30'),
          _field("Service d'admission", controllers['mhcService']!, required: true),
          _field('Médecin traitant (orientation réception)', controllers['mhcMedecinTraitant']!, readOnly: true),
          _field('Chambre / unité', controllers['mhcChambre']!),
          _field("Diagnostic / motif d'hospitalisation", controllers['mhcMotif']!, maxLines: 2, required: true),
        ];
      case 'bph':
        bind('mhcMotif', initial: p('motif_medical'));
        bind('mhcExamens', initial: p('examens_prevus'));
        bind('mhcCoutAdd');
        bind('mhcCoutTotal');
        bind('mhcDevise', initial: p('devise'));
        return [
          _field('Motif de la prolongation', controllers['mhcMotif']!, maxLines: 2, required: true),
          _field('Examens / traitements prévus', controllers['mhcExamens']!, maxLines: 2),
          _field('Coût additionnel autorisé', controllers['mhcCoutAdd']!),
          _field('Coût total à ce jour', controllers['mhcCoutTotal']!),
          _field('Devise', controllers['mhcDevise']!),
        ];
      case 'bs':
        bind('mhcDateEntree', initial: p('date_entree'));
        bind('mhcDateSortie', initial: p('date_sortie'));
        bind('mhcDureeJours', initial: p('duree_jours'));
        bind('mhcExitMode');
        bind('mhcResume', initial: p('resume_rapport'));
        bind('mhcDocsRemis');
        return [
          _field("Date d'entrée", controllers['mhcDateEntree']!, hint: '2026-09-01T08:00'),
          _field('Date de sortie', controllers['mhcDateSortie']!, hint: '2026-09-04T10:00'),
          _field('Durée totale (jours)', controllers['mhcDureeJours']!),
          _dropdownExitMode(controllers['mhcExitMode']!),
          _field('Résumé du rapport final', controllers['mhcResume']!, maxLines: 3),
          _field('Documentation remise (séparée par virgules)', controllers['mhcDocsRemis']!),
        ];
      case 'brs':
        bind('mhcDepart');
        bind('mhcDestination');
        bind('mhcTransport');
        bind('mhcTransporteur');
        bind('mhcEscorte');
        bind('mhcMotif', initial: p('motif_medical'));
        bind('mhcCoutRapat');
        bind('mhcDevise', initial: p('devise'));
        return [
          _field('Date / heure de départ prévues', controllers['mhcDepart']!),
          _field('Destination', controllers['mhcDestination']!, required: true),
          _field('Moyen de transport', controllers['mhcTransport']!),
          _field('Société de transport', controllers['mhcTransporteur']!),
          _field('Escorte médicale', controllers['mhcEscorte']!),
          _field('Motif médical', controllers['mhcMotif']!, maxLines: 2),
          _field('Coût total autorisé', controllers['mhcCoutRapat']!),
          _field('Devise', controllers['mhcDevise']!),
        ];
      case 'ars':
        bind('mhcLieuDepart');
        bind('mhcStructureDepart');
        bind('mhcDestination');
        bind('mhcStructureArrivee');
        bind('mhcDateDepart');
        bind('mhcDateArrivee');
        bind('mhcEtatArrivee');
        bind('mhcBonneReception');
        bind('mhcObservations');
        return [
          _field('Lieu de départ', controllers['mhcLieuDepart']!),
          _field('Structure de départ', controllers['mhcStructureDepart']!),
          _field('Destination finale', controllers['mhcDestination']!),
          _field("Structure d'arrivée", controllers['mhcStructureArrivee']!),
          _field('Départ', controllers['mhcDateDepart']!),
          _field('Arrivée', controllers['mhcDateArrivee']!),
          _field("État à l'arrivée", controllers['mhcEtatArrivee']!),
          _field('Bonne réception (oui/non)', controllers['mhcBonneReception']!),
          _field('Observations', controllers['mhcObservations']!, maxLines: 2),
        ];
      case 'brf':
        bind('mhcDateDeces');
        bind('mhcMotif', initial: p('motif_medical'));
        bind('mhcPaysDepart');
        bind('mhcDestination');
        bind('mhcTransport');
        bind('mhcTransporteur');
        bind('mhcContactFamille');
        bind('mhcCoutRapat');
        bind('mhcDevise', initial: p('devise'));
        return [
          _field('Date et heure du décès', controllers['mhcDateDeces']!),
          _field('Cause du décès', controllers['mhcMotif']!, maxLines: 2),
          _field('Pays de départ', controllers['mhcPaysDepart']!),
          _field('Pays de destination', controllers['mhcDestination']!),
          _field('Moyen de transport du corps', controllers['mhcTransport']!),
          _field('Société de transport', controllers['mhcTransporteur']!),
          _field('Contact famille', controllers['mhcContactFamille']!),
          _field('Coût total autorisé', controllers['mhcCoutRapat']!),
          _field('Devise', controllers['mhcDevise']!),
        ];
      case 'arf':
        bind('mhcDateDeces');
        bind('mhcNumActe');
        bind('mhcLieuDepart');
        bind('mhcDestination');
        bind('mhcReceptionnaire');
        bind('mhcDateRemise');
        bind('mhcBonneReception');
        bind('mhcObservations');
        return [
          _field('Date et lieu du décès', controllers['mhcDateDeces']!),
          _field("N° acte / certificat de décès", controllers['mhcNumActe']!),
          _field('Lieu de départ', controllers['mhcLieuDepart']!),
          _field('Destination finale', controllers['mhcDestination']!),
          _field('Réceptionnaire de la dépouille', controllers['mhcReceptionnaire']!),
          _field('Date / heure de remise', controllers['mhcDateRemise']!),
          _field('Bonne réception (oui/non)', controllers['mhcBonneReception']!),
          _field('Réserves / observations', controllers['mhcObservations']!, maxLines: 2),
        ];
      default:
        return [Text('Type de document non pris en charge : $type')];
    }
  }

  static String _prefillKey(String controllerKey) {
    switch (controllerKey) {
      case 'mhcMotif':
        return 'motif_medical';
      case 'mhcService':
        return 'service';
      case 'mhcMedecinTraitant':
        return 'medecin_traitant';
      case 'mhcMedecinReferent':
        return 'medecin_referent';
      case 'mhcChambre':
        return 'chambre';
      case 'mhcAdmission':
        return 'admission_prevue';
      case 'mhcDateEntree':
        return 'date_entree';
      case 'mhcDateSortie':
        return 'date_sortie';
      case 'mhcDureeJours':
        return 'duree_jours';
      case 'mhcResume':
        return 'resume_rapport';
      case 'mhcExamens':
        return 'examens_prevus';
      case 'mhcDevise':
        return 'devise';
      default:
        return controllerKey;
    }
  }

  static Widget _field(
    String label,
    TextEditingController controller, {
    int maxLines = 1,
    bool required = false,
    bool readOnly = false,
    String? hint,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: controller,
        maxLines: maxLines,
        readOnly: readOnly,
        decoration: InputDecoration(
          labelText: required ? '$label *' : label,
          hintText: hint,
          border: const OutlineInputBorder(),
          filled: readOnly,
          fillColor: readOnly ? Colors.grey.shade100 : null,
        ),
      ),
    );
  }

  static Widget _dropdownExitMode(TextEditingController controller) {
    const options = {
      'guerison': 'Guérison / retour au domicile',
      'ambulatoire': 'Sortie sous traitement ambulatoire',
      'transfert': 'Transfert inter-hospitalier',
      'rapatriement_sanitaire': 'Rapatriement sanitaire organisé par MHC',
      'autre': 'Autre modalité',
    };
    final current = controller.text.isEmpty ? 'guerison' : controller.text;
    if (controller.text.isEmpty) controller.text = current;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: DropdownButtonFormField<String>(
        key: ValueKey(current),
        initialValue: options.containsKey(current) ? current : 'guerison',
        decoration: const InputDecoration(
          labelText: 'Mode de sortie',
          border: OutlineInputBorder(),
        ),
        items: options.entries
            .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value, style: const TextStyle(fontSize: 13))))
            .toList(),
        onChanged: (v) => controller.text = v ?? 'guerison',
      ),
    );
  }
}
