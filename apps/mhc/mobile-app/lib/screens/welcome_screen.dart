import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/constants/app_colors.dart';
import '../core/widgets/mh_kit_widgets.dart';
import '../core/widgets/mh_logo_header.dart';
import '../core/widgets/mh_stripe.dart';

/// Écran d'accueil du kit MyMHC : « Votre santé sans frontières »,
/// photo héro, Créer un compte / Se connecter, connexion sociale,
/// mention « Your Health Has No Borders ».
class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      border: Border.all(color: const Color(0xFFD6CBE2)),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'FR',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: AppColors.secondary,
                          ),
                        ),
                        Icon(Icons.keyboard_arrow_down,
                            size: 16, color: AppColors.secondary),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            const Center(child: MHLogoHeader(compact: true)),
            const SizedBox(height: 10),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Column(
                  children: [
                    // Bandeau héro de la maquette : photo voyageur + textes
                    // « Votre santé sans frontières » incrustés dans l'image.
                    ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: AspectRatio(
                        aspectRatio: 248 / 126,
                        child: Image.asset(
                          'assets/images/welcome_hero.png',
                          fit: BoxFit.cover,
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                    MhSolidButton(
                      label: 'Créer un compte',
                      onPressed: () => context.go('/register'),
                    ),
                    const SizedBox(height: 12),
                    MhOutlineArrowButton(
                      label: 'Se connecter',
                      onPressed: () => context.go('/login'),
                    ),
                    const SizedBox(height: 18),
                    const MhSocialLogin(),
                    const SizedBox(height: 18),
                    const MhProtectionCard(),
                    const SizedBox(height: 16),
                    const Text(
                      'Your Health Has No Borders.',
                      style: TextStyle(
                        fontSize: 12,
                        color: AppColors.mutedText,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                ),
              ),
            ),
            const MhStripe(),
          ],
        ),
      ),
    );
  }
}
