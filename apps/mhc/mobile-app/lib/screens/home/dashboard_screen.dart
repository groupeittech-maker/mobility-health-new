import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/config/api_config.dart';
import '../../core/constants/app_colors.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_ecard.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/subscription.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';
import '../subscription/nouvelle_souscription_screen.dart';
import 'subscription_detail_screen.dart';
import 'subscriptions_filtered_screen.dart';

/// « Accueil » du kit MyMHC : carte d'assurance (adulte violet, mineurs
/// turquoise), état « Demande en attente », bandeau police, tuiles compteurs
/// (En attente / Expirées / Attestations), couverture ou voyage, accès rapides
/// et partenaires.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => DashboardScreenState();
}

class DashboardScreenState extends State<DashboardScreen>
    with WidgetsBindingObserver {
  String _displayName = '';
  List<SubscriptionModel> _subs = const [];
  Map<int, Map<String, dynamic>> _ecards = {};
  Map<int, Uint8List> _photos = {};
  int _attestationsCount = 0;
  String? _error;
  List<Map<String, dynamic>> _assureurs = [];

  final SubscriptionsService _subsService = SubscriptionsService();
  final EcardsService _ecardsService = EcardsService();
  final AttestationsService _attestationsService = AttestationsService();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  /// L'écran vit dans un IndexedStack : initState ne se rejoue pas au retour
  /// sur l'onglet — refresh public appelé par HomeScreen + reprise de l'app.
  void refresh() => _load();

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _load();
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
    });
    try {
      final results = await Future.wait<Object?>([
        _subsService.getSubscriptions(limit: 1000, forceRefresh: true),
        _attestationsService
            .getUserAttestations(forceRefresh: true)
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
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = apiErrorToUserMessage(e);
        });
      }
    }
  }

  /// Voyage le plus imminent parmi les polices actives (prochain départ).
  SubscriptionModel? get _imminentTrip {
    final active = _subs.where((s) => s.isActive).toList();
    if (active.isEmpty) return null;
    active.sort((a, b) {
      final da = a.projetVoyage?.dateDepart ?? a.dateDebut;
      final db = b.projetVoyage?.dateDepart ?? b.dateDebut;
      return da.compareTo(db);
    });
    return active.first;
  }

  String _holderName(SubscriptionModel s) {
    final n = _ecards[s.id]?['holder_name']?.toString() ?? '';
    if (n.isNotEmpty) return n;
    return _displayName.isNotEmpty ? _displayName : 'Assuré MHC';
  }

  /// « Du … au … » comme sur l'attestation d'assurance.
  String? _validity(SubscriptionModel s) {
    final e = _ecards[s.id];
    final raw = e?['coverage_end_date']?.toString() ??
        e?['card_expires_at']?.toString();
    final end = (raw != null ? DateTime.tryParse(raw) : null) ?? s.dateFin;
    return MhEcard.validityRange(s.dateDebut, end);
  }

  Future<void> _push(Widget page) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
    if (mounted) _load();
  }

  void _openDetail(SubscriptionModel s) =>
      _push(SubscriptionDetailScreen(subscription: s));

  void _openFiltered(SubscriptionsFilter f) =>
      _push(SubscriptionsFilteredScreen(filter: f));

  /// Bannière « Paiement en attente » : ouvre directement le paiement de la
  /// souscription concernée (ou la liste s'il y en a plusieurs).
  void _openPendingBanner(List<SubscriptionModel> pending) {
    final toPay =
        pending.where((s) => s.statut == 'en_attente_paiement').toList();
    final target = toPay.length == 1
        ? toPay.first
        : (toPay.isEmpty && pending.length == 1 ? pending.first : null);
    if (target != null) {
      _push(NouvelleSouscriptionScreen(resumeSubscriptionId: target.id));
    } else {
      _openFiltered(SubscriptionsFilter.pending);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final trip = _imminentTrip;
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    // « En attente » = brouillons + en attente de paiement + en attente de
    // validation, cohérent avec l'onglet Souscription (revue : compteur
    // incohérent avec le dossier réel).
    final pendingSubs = _subs
        .where((s) =>
            s.statut == 'en_attente_validation' ||
            s.statut == 'en_attente_paiement' ||
            s.isPending)
        .toList();
    final pendingPaymentCount = pendingSubs
        .where((s) => s.statut == 'en_attente_paiement')
        .length;
    final pendingDraftCount =
        pendingSubs.where((s) => s.isPending).length;

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
            'Votre santé vous accompagne partout.',
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
            InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () => _openPendingBanner(pendingSubs),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFEAFAF7),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFD7F1EC)),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            pendingPaymentCount > 0
                                ? 'Paiement en attente'
                                : 'Demande en attente',
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              color: AppColors.secondary,
                              fontSize: 13,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            pendingPaymentCount > 0
                                ? 'Vous avez $pendingPaymentCount souscription${pendingPaymentCount > 1 ? 's' : ''} '
                                    'en attente de paiement. Touchez pour finaliser.'
                                : pendingDraftCount > 0
                                    ? 'Vous avez $pendingDraftCount souscription${pendingDraftCount > 1 ? 's' : ''} '
                                        'à compléter. Touchez pour reprendre.'
                                    : 'Votre souscription nécessite une analyse. '
                                        'Nous vous informerons dès que votre '
                                        'dossier sera traité.',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: AppColors.mutedText,
                              height: 1.45,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right,
                        color: AppColors.secondary),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 18),
          // E-carte du voyage le plus imminent, entre « Paiement en attente »
          // et « Police d'assurance active ».
          if (trip != null) ...[
            GestureDetector(
              onTap: () => context.push('/ecards'),
              child: MhEcard(
                holderName: _holderName(trip),
                policyNumber: trip.numeroSouscription.isNotEmpty
                    ? trip.numeroSouscription
                    : _ecards[trip.id]?['numero_souscription']?.toString(),
                validityLabel: _validity(trip),
                photoBytes: _photos[trip.id],
              ),
            ),
            const SizedBox(height: 16),
            _PolicyStatusStrip(
              hasActive: true,
              onTap: () => _openDetail(trip),
            ),
            const SizedBox(height: 16),
          ],
          Row(
            children: [
              _CounterTile(
                icon: Icons.schedule,
                label: 'En attente',
                count: pendingSubs.length,
                tint: const Color(0xFFF1EBFA),
                iconColor: AppColors.secondary,
                onTap: () => _openFiltered(SubscriptionsFilter.pending),
              ),
              _CounterTile(
                icon: Icons.cancel_outlined,
                label: 'Expirées',
                count: _subs.where((s) => s.isExpired).length,
                tint: const Color(0xFFFDECEE),
                iconColor: AppColors.danger,
                onTap: () => _openFiltered(SubscriptionsFilter.expired),
              ),
              _CounterTile(
                icon: Icons.description_outlined,
                label: 'Attestations',
                count: _attestationsCount,
                tint: const Color(0xFFEAF4FB),
                iconColor: const Color(0xFF2E86C8),
                onTap: () => context.push('/attestations'),
              ),
            ],
          ),
          const SizedBox(height: 22),
          if (trip != null)
            _TripSummary(sub: trip, onTap: () => _openDetail(trip))
          else
            _CoverageEmpty(
              holderName: context.watch<AuthProvider>().currentUser?.displayName ?? '',
              photoBytes: _photos.values.isNotEmpty ? _photos.values.first : null,
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

/// Bandeau statut police du kit : vert « Police d'assurance active » ou
/// rouge « Aucune police d'assurance active ».
class _PolicyStatusStrip extends StatelessWidget {
  const _PolicyStatusStrip({required this.hasActive, this.onTap});

  final bool hasActive;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final color = hasActive ? const Color(0xFF0E9F7E) : AppColors.danger;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: hasActive ? const Color(0xFFEAFAF4) : const Color(0xFFFDF0F1),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(
              hasActive ? Icons.check_circle : Icons.cancel,
              color: color,
              size: 26,
            ),
            const SizedBox(width: 10),
            Container(width: 1, height: 30, color: const Color(0xFFDCD4E9)),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    hasActive
                        ? 'Police d\u2019assurance active'
                        : 'Aucune police d\u2019assurance active',
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: AppColors.secondary,
                    ),
                  ),
                  Text(
                    hasActive
                        ? 'Vos couvertures sont en cours de validité.'
                        : 'Souscrivez dès maintenant pour bénéficier de nos services.',
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.mutedText,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.secondary),
          ],
        ),
      ),
    );
  }
}

/// Tuile compteur du kit (icône colorée + libellé + compteur + chevron).
class _CounterTile extends StatelessWidget {
  const _CounterTile({
    required this.icon,
    required this.label,
    required this.count,
    required this.tint,
    required this.iconColor,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final int count;
  final Color tint;
  final Color iconColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 3),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(14),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 14),
            decoration: BoxDecoration(
              color: tint,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, color: iconColor, size: 24),
                const SizedBox(height: 8),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: iconColor,
                  ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '$count',
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        color: AppColors.secondary,
                      ),
                    ),
                    const Icon(Icons.chevron_right,
                        size: 18, color: AppColors.secondary),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CoverageEmpty extends StatelessWidget {
  const _CoverageEmpty({required this.holderName, this.photoBytes});

  final String holderName;
  final Uint8List? photoBytes;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Pas de couverture',
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            color: AppColors.secondary,
          ),
        ),
        const SizedBox(height: 10),
        // Carte du bénéficiaire même sans police (pas de validité ni de numéro).
        MhEcard(
          holderName: holderName.isNotEmpty ? holderName : 'Assuré MHC',
          policyNumber: null,
          validityLabel: null,
          photoBytes: photoBytes,
        ),
        const SizedBox(height: 10),
        MHSurfaceCard(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: const BoxDecoration(
                      color: Color(0xFFEDE9FE),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.add_moderator,
                      color: AppColors.secondary,
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Vous n\u2019avez pas encore de couverture active.',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: AppColors.secondary,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Souscrivez à une assurance adaptée à vos besoins '
                          'et profitez de nos services partout dans le monde.',
                          style: TextStyle(
                            fontSize: 12,
                            color: AppColors.mutedText,
                            height: 1.45,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Container(
                width: double.infinity,
                height: 50,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.brandPurple, AppColors.brandTeal],
                  ),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: () => context.push('/subscription/new'),
                    borderRadius: BorderRadius.circular(10),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          'Découvrir nos assurances',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        SizedBox(width: 8),
                        Icon(Icons.arrow_forward,
                            color: Colors.white, size: 18),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// « Votre voyage » : résumé du voyage couvert (destination, dates,
/// voyageurs) — un appui ouvre le « Détail de la souscription ».
class _TripSummary extends StatelessWidget {
  const _TripSummary({required this.sub, required this.onTap});

  final SubscriptionModel sub;
  final VoidCallback onTap;

  String _fmt(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  @override
  Widget build(BuildContext context) {
    final v = sub.projetVoyage;
    final dest = v?.destinationDisplay ??
        [v?.destination, v?.destinationCountryName]
            .where((s) => s != null && s.isNotEmpty)
            .join(', ');
    final days = v?.dateRetour != null
        ? v!.dateRetour!.difference(v.dateDepart).inDays + 1
        : null;
    final minors = v?.mineurs.length ?? 0;
    final participants = v?.nombreParticipants ?? 1;
    final adults = participants - minors;
    final personsLabel = [
      if (adults > 0) '$adults adulte${adults > 1 ? 's' : ''}',
      if (minors > 0) '$minors mineur${minors > 1 ? 's' : ''}',
    ].join(' + ');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Votre voyage',
          style: TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            color: AppColors.secondary,
          ),
        ),
        const SizedBox(height: 10),
        Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: onTap,
            child: MHSurfaceCard(
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                children: [
                  const Icon(Icons.flight_takeoff,
                      color: AppColors.secondary, size: 22),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          dest.isNotEmpty ? dest : 'Voyage en cours',
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: AppColors.secondary,
                          ),
                        ),
                        if (v != null)
                          Text(
                            'Du ${_fmt(v.dateDepart)}'
                            '${v.dateRetour != null ? ' au ${_fmt(v.dateRetour!)}' : ''}'
                            '${days != null ? ' • $days jours' : ''}',
                            style: const TextStyle(
                                fontSize: 12, color: AppColors.mutedText),
                          ),
                        Text(
                          '$participants personne${participants > 1 ? 's' : ''}'
                          '${personsLabel.isNotEmpty ? ' ($personsLabel)' : ''}',
                          style: const TextStyle(
                              fontSize: 12, color: AppColors.mutedText),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: AppColors.secondary),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
