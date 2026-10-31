import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_colors.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_stripe.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/subscription.dart';
import '../../models/user.dart';
import '../../services/account_service.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';
import '../../core/utils/api_error_helper.dart';

/// « Mon profil » (kit) : coordonnées modifiables, personne à contacter,
/// sécurité, déconnexion.
class MonProfilScreen extends StatefulWidget {
  const MonProfilScreen({super.key});

  @override
  State<MonProfilScreen> createState() => _MonProfilScreenState();
}

class _MonProfilScreenState extends State<MonProfilScreen> {
  UserModel? _user;
  SubscriptionModel? _voyageEnCours;
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
      SubscriptionModel? voyage;
      try {
        final subs = await SubscriptionsService().getSubscriptions();
        for (final s in subs) {
          if (s.isActive && s.projetVoyage != null) {
            voyage = s;
            break;
          }
        }
      } catch (_) {
        voyage = null;
      }
      if (mounted) {
        setState(() {
          _user = u;
          _voyageEnCours = voyage;
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

  Future<void> _editAdresse() async {
    final ctrl = TextEditingController(text: _user?.adresse ?? '');
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(
            16, 16, 16, 16 + MediaQuery.viewInsetsOf(ctx).bottom),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Adresse postale',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            TextField(
              controller: ctrl,
              maxLines: 3,
              decoration: MHSurfaceCard.input(
                labelText: 'Adresse postale',
                hintText: 'Rue, ville, code postal, pays',
              ),
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Enregistrer'),
              ),
            ),
          ],
        ),
      ),
    );
    if (saved == true && mounted) {
      try {
        await AccountService.instance.updateAddress(ctrl.text);
        _load();
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(apiErrorToUserMessage(e)),
          backgroundColor: AppColors.danger,
        ));
      }
    }
  }

  String _masked(String? value) {
    if (value == null || value.trim().isEmpty) return 'Non renseigné';
    return value;
  }

  String _fmtDate(DateTime? d) => d == null
      ? ''
      : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  String _voyageDates(SubscriptionModel s) {
    final v = s.projetVoyage;
    if (v == null) return 'Non renseigné';
    final dep = _fmtDate(v.dateDepart);
    final ret = _fmtDate(v.dateRetour);
    if (ret.isEmpty) return 'À partir du $dep';
    return 'Du $dep au $ret';
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
              : SafeArea(
                  bottom: false,
                  child: Column(
                    children: [
                      Expanded(
                        child: RefreshIndicator(
                          onRefresh: _load,
                          child: ListView(
                            padding:
                                const EdgeInsets.fromLTRB(20, 16, 20, 16),
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
                            _EditRow(
                              label: 'Adresse postale',
                              value: _masked(_user?.adresse),
                              actionLabel: 'Modifier',
                              onTap: _editAdresse,
                            ),
                            _EditRow(
                              label: 'Identité (nom, naissance, nationalité…)',
                              value: 'Via une réclamation avec pièce d’identité',
                              actionLabel: 'Demander',
                              onTap: () => context.push('/reclamations'),
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
                            if (_voyageEnCours?.projetVoyage == null)
                              const Padding(
                                padding: EdgeInsets.symmetric(vertical: 10),
                                child: Text(
                                  'Vous n’avez pas de voyage en cours.',
                                  style: TextStyle(
                                    fontSize: 13,
                                    color: AppColors.mutedText,
                                  ),
                                ),
                              )
                            else ...[
                              _EditRow(
                                label: 'Destination',
                                value: _voyageEnCours!.projetVoyage!
                                        .destinationDisplay ??
                                    _voyageEnCours!.projetVoyage!.destination,
                              ),
                              _EditRow(
                                label: 'Dates',
                                value: _voyageDates(_voyageEnCours!),
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: 14),
                      MHSurfaceCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _BoxTitle('Enfants mineurs'),
                            _EditRow(
                              label: 'Bénéficiaires enregistrés',
                              value: 'Liste, ajout, modification, suppression',
                              actionLabel: 'Gérer',
                              onTap: () => context.push('/enfants'),
                            ),
                          ],
                        ),
                      ),
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
