import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/user.dart';
import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';

/// « Mon profil » (kit) : coordonnées modifiables, personne à contacter,
/// sécurité, déconnexion.
class MonProfilScreen extends StatefulWidget {
  const MonProfilScreen({super.key});

  @override
  State<MonProfilScreen> createState() => _MonProfilScreenState();
}

class _MonProfilScreenState extends State<MonProfilScreen> {
  UserModel? _user;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final u = await AuthService.instance.getMe();
      if (mounted) {
        setState(() {
          _user = u;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _loading = false;
        });
      }
    }
  }

  String _masked(String? value) {
    if (value == null || value.trim().isEmpty) return 'Non renseigné';
    return value;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Mon profil'),
      body: _loading
          ? const MhLoadingView()
          : _error != null
              ? MhOfflineView(onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
                    children: [
                      MHSurfaceCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _BoxTitle('Mes coordonnées'),
                            _EditRow(
                              label: 'Nom complet',
                              value: _masked(_user?.fullName),
                            ),
                            _EditRow(
                              label: 'Adresse e-mail',
                              value: _masked(_user?.email),
                              actionLabel: 'Modifier',
                              onTap: () => context
                                  .push('/profile/edit-email')
                                  .then((_) => _load()),
                            ),
                            _EditRow(
                              label: 'Téléphone',
                              value: _masked(_user?.telephone),
                              actionLabel: 'Modifier',
                              onTap: () => context
                                  .push('/profile/edit-phone')
                                  .then((_) => _load()),
                            ),
                            _EditRow(
                              label: 'Pays de résidence',
                              value: _masked(_user?.paysResidence),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 14),
                      MHSurfaceCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _BoxTitle('Personne à contacter'),
                            _EditRow(
                              label: 'Nom',
                              value: _masked(_user?.nomContactUrgence),
                              actionLabel: 'Modifier',
                              onTap: () => context
                                  .push('/profile/edit-contact')
                                  .then((_) => _load()),
                            ),
                            _EditRow(
                              label: 'Téléphone',
                              value: _masked(_user?.contactUrgence),
                              actionLabel: 'Modifier',
                              onTap: () => context
                                  .push('/profile/edit-contact')
                                  .then((_) => _load()),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 14),
                      MHSurfaceCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _BoxTitle('Voyage en cours'),
                            _EditRow(
                              label: 'Destination',
                              value: 'Modifier ma destination',
                              actionLabel: 'Ouvrir',
                              onTap: () =>
                                  context.push('/profile/change-destination'),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 14),
                      MHSurfaceCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _BoxTitle('Sécurité'),
                            _EditRow(
                              label: 'Mot de passe',
                              value: '••••••••',
                              actionLabel: 'Modifier',
                              onTap: () => context.push('/forgot-password'),
                            ),
                            const _EditRow(
                              label: 'Vérification du compte',
                              value: 'Effectuée',
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                      SizedBox(
                        height: 48,
                        child: OutlinedButton.icon(
                          onPressed: () async {
                            await AuthService.instance.logout();
                            if (!context.mounted) return;
                            context.read<AuthProvider>().checkAuth();
                            context.go('/login');
                          },
                          icon: const Icon(Icons.logout,
                              color: AppColors.danger, size: 18),
                          label: const Text(
                            'Déconnexion',
                            style: TextStyle(
                              color: AppColors.danger,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Color(0xFFF3C2C7)),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }
}

class _BoxTitle extends StatelessWidget {
  const _BoxTitle(this.title);
  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: const TextStyle(
          fontWeight: FontWeight.bold,
          color: AppColors.secondary,
          fontSize: 14,
        ),
      ),
    );
  }
}

class _EditRow extends StatelessWidget {
  const _EditRow({
    required this.label,
    required this.value,
    this.actionLabel,
    this.onTap,
  });

  final String label;
  final String value;
  final String? actionLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label,
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.mutedText)),
                  const SizedBox(height: 2),
                  Text(
                    value,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF332542),
                    ),
                  ),
                ],
              ),
            ),
            if (actionLabel != null)
              Text(
                actionLabel!,
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.brandTeal,
                  fontWeight: FontWeight.w600,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
