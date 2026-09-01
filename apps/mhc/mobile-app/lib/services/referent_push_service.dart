import 'dart:convert';

import 'package:app_badge_plus/app_badge_plus.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../core/network/api_client.dart';
import '../core/storage/token_storage.dart';
import 'referent_navigation.dart';

/// FCM + notification locale (bip) + badge sur l’icône (style type messagerie).
class ReferentPushService {
  ReferentPushService._();
  static final ReferentPushService instance = ReferentPushService._();

  final ApiClient _api = ApiClient();
  final FlutterLocalNotificationsPlugin _local =
      FlutterLocalNotificationsPlugin();
  static const int _notifId = 1001;

  Future<void> setupLocalNotifications() async {
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const ios = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    await _local.initialize(
      const InitializationSettings(android: android, iOS: ios),
      onDidReceiveNotificationResponse: (details) {
        if (details.notificationResponseType !=
            NotificationResponseType.selectedNotification) {
          return;
        }
        final p = details.payload;
        if (p != null && p.isNotEmpty) {
          navigateFromReferentPushPayload(p);
        }
      },
    );

    await _local
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(
          const AndroidNotificationChannel(
            'mh_referent',
            'Mobility Health — Médecin référent',
            description:
                'Alertes SOS, rapports médicaux et factures à valider',
            importance: Importance.max,
            playSound: true,
            enableVibration: true,
          ),
        );
  }

  Future<void> updateBadgeFromData(Map<String, dynamic> data) async {
    final raw = data['mh_badge'];
    final n = int.tryParse(raw?.toString() ?? '');
    if (n != null) {
      await AppBadgePlus.updateBadge(n);
    }
  }

  Future<void> handleForegroundMessage(RemoteMessage message) async {
    await updateBadgeFromData(message.data);

    final ntype = message.data['type_notification']?.toString();
    if (ntype == null || !kReferentPushTypes.contains(ntype) || kIsWeb) {
      return;
    }

    final title = message.notification?.title ??
        message.data['title'] ??
        'Mobility Health';
    final body = message.notification?.body ?? message.data['body'] ?? '';
    final badgeRaw = message.data['mh_badge'];
    final number = int.tryParse(badgeRaw?.toString() ?? '') ?? 0;

    final payloadMap = <String, String>{
      for (final e in message.data.entries) e.key: e.value?.toString() ?? '',
    };
    final payloadJson =
        payloadMap.isNotEmpty ? jsonEncode(payloadMap) : null;

    if (defaultTargetPlatform == TargetPlatform.android) {
      final androidDetails = AndroidNotificationDetails(
        'mh_referent',
        'Mobility Health — Médecin référent',
        channelDescription:
            'Alertes SOS, rapports médicaux et factures à valider',
        importance: Importance.max,
        priority: Priority.high,
        playSound: true,
        enableVibration: true,
        number: number > 0 ? number : 1,
        styleInformation: BigTextStyleInformation(
          body,
          contentTitle: title,
        ),
      );

      await _local.show(
        _notifId,
        title,
        body,
        NotificationDetails(android: androidDetails),
        payload: payloadJson,
      );
    } else if (defaultTargetPlatform == TargetPlatform.iOS) {
      final iosDetails = DarwinNotificationDetails(
        presentAlert: true,
        presentBadge: true,
        presentSound: true,
        badgeNumber: number > 0 ? number : null,
      );
      await _local.show(
        _notifId,
        title,
        body,
        NotificationDetails(iOS: iosDetails),
        payload: payloadJson,
      );
    }
  }

  /// Enregistre le jeton FCM sur l’API (`PUT /auth/me/fcm-token`) si session active ([TokenStorage]).
  Future<void> registerTokenWithBackend(String? fcmToken) async {
    if (fcmToken == null || fcmToken.isEmpty) return;
    final access = await TokenStorage().getAccessToken();
    if (access == null || access.isEmpty) {
      debugPrint('FCM : pas de session — enregistrement push ignoré');
      return;
    }
    try {
      await _api.put<Map<String, dynamic>>(
        '/auth/me/fcm-token',
        body: {'fcm_registration_token': fcmToken},
        fromJson: (d) => d as Map<String, dynamic>,
      );
      debugPrint('FCM : jeton enregistré côté API');
    } catch (e, st) {
      debugPrint('FCM : échec enregistrement API $e\n$st');
    }
  }

  /// Relit le jeton FCM courant et le pousse vers l’API (après login ou restauration de session).
  Future<void> syncBackendTokenIfSessionOpen() async {
    final t = await FirebaseMessaging.instance.getToken();
    await registerTokenWithBackend(t);
  }

  /// Supprime le jeton côté serveur avant déconnexion locale (nécessite encore un JWT valide).
  Future<void> clearBackendFcmRegistration() async {
    final access = await TokenStorage().getAccessToken();
    if (access == null || access.isEmpty) return;
    try {
      await _api.delete('/auth/me/fcm-token');
      debugPrint('FCM : jeton supprimé côté API');
    } catch (e) {
      debugPrint('FCM : suppression API ignorée ($e)');
    }
  }
}
