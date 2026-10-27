import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../providers/auth_provider.dart';
import '../../services/account_service.dart';
import '../../services/auth_service.dart';
import '../../core/storage/token_storage.dart';

/// Sécurité du compte (workflow V3 §3.2) : changement de mot de passe
/// (ancien + nouveau + confirmation), fermeture des autres sessions,
/// lien vers « mot de passe oublié ».
class SecurityScreen extends StatefulWidget {
  const SecurityScreen({super.key});

  @override
  State<SecurityScreen> createState() => _SecurityScreenState();
}

class _SecurityScreenState extends State<SecurityScreen> {
  final _currentCtrl = TextEditingController();
  final _newCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  bool _saving = false;
  bool _revoking = false;
  String? _error;
  String? _success;

  @override
  void dispose() {
    _currentCtrl.dispose();
    _newCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  void _snack(String message, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: error ? AppColors.danger : AppColors.success,
    ));
  }

  Future<void> _changePassword() async {
    final current = _currentCtrl.text;
    final next = _newCtrl.text;
    final confirm = _confirmCtrl.text;
    if (current.isEmpty || next.isEmpty || confirm.isEmpty) {
      setState(() => _error = 'Renseignez les trois champs.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
      _success = null;
    });
    try {
      final tokens = await AccountService.instance.changePassword(
        currentPassword: current,
        newPassword: next,
        confirmPassword: confirm,
      );
      // Le backend révoque les autres sessions et renvoie de nouveaux jetons.
      final storage = TokenStorage();
      final access = tokens['access_token']?.toString();
      final refresh = tokens['refresh_token']?.toString();
      if (access != null) await storage.setAccessToken(access);
      if (refresh != null) await storage.setRefreshToken(refresh);
      _currentCtrl.clear();
      _newCtrl.clear();
      _confirmCtrl.clear();
      setState(() => _success =
          'Mot de passe modifié. Les autres appareils ont été déconnectés.');
    } catch (e) {
      setState(() => _error = apiErrorToUserMessage(e));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _revokeAll() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Fermer toutes les sessions ?'),
        content: const Text(
          'Vous serez déconnecté de tous les appareils, y compris celui-ci. '
          'Vous devrez vous reconnecter avec votre mot de passe.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Fermer les sessions'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _revoking = true);
    try {
      await AccountService.instance.revokeAllSessions();
    } catch (_) {
      // Même en cas d'erreur réseau, on purge la session locale.
    }
    if (!mounted) return;
    await AuthService.instance.logout();
    if (!mounted) return;
    await context.read<AuthProvider>().checkAuth();
    if (!mounted) return;
    context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Sécurité'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        children: [
          MHSurfaceCard(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Changer le mot de passe',
                    style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: AppColors.secondary,
                        fontSize: 14)),
                const SizedBox(height: 6),
                const Text(
                  'Un mot de passe oublié ? Utilisez « Mot de passe oublié » depuis l’écran de connexion.',
                  style: TextStyle(fontSize: 12, color: AppColors.mutedText, height: 1.4),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _currentCtrl,
                  obscureText: true,
                  decoration: MHSurfaceCard.input(labelText: 'Mot de passe actuel'),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _newCtrl,
                  obscureText: true,
                  decoration: MHSurfaceCard.input(labelText: 'Nouveau mot de passe'),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _confirmCtrl,
                  obscureText: true,
                  decoration: MHSurfaceCard.input(labelText: 'Confirmer le nouveau mot de passe'),
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () => context.push('/forgot-password'),
                    child: const Text('Mot de passe oublié ?',
                        style: TextStyle(fontSize: 12, color: AppColors.brandTeal)),
                  ),
                ),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(_error!,
                        style: const TextStyle(color: AppColors.danger, fontSize: 13)),
                  ),
                if (_success != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(_success!,
                        style: const TextStyle(color: AppColors.success, fontSize: 13)),
                  ),
                MHGradientButton(
                  label: 'Mettre à jour le mot de passe',
                  loading: _saving,
                  onPressed: _changePassword,
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
                const Text('Sessions actives',
                    style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: AppColors.secondary,
                        fontSize: 14)),
                const SizedBox(height: 6),
                const Text(
                  'Votre compte est limité à une session : une nouvelle connexion '
                  'sur un autre appareil ferme automatiquement la précédente.',
                  style: TextStyle(fontSize: 12, color: AppColors.mutedText, height: 1.4),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  height: 44,
                  child: OutlinedButton.icon(
                    onPressed: _revoking ? null : _revokeAll,
                    icon: const Icon(Icons.devices_other, color: AppColors.danger, size: 18),
                    label: Text(
                      _revoking ? 'Fermeture…' : 'Fermer toutes les sessions',
                      style: const TextStyle(
                          color: AppColors.danger, fontWeight: FontWeight.w600),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: Color(0xFFF3C2C7)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          const MHSurfaceCard(
            padding: EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Blocage automatique',
                    style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: AppColors.secondary,
                        fontSize: 14)),
                SizedBox(height: 6),
                Text(
                  'Après 5 tentatives de connexion erronées, le compte est bloqué '
                  'temporairement. Utilisez « Mot de passe oublié » pour le débloquer '
                  'immédiatement.',
                  style: TextStyle(fontSize: 12, color: AppColors.mutedText, height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
