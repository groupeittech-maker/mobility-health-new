import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/config/api_config.dart';
import '../../core/constants/app_colors.dart';
import '../../core/utils/api_error_helper.dart';
import '../../models/subscription.dart';
import '../../services/auth_service.dart';
import '../../services/api_services.dart';

/// Tableau de bord : Bienvenue, 4 cartes métriques (API), partenaires. Pas de bouton "Nouvelle souscription" (accès via onglet Souscription > action AppBar).
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  String _displayName = '';
  int _activeCount = 0;
  int _pendingCount = 0;
  int _expiredCount = 0;
  int _attestationsCount = 0;
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _assureurs = [];
  final ScrollController _partnerScrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _load();
    WidgetsBinding.instance.addPostFrameCallback((_) => _startPartnerAutoScroll());
  }

  @override
  void dispose() {
    _partnerScrollController.dispose();
    super.dispose();
  }

  Future<List<Map<String, dynamic>>> _safeAssureurs() async {
    try {
      return await AssureursService().getAssureurs();
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }

  void _startPartnerAutoScroll() async {
    while (mounted) {
      await Future<void>.delayed(const Duration(milliseconds: 60));
      if (!mounted || !_partnerScrollController.hasClients) break;
      final pos = _partnerScrollController.position;
      final maxExtent = pos.maxScrollExtent;
      if (maxExtent <= 0) continue;
      final loopAt = maxExtent / 2;
      double newOffset = pos.pixels + 0.4;
      if (newOffset >= loopAt) newOffset = 0.0;
      _partnerScrollController.jumpTo(newOffset);
    }
  }

  Future<void> _load() async {
    AuthService.instance.getDisplayName().then((name) {
      if (mounted) setState(() => _displayName = name);
    });
    try {
      final results = await Future.wait<Object?>([
        SubscriptionsService().getSubscriptions(limit: 1000),
        AttestationsService().getUserAttestations().then((l) => l.length),
        _safeAssureurs(),
      ]);
      if (!mounted) return;
      final subs = results[0]! as List<SubscriptionModel>;
      final attCount = results[1]! as int;
      final assureurs = results[2]! as List<Map<String, dynamic>>;
      final active = subs.where((s) => s.statut == 'active').length;
      final pending = subs.where((s) => s.statut == 'en_attente' || s.statut == 'pending').length;
      final expired = subs.where((s) => s.statut == 'expiree' || s.statut == 'expired').length;
      setState(() {
        _activeCount = active;
        _pendingCount = pending;
        _expiredCount = expired;
        _attestationsCount = attCount;
        _assureurs = assureurs;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _loading = false;
        _error = apiErrorToUserMessage(e);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
          padding: EdgeInsets.fromLTRB(20, 16, 20, bottomPadding),
          children: [
            Text(
              'Mon Tableau de Bord',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: const Color(0xFF1E293B),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _displayName.isEmpty ? 'Bienvenue' : 'Bienvenue, $_displayName',
              style: theme.textTheme.bodyLarge?.copyWith(
                color: AppColors.mutedText,
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: AppColors.danger, fontSize: 13)),
            ],
            const SizedBox(height: 20),
            GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: 2,
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.35,
            children: [
              _MetricCard(
                title: 'Souscr. actives',
                value: _loading ? '...' : '$_activeCount',
                icon: Icons.check_circle,
                iconColor: AppColors.success,
                iconBgColor: AppColors.success.withValues(alpha: 0.15),
              ),
              _MetricCard(
                title: 'En attente',
                value: _loading ? '...' : '$_pendingCount',
                icon: Icons.hourglass_empty,
                iconColor: AppColors.warning,
                iconBgColor: AppColors.warning.withValues(alpha: 0.15),
              ),
              _MetricCard(
                title: 'Expirées',
                value: _loading ? '...' : '$_expiredCount',
                icon: Icons.cancel,
                iconColor: AppColors.danger,
                iconBgColor: AppColors.danger.withValues(alpha: 0.15),
              ),
              _MetricCard(
                title: 'Attestations',
                value: _loading ? '...' : '$_attestationsCount',
                icon: Icons.description_outlined,
                iconColor: const Color(0xFF2563EB),
                iconBgColor: const Color(0xFF2563EB).withValues(alpha: 0.15),
                onTap: () => context.push('/attestations'),
              ),
            ],
          ),
          const SizedBox(height: 28),
          Text(
            'Nos partenaires assurance',
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
              color: const Color(0xFF1E293B),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 140,
            child: ListView.separated(
              controller: _partnerScrollController,
              scrollDirection: Axis.horizontal,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: (_assureurs.isEmpty ? 3 : _assureurs.length) * 2,
              separatorBuilder: (_, __) => const SizedBox(width: 12),
              itemBuilder: (context, i) {
                final n = _assureurs.isEmpty ? 3 : _assureurs.length;
                final index = i % n;
                if (_assureurs.isEmpty) {
                  final fallbacks = ['ARC', 'AXA afrique', 'NSIA'];
                  return _PartnerCard(label: fallbacks[index], logoUrl: null);
                }
                final a = _assureurs[index];
                return _PartnerCard(
                  label: a['nom'] as String? ?? '—',
                  logoUrl: a['id'] != null
                      ? '${ApiConfig.baseUrl}/assureurs/${a['id']}/logo'
                      : null,
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.iconColor,
    required this.iconBgColor,
    this.onTap,
  });

  final String title;
  final String value;
  final IconData icon;
  final Color iconColor;
  final Color iconBgColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    Widget card = Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: AppColors.mutedText,
                    fontWeight: FontWeight.w500,
                    fontSize: 12,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: iconBgColor,
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, size: 20, color: iconColor),
              ),
            ],
          ),
          Text(
            value,
            style: theme.textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: const Color(0xFF1E293B),
            ),
          ),
        ],
      ),
    );
    if (onTap != null) {
      card = InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: card,
      );
    }
    return card;
  }
}

class _PartnerCard extends StatelessWidget {
  const _PartnerCard({required this.label, this.logoUrl});

  final String label;
  final String? logoUrl;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 120,
      padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (logoUrl != null && logoUrl!.isNotEmpty)
            SizedBox(
              height: 56,
              width: 56,
              child: Image.network(
                logoUrl!,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => _avatarFallback(label),
              ),
            )
          else
            _avatarFallback(label),
          const SizedBox(height: 8),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: const Color(0xFF475569),
                  fontWeight: FontWeight.w600,
                ),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _avatarFallback(String label) {
    return CircleAvatar(
      radius: 28,
      backgroundColor: const Color(0xFFE2E8F0),
      child: Text(
        label.isNotEmpty ? label.substring(0, 1).toUpperCase() : '?',
        style: const TextStyle(
          fontWeight: FontWeight.bold,
          color: Color(0xFF64748B),
          fontSize: 20,
        ),
      ),
    );
  }
}
