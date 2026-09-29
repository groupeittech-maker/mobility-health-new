import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/config/api_config.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_ecard.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/subscription.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';
import 'historique_screen.dart';

/// « Accueil » du kit MyMHC : carte d'assurance (adulte violet, mineurs
/// turquoise), état « Demande en attente », accès rapides et partenaires.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  String _displayName = '';
  List<SubscriptionModel> _subs = const [];
  Map<int, Map<String, dynamic>> _ecards = {};
  Map<int, Uint8List> _photos = {};
  int _attestationsCount = 0;
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _assureurs = [];
  int _cardIndex = 0;

  final SubscriptionsService _subsService = SubscriptionsService();
  final EcardsService _ecardsService = EcardsService();
  final AttestationsService _attestationsService = AttestationsService();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<List<Map<String, dynamic>>> _safeAssureurs() async {
    try {
      return await AssureursService().getAssureurs();
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }

  Future<void> _load() async {
    AuthService.instance.getDisplayName().then((name) {
      if (mounted) setState(() => _displayName = name);
    });
    final cachedSubs = SubscriptionsService.peekSubscriptionsCache();
    if (cachedSubs != null && mounted) {
      setState(() => _subs = cachedSubs);
    }
    setState(() {
      _error = null;
      if (_subs.isEmpty) _loading = true;
    });
    try {
      final results = await Future.wait<Object?>([
        _subsService.getSubscriptions(limit: 1000, forceRefresh: true),
        _attestationsService
            .getUserAttestations()
            .then((l) => l.length),
        _safeAssureurs(),
      ]);
      if (!mounted) return;
      final subs = results[0]! as List<SubscriptionModel>;
      final attCount = results[1]! as int;
      final assureurs = results[2]! as List<Map<String, dynamic>>;

      final ecards = <int, Map<String, dynamic>>{};
      final photos = <int, Uint8List>{};
      for (final s in subs.where((s) => s.isActive)) {
        try {
          ecards[s.id] = await _ecardsService.getEcard(s.id);
        } catch (_) {}
        try {
          final bytes = await _ecardsService.getUserPhoto(s.id);
          if (bytes != null) photos[s.id] = Uint8List.fromList(bytes);
        } catch (_) {}
      }
      setState(() {
        _subs = subs;
        _attestationsCount = attCount;
        _assureurs = assureurs;
        _ecards = ecards;
        _photos = photos;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = apiErrorToUserMessage(e);
        });
      }
    }
  }

  String? _formatValidity(Map<String, dynamic>? ecard) {
    final raw = ecard?['coverage_end_date']?.toString() ??
        ecard?['card_expires_at']?.toString();
    if (raw == null || raw.isEmpty) return null;
    final d = DateTime.tryParse(raw);
    if (d == null) return raw;
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  }

  List<String> _minorNames(SubscriptionModel sub) {
    // Champ structuré d'abord, puis rétro-compatibilité avec les notes.
    final structured = sub.projetVoyage?.mineurs;
    if (structured != null && structured.isNotEmpty) {
      return structured
          .map((m) => m.nom)
          .where((s) => s.isNotEmpty)
          .toList();
    }
    final notes = sub.projetVoyage?.notes ?? sub.notes ?? '';
    final match = RegExp(r'Mineurs accompagnés:\s*(.+)').firstMatch(notes);
    if (match == null) return const [];
    return match
        .group(1)!
        .split(';')
        .map((s) => s.split('(').first.trim())
        .where((s) => s.isNotEmpty)
        .toList();
  }

  List<Widget> get _cards {
    final active = _subs.where((s) => s.isActive).toList();
    if (active.isEmpty) {
      return [
        MhEcardEmpty(onSubscribe: () => context.push('/subscription/new')),
      ];
    }
    final widgets = <Widget>[];
    for (final s in active) {
      final ecard = _ecards[s.id];
      final validity = _formatValidity(ecard);
      widgets.add(MhEcard(
        holderName: ecard?['holder_name']?.toString().isNotEmpty == true
            ? ecard!['holder_name'].toString()
            : _displayName.isNotEmpty
                ? _displayName
                : 'Assuré MHC',
        policyNumber: s.numeroSouscription.isNotEmpty
            ? s.numeroSouscription
            : ecard?['numero_souscription']?.toString(),
        validityLabel: validity,
        photoBytes: _photos[s.id],
      ));
      for (final child in _minorNames(s)) {
        widgets.add(MhEcard(
          holderName: child,
          policyNumber: s.numeroSouscription.isNotEmpty
              ? s.numeroSouscription
              : null,
          validityLabel: validity,
          isChild: true,
        ));
      }
    }
    return widgets;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    final pendingSubs =
        _subs.where((s) => s.statut == 'en_attente_validation' || s.isPending).toList();
    final cards = _cards;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: EdgeInsets.fromLTRB(20, 16, 20, bottomPadding),
        children: [
          Text(
            'Bonjour${_displayName.isEmpty ? '' : ', $_displayName'}',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.w700,
              color: AppColors.secondary,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Votre assurance voyage, où que vous soyez.',
            style: TextStyle(fontSize: 13, color: AppColors.mutedText),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!,
                style:
                    const TextStyle(color: AppColors.danger, fontSize: 13)),
          ],
          if (pendingSubs.isNotEmpty) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFEAFAF7),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFD7F1EC)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Demande en attente',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: AppColors.secondary,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Votre souscription nécessite une analyse. Nous vous '
                    'informerons dès que votre dossier sera traité.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: AppColors.mutedText,
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 18),
          if (_loading)
            const SizedBox(
              height: 176,
              child: Center(child: CircularProgressIndicator()),
            )
          else
            SizedBox(
              height: 176,
              child: PageView.builder(
                itemCount: cards.length,
                onPageChanged: (i) => setState(() => _cardIndex = i),
                itemBuilder: (_, i) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: cards[i],
                ),
              ),
            ),
          if (cards.length > 1)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(
                  cards.length,
                  (i) => Container(
                    width: 7,
                    height: 7,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: i == _cardIndex
                          ? AppColors.brandTeal
                          : const Color(0xFFDDD4E9),
                    ),
                  ),
                ),
              ),
            ),
          const SizedBox(height: 22),
          Row(
            children: [
              _QuickLink(
                icon: Icons.credit_card,
                label: 'Mes cartes',
                onTap: () => context.push('/ecards'),
              ),
              _QuickLink(
                icon: Icons.description_outlined,
                label: 'Attestations',
                badge: _attestationsCount > 0 ? '$_attestationsCount' : null,
                onTap: () => context.push('/attestations'),
              ),
              _QuickLink(
                icon: Icons.public,
                label: 'Réseau MHC',
                onTap: () => context.push('/reseau'),
              ),
              _QuickLink(
                icon: Icons.history,
                label: 'Historique',
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => const Scaffold(
                      backgroundColor: Colors.transparent,
                      appBar: MhAppBar(title: 'Historique'),
                      body: ColoredBox(
                        color: kMhContentBackground,
                        child: HistoriqueScreen(),
                      ),
                    ),
                  ),
                ),
              ),
              _QuickLink(
                icon: Icons.person_outline,
                label: 'Mon profil',
                onTap: () => context.push('/profile'),
              ),
            ],
          ),
          const SizedBox(height: 26),
          if (_assureurs.isNotEmpty) ...[
            Text(
              'Nos partenaires assurance',
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
                color: AppColors.secondary,
              ),
            ),
            const SizedBox(height: 10),
            SizedBox(
              height: 92,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _assureurs.length,
                separatorBuilder: (_, __) => const SizedBox(width: 10),
                itemBuilder: (context, i) {
                  final a = _assureurs[i];
                  final logoUrl = a['id'] != null
                      ? '${ApiConfig.baseUrl}/assureurs/${a['id']}/logo'
                      : null;
                  return _PartnerChip(
                    label: a['nom'] as String? ?? '—',
                    logoUrl: logoUrl,
                  );
                },
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _QuickLink extends StatelessWidget {
  const _QuickLink({
    required this.icon,
    required this.label,
    this.badge,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final String? badge;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Column(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE8E2F0)),
              ),
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  Center(
                    child: Icon(icon, color: AppColors.secondary, size: 22),
                  ),
                  if (badge != null)
                    Positioned(
                      right: -4,
                      top: -4,
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: const BoxDecoration(
                          color: Color(0xFFF03E4D),
                          shape: BoxShape.circle,
                        ),
                        child: Text(
                          badge!,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 8,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: const TextStyle(
                fontSize: 9.5,
                color: AppColors.secondary,
                fontWeight: FontWeight.w500,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}

class _PartnerChip extends StatelessWidget {
  const _PartnerChip({required this.label, this.logoUrl});

  final String label;
  final String? logoUrl;

  @override
  Widget build(BuildContext context) {
    return MHSurfaceCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      borderRadius: 12,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (logoUrl != null && logoUrl!.isNotEmpty)
            SizedBox(
              height: 40,
              width: 52,
              child: Image.network(
                logoUrl!,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => _fallback(),
              ),
            )
          else
            _fallback(),
          const SizedBox(height: 6),
          Text(
            label,
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: Color(0xFF475569),
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _fallback() => CircleAvatar(
        radius: 20,
        backgroundColor: const Color(0xFFEDE9FE),
        child: Text(
          label.isNotEmpty ? label.substring(0, 1).toUpperCase() : '?',
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            color: AppColors.secondary,
            fontSize: 14,
          ),
        ),
      );
}
