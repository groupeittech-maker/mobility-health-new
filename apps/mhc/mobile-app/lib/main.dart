import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:permission_handler/permission_handler.dart';

import 'app.dart';
import 'services/referent_navigation.dart';
import 'services/referent_push_service.dart';

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  await ReferentPushService.instance.updateBadgeFromData(message.data);
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    await dotenv.load(fileName: '.env');
  } catch (_) {
    // .env absent : [ApiConfig] utilise des valeurs par défaut
  }

  var firebaseReady = false;
  try {
    await Firebase.initializeApp();
    firebaseReady = true;
  } catch (e, st) {
    debugPrint(
      'Firebase non initialisé (ajoutez android/app/google-services.json depuis la console Firebase) : $e\n$st',
    );
  }

  if (firebaseReady) {
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    await ReferentPushService.instance.setupLocalNotifications();

    final coldStart = await FirebaseMessaging.instance.getInitialMessage();
    if (coldStart != null) {
      await ReferentPushService.instance
          .updateBadgeFromData(coldStart.data);
      ReferentPendingDeepLink.storeFromFcmData(coldStart.data);
    }

    await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (!kIsWeb) {
      await Permission.notification.request();
    }

    final fcm = await FirebaseMessaging.instance.getToken();
    await ReferentPushService.instance.registerTokenWithBackend(fcm);

    FirebaseMessaging.instance.onTokenRefresh.listen(
      ReferentPushService.instance.registerTokenWithBackend,
    );

    FirebaseMessaging.onMessage.listen(
      ReferentPushService.instance.handleForegroundMessage,
    );
    FirebaseMessaging.onMessageOpenedApp.listen((m) {
      ReferentPushService.instance.updateBadgeFromData(m.data);
      final map = <String, String>{
        for (final e in m.data.entries) e.key: e.value?.toString() ?? '',
      };
      WidgetsBinding.instance.addPostFrameCallback((_) {
        navigateFromReferentPushData(map);
      });
    });
  }

  runApp(const MyApp());
}
