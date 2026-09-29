import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../constants/app_colors.dart';
import '../theme/app_theme.dart';

/// États transitoires du kit MyMHC : chargement, hors connexion, 404.

class MhLoadingView extends StatelessWidget {
  const MhLoadingView({super.key, this.message = 'Nous préparons vos informations.'});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(
            width: 44,
            height: 44,
            child: CircularProgressIndicator(
              strokeWidth: 4,
              color: AppColors.brandPurple,
              backgroundColor: Color(0xFFE5F6F3),
            ),
          ),
          const SizedBox(height: 20),
          const Text(
            'Chargement en cours',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: AppColors.secondary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 13, color: AppColors.mutedText),
          ),
        ],
      ),
    );
  }
}

class MhOfflineView extends StatelessWidget {
  const MhOfflineView({super.key, this.onRetry});

  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.wifi_off_rounded, size: 52, color: AppColors.brandTeal),
            const SizedBox(height: 20),
            const Text(
              'Connexion indisponible',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.secondary,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Vérifiez votre accès Internet, puis reprenez votre démarche.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: AppColors.mutedText),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              MHGradientButton(label: 'Réessayer', onPressed: onRetry),
            ],
          ],
        ),
      ),
    );
  }
}

class MhNotFoundView extends StatelessWidget {
  const MhNotFoundView({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              '404',
              style: TextStyle(
                fontSize: 44,
                fontWeight: FontWeight.bold,
                color: AppColors.brandTeal,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Page introuvable',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.secondary,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Cette page n’est plus disponible.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: AppColors.mutedText),
            ),
            const SizedBox(height: 24),
            MHGradientButton(
              label: 'Retour à l’accueil',
              onPressed: () => context.go('/home'),
            ),
          ],
        ),
      ),
    );
  }
}
