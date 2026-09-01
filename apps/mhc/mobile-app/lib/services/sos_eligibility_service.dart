import '../models/subscription.dart';
import 'api_services.dart';

/// Règles métier SOS alignées sur l’API : souscription active + attestation définitive valide.
class SosEligibilityService {
  SosEligibilityService._();

  static Future<bool> canTriggerSos() async {
    final results = await Future.wait<Object?>([
      SubscriptionsService().getSubscriptions(limit: 500),
      AttestationsService().getUserAttestations(),
    ]);
    final subs = results[0]! as List<SubscriptionModel>;
    final atts = results[1]! as List<Map<String, dynamic>>;

    // Même logique que l’API POST /sos/trigger : dernière souscription active (created_at desc).
    SubscriptionModel? latestActive;
    for (final s in subs) {
      if (s.statut != 'active') continue;
      if (latestActive == null || s.createdAt.isAfter(latestActive.createdAt)) {
        latestActive = s;
      }
    }
    if (latestActive == null) return false;
    final targetId = latestActive.id;

    for (final a in atts) {
      final type = (a['type_attestation'] ?? '').toString().toLowerCase().trim();
      if (type != 'definitive') continue;
      if (a['est_valide'] == false) continue;
      final sid = a['souscription_id'];
      final sidInt = sid is int ? sid : int.tryParse(sid?.toString() ?? '');
      if (sidInt == targetId) return true;
    }
    return false;
  }
}
