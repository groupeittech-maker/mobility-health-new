import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../providers/auth_provider.dart';

/// Écran profil / déconnexion (ouvert depuis la barre d’app du référent).
class ReferentProfileScreen extends StatelessWidget {
  const ReferentProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().currentUser;
    final name = user?.displayName ?? 'Utilisateur';

    return Scaffold(
      backgroundColor: kMhContentBackground,
      appBar: AppBar(
        title: const Text('Profil'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        backgroundColor: AppColors.cardBg,
        foregroundColor: AppColors.primary,
        elevation: 0.5,
      ),
      body: SafeArea(
        top: false,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
          CircleAvatar(
            radius: 40,
            backgroundColor: AppColors.primary.withValues(alpha: 0.15),
            child: const Icon(Icons.medical_information_outlined, size: 40, color: AppColors.primary),
          ),
          const SizedBox(height: 16),
          Text(
            name,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          const Text(
            'Médecin référent MH',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.mutedText),
          ),
          if (user?.email != null) ...[
            const SizedBox(height: 8),
            Text(user!.email, textAlign: TextAlign.center, style: const TextStyle(fontSize: 13)),
          ],
          const SizedBox(height: 32),
          const Card(
            child: ListTile(
              leading: Icon(Icons.badge_outlined),
              title: Text('Rôle'),
              subtitle: Text(
                'Validation des urgences SOS, des rapports hospitaliers et des factures au titre médical.',
              ),
            ),
          ),
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: () async {
              await context.read<AuthProvider>().logout();
              if (!context.mounted) return;
              context.go('/login');
            },
            icon: const Icon(Icons.logout),
            label: const Text('Déconnexion'),
          ),
        ],
        ),
      ),
    );
  }
}
