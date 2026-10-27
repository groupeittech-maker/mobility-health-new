import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../providers/auth_provider.dart';
import '../../providers/locale_provider.dart';
import '../../services/account_service.dart';
import '../../services/auth_service.dart';

/// Paramètres du compte (workflow V3 §3.3) : langue (fr/en/es/pt/ar — arabe
/// en RTL), notifications non essentielles, adresse, suppression du compte.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  static const _languages = {
    'fr': 'Français',
    'en': 'English',
    'es': 'Español',
    'pt': 'Português',
    'ar': 'العربية',
  };

  bool _loading = true;
  bool _saving = false;
  String? _langue = 'fr';
  bool _nonEssential = true;
  List<String> _available = const ['fr'];
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await AccountService.instance.getSettings();
      if (mounted) {
        setState(() {
          _langue = s['langue']?.toString() ?? 'fr';
          _nonEssential = s['notifications_non_essentielles'] != false;
          final langs = s['langues_disponibles'];
          if (langs is List) _available = langs.map((e) => e.toString()).toList();
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = apiErrorToUserMessage(e);
          _loading = false;
        });
      }
    }
  }

  void _snack(String message, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: error ? AppColors.danger : AppColors.success,
    ));
  }

  Future<void> _setLangue(String code) async {
    setState(() => _saving = true);
    try {
      await AccountService.instance.updateSettings(langue: code);
      if (mounted) {
        context.read<LocaleProvider>().setLocale(Locale(code));
        setState(() => _langue = code);
      }
    } catch (e) {
      _snack(apiErrorToUserMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _setNonEssential(bool value) async {
    setState(() => _nonEssential = value);
    try {
      await AccountService.instance.updateSettings(notificationsNonEssentielles: value);
    } catch (e) {
      if (mounted) setState(() => _nonEssential = !value);
      _snack(apiErrorToUserMessage(e), error: true);
    }
  }

  Future<void> _editAddress() async {
    final ctrl = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Mon adresse'),
        content: TextField(
          controller: ctrl,
          maxLines: 3,
          decoration: const InputDecoration(
            hintText: 'Adresse complète',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: const Text('Enregistrer'),
          ),
        ],
      ),
    );
    ctrl.dispose();
    if (result == null || result.isEmpty) return;
    try {
      await AccountService.instance.updateAddress(result);
      _snack('Adresse mise à jour.');
    } catch (e) {
      _snack(apiErrorToUserMessage(e), error: true);
    }
  }

  Future<void> _deleteAccount() async {
    final pwdCtrl = TextEditingController();
    final confirmCtrl = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Supprimer mon compte'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Votre compte sera désactivé. Vos assurances en cours de validité '
                'restent couvertes jusqu’à leur terme, conformément au contrat.',
                style: TextStyle(fontSize: 13, height: 1.4),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: pwdCtrl,
                obscureText: true,
                decoration: const InputDecoration(
                    labelText: 'Mot de passe', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: confirmCtrl,
                decoration: const InputDecoration(
                  labelText: 'Saisissez SUPPRIMER pour confirmer',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      pwdCtrl.dispose();
      confirmCtrl.dispose();
      return;
    }
    try {
      final res = await AccountService.instance.deleteAccount(
        password: pwdCtrl.text,
        confirmation: confirmCtrl.text,
      );
      pwdCtrl.dispose();
      confirmCtrl.dispose();
      final n = res['assurances_actives'] ?? 0;
      if (!mounted) return;
      _snack(n is int && n > 0
          ? 'Compte supprimé. $n assurance(s) reste(nt) couverte(s) jusqu’à leur terme.'
          : 'Compte supprimé.');
      await AuthService.instance.logout();
      if (!mounted) return;
      await context.read<AuthProvider>().checkAuth();
      if (!mounted) return;
      context.go('/login');
    } catch (e) {
      pwdCtrl.dispose();
      confirmCtrl.dispose();
      _snack(apiErrorToUserMessage(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Paramètres'),
      body: _loading
          ? const MhLoadingView()
          : _error != null
              ? MhOfflineView(onRetry: _load)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
                  children: [
                    MHSurfaceCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Langue de l’application',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.secondary,
                                  fontSize: 14)),
                          const SizedBox(height: 10),
                          ..._available.map((code) => RadioListTile<String>(
                                dense: true,
                                contentPadding: EdgeInsets.zero,
                                value: code,
                                groupValue: _langue,
                                onChanged: _saving
                                    ? null
                                    : (v) {
                                        if (v != null) _setLangue(v);
                                      },
                                title: Text(_languages[code] ?? code,
                                    style: const TextStyle(fontSize: 14)),
                              )),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    MHSurfaceCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Notifications',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.secondary,
                                  fontSize: 14)),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            value: _nonEssential,
                            onChanged: _setNonEssential,
                            title: const Text('Notifications non essentielles',
                                style: TextStyle(fontSize: 14)),
                            subtitle: const Text(
                              'Rappels, conseils et informations commerciales. '
                              'Les alertes de sécurité et de paiement restent actives.',
                              style: TextStyle(fontSize: 12, color: AppColors.mutedText),
                            ),
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
                          const Text('Coordonnées',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.secondary,
                                  fontSize: 14)),
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: const Icon(Icons.home_outlined,
                                color: AppColors.secondary),
                            title: const Text('Adresse postale',
                                style: TextStyle(fontSize: 14)),
                            subtitle: const Text('Modifiable directement',
                                style:
                                    TextStyle(fontSize: 12, color: AppColors.mutedText)),
                            trailing: const Icon(Icons.edit_outlined,
                                size: 18, color: AppColors.brandTeal),
                            onTap: _editAddress,
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
                          const Text('Identité',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.secondary,
                                  fontSize: 14)),
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: const Icon(Icons.verified_user_outlined,
                                color: AppColors.secondary),
                            title: const Text("Vérification d'identité (eKYC)",
                                style: TextStyle(fontSize: 14)),
                            subtitle: const Text(
                                'Document, selfie et puce NFC du passeport',
                                style: TextStyle(
                                    fontSize: 12, color: AppColors.mutedText)),
                            trailing: const Icon(Icons.chevron_right,
                                size: 18, color: AppColors.brandTeal),
                            onTap: () =>
                                context.push('/ekyc-verification'),
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
                          const Text('Zone dangereuse',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.danger,
                                  fontSize: 14)),
                          const SizedBox(height: 6),
                          const Text(
                            'La suppression désactive votre compte. Les assurances '
                            'en cours de validité restent couvertes jusqu’à leur terme.',
                            style: TextStyle(
                                fontSize: 12, color: AppColors.mutedText, height: 1.4),
                          ),
                          const SizedBox(height: 10),
                          SizedBox(
                            width: double.infinity,
                            height: 44,
                            child: OutlinedButton.icon(
                              onPressed: _deleteAccount,
                              icon: const Icon(Icons.delete_outline,
                                  color: AppColors.danger, size: 18),
                              label: const Text('Supprimer mon compte',
                                  style: TextStyle(
                                      color: AppColors.danger,
                                      fontWeight: FontWeight.w600)),
                              style: OutlinedButton.styleFrom(
                                side: const BorderSide(color: Color(0xFFF3C2C7)),
                                shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(10)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
    );
  }
}
