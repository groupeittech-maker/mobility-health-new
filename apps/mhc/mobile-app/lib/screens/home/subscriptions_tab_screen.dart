import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../core/widgets/mh_text_highlight.dart';
import '../../models/subscription.dart';
import '../../services/api_services.dart';
import 'subscription_detail_screen.dart';

/// Onglet « Souscription » (kit) : CTA nouvelle souscription + liste des
/// contrats groupée par statut (actives, en attente, expirées).
class SubscriptionsTabScreen extends StatefulWidget {
  const SubscriptionsTabScreen({super.key});

  @override
  State<SubscriptionsTabScreen> createState() => _SubscriptionsTabScreenState();
}

class _SubscriptionsTabScreenState extends State<SubscriptionsTabScreen> {
  final SubscriptionsService _subsService = SubscriptionsService();
  List<SubscriptionModel> _list = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    final peek = SubscriptionsService.peekSubscriptionsCache();
    if (peek != null) {
      _list = peek;
      _loading = false;
    }
    _load();
  }

  Future<void> _load({bool forceRefresh = false}) async {
    setState(() {
      _error = null;
      if (_list.isEmpty) _loading = true;
    });
    try {
      final list = await _subsService.getSubscriptions(
        limit: 500,
        forceRefresh: forceRefresh,
      );
      if (mounted) {
        setState(() {
          _list = list;
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    final active = _list.where((s) => s.isActive).toList();
    final pending = _list.where((s) => s.isPending).toList();
    final expired = _list.where((s) => s.isExpired).toList();
    final other = _list
        .where((s) => !s.isActive && !s.isPending && !s.isExpired)
        .toList();

    return ColoredBox(
      color: kMhContentBackground,
      child: RefreshIndicator(
        onRefresh: () => _load(forceRefresh: true),
        child: ListView(
          padding: EdgeInsets.fromLTRB(20, 16, 20, bottomPadding),
          children: [
            const MHSectionTitle(
              title: 'Souscription',
              subtitle: 'Vos contrats et nouvelles demandes.',
            ),
            const SizedBox(height: 16),
            MHGradientButton(
              label: 'Nouvelle souscription',
              onPressed: () => context.push('/subscription/new'),
            ),
            const SizedBox(height: 18),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              MHSurfaceCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  children: [
                    Text(
                      _error!,
                      style: const TextStyle(
                          color: AppColors.danger, fontSize: 13),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 10),
                    TextButton.icon(
                      onPressed: () => _load(forceRefresh: true),
                      icon: const Icon(Icons.refresh, size: 18),
                      label: const Text('Réessayer'),
                    ),
                  ],
                ),
              )
            else if (_list.isEmpty)
              MHSurfaceCard(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'Aucune souscription pour le moment. Lancez votre première '
                  'demande pour obtenir votre carte d’assurance voyage.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: AppColors.mutedText,
                    height: 1.5,
                  ),
                ),
              )
            else ...[
              if (active.isNotEmpty)
                _Section(title: 'Actives', items: active),
              if (pending.isNotEmpty)
                _Section(title: 'En attente', items: pending),
              if (expired.isNotEmpty)
                _Section(title: 'Expirées', items: expired),
              if (other.isNotEmpty)
                _Section(title: 'Autres', items: other),
            ],
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.items});

  final String title;
  final List<SubscriptionModel> items;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Text(
            title,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: AppColors.brandTeal,
              letterSpacing: 0.5,
            ),
          ),
        ),
        ...items.map((s) => _SubCard(subscription: s)),
        const SizedBox(height: 12),
      ],
    );
  }
}

class _SubCard extends StatelessWidget {
  const _SubCard({required this.subscription});

  final SubscriptionModel subscription;

  @override
  Widget build(BuildContext context) {
    final s = subscription;
    final statusColor = s.isActive
        ? AppColors.success
        : s.isPending
            ? AppColors.warning
            : AppColors.mutedText;
    final statusLabel = s.isActive
        ? 'Active'
        : s.isPending
            ? 'En attente'
            : s.isExpired
                ? 'Expirée'
                : s.statut;
    return MHSurfaceCard(
      padding: const EdgeInsets.all(14),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => SubscriptionDetailScreen(subscription: s),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.secondary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.verified_user_outlined,
                color: AppColors.secondary, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  s.numeroSouscription.isNotEmpty
                      ? s.numeroSouscription
                      : 'Souscription #${s.id}',
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    color: AppColors.secondary,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  s.produitAssurance?.nom ??
                      'Produit #${s.produitAssuranceId}',
                  style: const TextStyle(
                      fontSize: 11, color: AppColors.mutedText),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${s.prixApplique.toStringAsFixed(0)} XAF',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 12,
                  color: AppColors.secondary,
                ),
              ),
              const SizedBox(height: 4),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  statusLabel,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
