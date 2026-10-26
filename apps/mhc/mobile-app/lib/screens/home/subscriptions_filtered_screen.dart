import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/subscription.dart';
import '../../services/api_services.dart';
import '../subscription/nouvelle_souscription_screen.dart';
import 'subscription_detail_screen.dart';

/// Filtre des tuiles compteurs du tableau de bord.
enum SubscriptionsFilter { pending, expired }

const _pendingStatuses = {
  'en_attente',
  'pending',
  'en_attente_validation',
  'en_attente_paiement',
};
const _expiredStatuses = {'expiree', 'expired'};

/// Brouillons et « à payer » : supprimables par l'assuré (sinon purge
/// automatique au bout de 3 jours côté serveur).
const _deletableStatuses = {'en_attente', 'pending', 'en_attente_paiement'};

bool matchesSubscriptionsFilter(SubscriptionModel s, SubscriptionsFilter f) =>
    f == SubscriptionsFilter.pending
        ? _pendingStatuses.contains(s.statut)
        : _expiredStatuses.contains(s.statut);

/// Liste « En attente » (validation, à payer, brouillons) ou « Expirées ».
class SubscriptionsFilteredScreen extends StatefulWidget {
  const SubscriptionsFilteredScreen({super.key, required this.filter});

  final SubscriptionsFilter filter;

  @override
  State<SubscriptionsFilteredScreen> createState() =>
      _SubscriptionsFilteredScreenState();
}

class _SubscriptionsFilteredScreenState
    extends State<SubscriptionsFilteredScreen> {
  final SubscriptionsService _api = SubscriptionsService();
  List<SubscriptionModel> _list = const [];
  bool _loading = true;
  String? _error;

  String get _title => widget.filter == SubscriptionsFilter.pending
      ? 'En attente'
      : 'Expirées';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _error = null;
      if (_list.isEmpty) _loading = true;
    });
    try {
      final all = await _api.getSubscriptions(forceRefresh: true);
      if (!mounted) return;
      setState(() {
        _list = all
            .where((s) => matchesSubscriptionsFilter(s, widget.filter))
            .toList();
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = apiErrorToUserMessage(e);
        _loading = false;
      });
    }
  }

  Future<void> _open(SubscriptionModel s) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => _pendingStatuses.contains(s.statut)
            ? NouvelleSouscriptionScreen(resumeSubscriptionId: s.id)
            : SubscriptionDetailScreen(subscription: s),
      ),
    );
    if (mounted) _load();
  }

  Future<void> _delete(SubscriptionModel s) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Supprimer la souscription ?'),
        content: Text(
          'La souscription ${_label(s)} sera définitivement supprimée.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Annuler'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await _api.deleteSubscription(s.id);
      if (!mounted) return;
      setState(() => _list = _list.where((e) => e.id != s.id).toList());
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Souscription supprimée')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(apiErrorToUserMessage(e)),
          backgroundColor: AppColors.danger,
        ),
      );
    }
  }

  String _label(SubscriptionModel s) => s.numeroSouscription.isNotEmpty
      ? s.numeroSouscription
      : '#${s.id}';

  static (String, Color) _status(String statut) {
    switch (statut) {
      case 'en_attente':
      case 'pending':
        return ('Brouillon', AppColors.warning);
      case 'en_attente_validation':
        return ('En validation', const Color(0xFFEA580C));
      case 'en_attente_paiement':
        return ('À payer', AppColors.secondary);
      default:
        return ('Expirée', AppColors.danger);
    }
  }

  static String _fmt(DateTime? d) => d == null
      ? '–'
      : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kMhContentBackground,
      appBar: MhAppBar(title: _title, showBell: false),
      body: _body(),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppColors.danger)),
              TextButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh),
                label: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      );
    }
    if (_list.isEmpty) {
      return Center(
        child: Text(
          widget.filter == SubscriptionsFilter.pending
              ? 'Aucune souscription en attente'
              : 'Aucune souscription expirée',
          style: const TextStyle(color: AppColors.mutedText),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: EdgeInsets.fromLTRB(
            20, 16, 20, MediaQuery.of(context).padding.bottom + 24),
        itemCount: _list.length + (widget.filter == SubscriptionsFilter.pending ? 1 : 0),
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (context, i) {
          if (i == _list.length) {
            return const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text(
                'Les brouillons et souscriptions à payer non finalisés sont '
                'supprimés automatiquement au bout de 3 jours.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 11, color: AppColors.mutedText),
              ),
            );
          }
          final s = _list[i];
          final (label, color) = _status(s.statut);
          final v = s.projetVoyage;
          final dest = v?.destinationDisplay ?? v?.destination ?? '';
          return MHSurfaceCard(
            padding: EdgeInsets.zero,
            child: InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: () => _open(s),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 6, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Flexible(
                                child: Text(
                                  _label(s),
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.secondary,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: color.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(
                                  label,
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                    color: color,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text(
                            [
                              s.produitAssurance?.nom,
                              if (dest.isNotEmpty) dest,
                              if (v != null) 'Départ ${_fmt(v.dateDepart)}',
                              if (s.prixApplique > 0)
                                '${s.prixApplique.toStringAsFixed(0)} XAF',
                            ].whereType<String>().join(' • '),
                            style: const TextStyle(
                                fontSize: 12, color: AppColors.mutedText),
                          ),
                        ],
                      ),
                    ),
                    if (_deletableStatuses.contains(s.statut))
                      IconButton(
                        tooltip: 'Supprimer',
                        onPressed: () => _delete(s),
                        icon: const Icon(Icons.delete_outline,
                            color: AppColors.danger),
                      )
                    else
                      const Padding(
                        padding: EdgeInsets.only(right: 8),
                        child: Icon(Icons.chevron_right,
                            color: AppColors.secondary),
                      ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
