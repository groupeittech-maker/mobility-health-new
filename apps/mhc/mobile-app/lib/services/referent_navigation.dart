import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../router.dart';

/// Types FCM / API gérés pour le médecin référent MH (aligné backend).
const Set<String> kReferentPushTypes = {
  'sos_alert',
  'medical_report_submitted',
  'invoice_medical_review',
};

/// Navigation depuis les données `data` FCM ou le payload JSON d’une notification locale.
void navigateFromReferentPushData(Map<String, String> data) {
  try {
    final type = data['type_notification'] ?? '';
    if (type.isEmpty) {
      appRouter.go('/referent/notifications');
      return;
    }

    final alerteId = int.tryParse(data['alerte_id'] ?? '');
    if (alerteId != null &&
        alerteId > 0 &&
        (type == 'sos_alert' || type == 'medical_report_submitted')) {
      appRouter.go('/referent/dossier/$alerteId');
      return;
    }

    if (type == 'invoice_medical_review') {
      final lt = (data['lien_relation_type'] ?? 'invoice').toLowerCase();
      final raw = data['invoice_id'] ?? data['lien_relation_id'] ?? '';
      final inv = int.tryParse(raw);
      if (lt == 'invoice' && inv != null && inv > 0) {
        appRouter.go('/referent/facture/$inv');
        return;
      }
    }

    if (kReferentPushTypes.contains(type)) {
      appRouter.go('/referent/notifications');
    }
  } catch (e, st) {
    debugPrint('Deep link référent: $e\n$st');
  }
}

void navigateFromReferentPushPayload(String? payload) {
  if (payload == null || payload.isEmpty) return;
  try {
    final decoded = jsonDecode(payload);
    if (decoded is! Map) return;
    final m = <String, String>{
      for (final e in decoded.entries) '${e.key}': '${e.value}',
    };
    navigateFromReferentPushData(m);
  } catch (e) {
    debugPrint('Payload notification invalide: $e');
  }
}

/// Ouverture app via icône après tap sur une push (cold start).
class ReferentPendingDeepLink {
  static Map<String, String>? _pending;

  static void storeFromFcmData(Map<String, dynamic> data) {
    _pending = {
      for (final e in data.entries) e.key: e.value?.toString() ?? '',
    };
  }

  static void tryConsumeAfterReferentLogin() {
    final p = _pending;
    _pending = null;
    if (p == null || p.isEmpty) return;
    final type = p['type_notification'] ?? '';
    if (!kReferentPushTypes.contains(type)) return;
    navigateFromReferentPushData(p);
  }

  static void clear() => _pending = null;
}

/// Route cible pour une ligne de [GET /notifications/] (liste in-app).
String? referentRouteForNotificationRow(Map<String, dynamic> n) {
  final type = n['type_notification']?.toString() ?? '';
  final alerteRaw = n['alerte_id'];
  final aid = alerteRaw is int
      ? alerteRaw
      : (alerteRaw is num
          ? alerteRaw.toInt()
          : int.tryParse('$alerteRaw'));
  if (aid != null &&
      aid > 0 &&
      (type == 'sos_alert' || type == 'medical_report_submitted')) {
    return '/referent/dossier/$aid';
  }
  if (type == 'invoice_medical_review') {
    final lid = n['lien_relation_id'];
    final iid = lid is int
        ? lid
        : (lid is num ? lid.toInt() : int.tryParse('$lid'));
    final lt = n['lien_relation_type']?.toString().toLowerCase() ?? '';
    if (iid != null && iid > 0 && lt == 'invoice') {
      return '/referent/facture/$iid';
    }
  }
  return null;
}
