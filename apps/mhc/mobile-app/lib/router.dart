import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'core/widgets/mh_states.dart';
import 'screens/forgot_password_screen.dart';
import 'screens/home/attestations_screen.dart';
import 'screens/home/ecards_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/home/reseau_mhc_screen.dart';
import 'screens/login_screen.dart';
import 'screens/profile/change_destination_screen.dart';
import 'screens/profile/mon_profil_screen.dart';
import 'screens/profile/profile_edit_screens.dart';
import 'screens/referent/referent_dossier_detail_screen.dart';
import 'screens/referent/referent_invoice_detail_screen.dart';
import 'screens/referent/referent_notifications_screen.dart';
import 'screens/referent/referent_profile_screen.dart';
import 'screens/referent/referent_shell_screen.dart';
import 'screens/register_screen.dart';
import 'screens/verify_email_screen.dart';
import 'screens/splash/splash_screen.dart';
import 'screens/subscription/nouvelle_souscription_screen.dart';
import 'screens/welcome_screen.dart';

final appRouter = GoRouter(
  initialLocation: '/splash',
  errorBuilder: (context, state) => const Scaffold(
    backgroundColor: Colors.transparent,
    body: MhNotFoundView(),
  ),
  routes: [
    GoRoute(
      path: '/splash',
      builder: (context, state) => const SplashScreen(),
    ),
    GoRoute(
      path: '/welcome',
      builder: (context, state) => const WelcomeScreen(),
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
      path: '/verify-email',
      builder: (context, state) {
        final email = state.uri.queryParameters['email'] ?? '';
        if (email.trim().isEmpty) {
          return const RegisterScreen();
        }
        return VerifyEmailScreen(
          email: email.trim(),
          channel: state.uri.queryParameters['channel'],
        );
      },
    ),
    GoRoute(
      path: '/forgot-password',
      builder: (context, state) => const ForgotPasswordScreen(),
    ),
    GoRoute(
      path: '/home',
      builder: (context, state) {
        final tab = int.tryParse(state.uri.queryParameters['tab'] ?? '') ?? 0;
        return HomeScreen(initialTab: tab.clamp(0, 4));
      },
    ),
    GoRoute(
      path: '/subscription/new',
      builder: (context, state) {
        final resumeId =
            int.tryParse(state.uri.queryParameters['subscription_id'] ?? '');
        return NouvelleSouscriptionScreen(resumeSubscriptionId: resumeId);
      },
    ),
    GoRoute(
      path: '/ecards',
      builder: (context, state) => const EcardsScreen(),
    ),
    GoRoute(
      path: '/reseau',
      builder: (context, state) => const ReseauMhcScreen(),
    ),
    GoRoute(
      path: '/profile',
      builder: (context, state) => const MonProfilScreen(),
    ),
    GoRoute(
      path: '/profile/edit-email',
      builder: (context, state) => const EditEmailScreen(),
    ),
    GoRoute(
      path: '/profile/edit-phone',
      builder: (context, state) => const EditPhoneScreen(),
    ),
    GoRoute(
      path: '/profile/edit-contact',
      builder: (context, state) => const EditContactScreen(),
    ),
    GoRoute(
      path: '/profile/change-destination',
      builder: (context, state) => const ChangeDestinationScreen(),
    ),
    GoRoute(
      path: '/referent',
      builder: (context, state) {
        final tab = int.tryParse(state.uri.queryParameters['tab'] ?? '') ?? 0;
        final sub = int.tryParse(state.uri.queryParameters['sub'] ?? '') ?? 0;
        return ReferentShellScreen(
          key: ValueKey('referent_${tab}_$sub'),
          initialNavIndex: tab.clamp(0, 3),
          initialSubTab: sub.clamp(0, 1),
        );
      },
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
      path: '/attestations',
      builder: (context, state) => const AttestationsScreen(),
    ),
  ],
);
