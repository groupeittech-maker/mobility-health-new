import 'package:flutter/material.dart';

import '../models/subscription.dart';
import 'api_services.dart';

/// Raisons de blocage SOS, alignées sur les règles de l'API POST /sos/trigger.
enum SosEligibilityStatus {
  ok,
  noSubscription,
  coverageNotStarted,
  coverageEnded,
  noDefinitiveAttestation,
}

class SosEligibilityResult {
  const SosEligibilityResult(
    this.status, {
    this.coverageStart,
    this.coverageEnd,
  });

  final SosEligibilityStatus status;
  final DateTime? coverageStart;
  final DateTime? coverageEnd;

  bool get canTrigger => status == SosEligibilityStatus.ok;

  String get blockedMessage {
    switch (status) {
      case SosEligibilityStatus.coverageNotStarted:
        return 'Votre couverture débute le ${_fmt(coverageStart)} — '
            "l'assistance SOS sera disponible à partir de cette date.";
      case SosEligibilityStatus.coverageEnded:
        return 'Votre couverture est terminée depuis le ${_fmt(coverageEnd)} — '
            "l'assistance SOS n'est plus disponible sur ce dossier.";
      case SosEligibilityStatus.noSubscription:
        return 'Aucune souscription active. Souscrivez une couverture voyage '
            "pour accéder à l'assistance SOS.";
      case SosEligibilityStatus.noDefinitiveAttestation:
        return 'Une attestation définitive est requise (après validation '
            'production de votre dossier). Vous pouvez consulter l’état de '
            'vos attestations dans le tableau de bord.';
      case SosEligibilityStatus.ok:
        return '';
    }
  }

  static String _fmt(DateTime? d) {
    if (d == null) return '';
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  }
}

/// Règles métier SOS alignées sur l’API : souscription active + attestation définitive valide.
class SosEligibilityService {
  SosEligibilityService._();

  static Future<SosEligibilityResult> check() async {
    final results = await Future.wait<Object?>([
      SubscriptionsService().getSubscriptions(limit: 500),
      AttestationsService().getUserAttestations(),
    ]);
    final subs = results[0]! as List<SubscriptionModel>;
    final atts = results[1]! as List<Map<String, dynamic>>;

    // Même logique que l’API POST /sos/trigger : dernière souscription active
    // (created_at desc) dont la couverture a commencé — avant la date d'effet,
    // les demandes d'assistance sont bloquées (workflow V3 §7).
    final today = DateUtils.dateOnly(DateTime.now());
    SubscriptionModel? latestActive;
    SubscriptionModel? nextUpcoming;
    SubscriptionModel? lastEnded;
    for (final s in subs) {
      if (s.statut != 'active') continue;
      if (DateUtils.dateOnly(s.dateDebut).isAfter(today)) {
        if (nextUpcoming == null || s.dateDebut.isBefore(nextUpcoming.dateDebut)) {
          nextUpcoming = s;
        }
        continue;
      }
      if (s.dateFin != null && DateUtils.dateOnly(s.dateFin!).isBefore(today)) {
        if (lastEnded == null || s.dateFin!.isAfter(lastEnded.dateFin!)) {
          lastEnded = s;
        }
        continue;
      }
      if (latestActive == null || s.createdAt.isAfter(latestActive.createdAt)) {
        latestActive = s;
      }
    }

    if (latestActive == null) {
      if (nextUpcoming != null) {
        return SosEligibilityResult(
          SosEligibilityStatus.coverageNotStarted,
          coverageStart: nextUpcoming.dateDebut,
        );
      }
      if (lastEnded != null) {
        return SosEligibilityResult(
          SosEligibilityStatus.coverageEnded,
          coverageEnd: lastEnded.dateFin,
        );
      }
      return const SosEligibilityResult(SosEligibilityStatus.noSubscription);
    }
    final targetId = latestActive.id;

    for (final a in atts) {
      final type = (a['type_attestation'] ?? '').toString().toLowerCase().trim();
      if (type != 'definitive') continue;
      if (a['est_valide'] == false) continue;
      final sid = a['souscription_id'];
      final sidInt = sid is int ? sid : int.tryParse(sid?.toString() ?? '');
      if (sidInt == targetId) {
        return const SosEligibilityResult(SosEligibilityStatus.ok);
      }
    }
    return const SosEligibilityResult(SosEligibilityStatus.noDefinitiveAttestation);
  }
}
