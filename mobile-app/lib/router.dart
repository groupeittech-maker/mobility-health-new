import 'package:go_router/go_router.dart';

import 'screens/forgot_password_screen.dart';
import 'screens/home/attestations_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/referent/referent_dossier_detail_screen.dart';
import 'screens/referent/referent_invoice_detail_screen.dart';
import 'screens/referent/referent_notifications_screen.dart';
import 'screens/referent/referent_profile_screen.dart';
import 'screens/referent/referent_shell_screen.dart';
import 'screens/register_screen.dart';
import 'screens/splash/splash_screen.dart';
import 'screens/subscription/nouvelle_souscription_screen.dart';

final appRouter = GoRouter(
  initialLocation: '/splash',
  routes: [
    GoRoute(
      path: '/splash',
      builder: (context, state) => const SplashScreen(),
    ),
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/register',
      builder: (context, state) => const RegisterScreen(),
    ),
    GoRoute(
      path: '/forgot-password',
      builder: (context, state) => const ForgotPasswordScreen(),
    ),
    GoRoute(
      path: '/home',
      builder: (context, state) => const HomeScreen(),
    ),
    GoRoute(
      path: '/referent',
      builder: (context, state) => const ReferentShellScreen(),
    ),
    GoRoute(
      path: '/referent/dossier/:alertId',
      builder: (context, state) {
        final id = int.tryParse(state.pathParameters['alertId'] ?? '') ?? 0;
        return ReferentDossierDetailScreen(alerteId: id);
      },
    ),
    GoRoute(
      path: '/referent/facture/:invoiceId',
      builder: (context, state) {
        final id = int.tryParse(state.pathParameters['invoiceId'] ?? '') ?? 0;
        return ReferentInvoiceDetailScreen(invoiceId: id);
      },
    ),
    GoRoute(
      path: '/referent/notifications',
      builder: (context, state) => const ReferentNotificationsPage(),
    ),
    GoRoute(
      path: '/referent/profil',
      builder: (context, state) => const ReferentProfileScreen(),
    ),
    GoRoute(
      path: '/subscription/new',
      builder: (context, state) => const NouvelleSouscriptionScreen(),
    ),
    GoRoute(
      path: '/attestations',
      builder: (context, state) => const AttestationsScreen(),
    ),
  ],
);
