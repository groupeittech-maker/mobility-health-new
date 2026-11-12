import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:open_filex/open_filex.dart';

import '../../core/constants/app_colors.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_ecard.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/subscription.dart';
import '../../services/api_services.dart';
import '../../core/utils/api_error_helper.dart';

/// « Ma carte d'assurance » (kit) : une e-carte par assuré — adulte en violet,
/// chaque mineur rattaché en turquoise — avec identité et téléchargement.
class EcardsScreen extends StatefulWidget {
  const EcardsScreen({super.key});

  @override
  State<EcardsScreen> createState() => _EcardsScreenState();
}

class _EcardsScreenState extends State<EcardsScreen> {
  final SubscriptionsService _subsService = SubscriptionsService();
  final EcardsService _ecardsService = EcardsService();

  bool _loading = true;
  String? _error;
  List<_CardEntry> _cards = [];
  int _currentIndex = 0;
  bool _downloading = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _error = null;
      _loading = true;
    });
    try {
      final subs = await _subsService.getSubscriptions(limit: 200);
      final active = subs.where((s) => s.isActive).toList();
      final cards = <_CardEntry>[];
      for (final sub in active) {
        Map<String, dynamic>? ecard;
        Uint8List? photo;
        try {
          ecard = await _ecardsService.getEcard(sub.id);
        } catch (_) {}
        try {
          final bytes = await _ecardsService.getUserPhoto(sub.id);
          if (bytes != null) photo = Uint8List.fromList(bytes);
        } catch (_) {}
        final policyNumber = ecard?['numero_souscription']?.toString() ??
            (sub.numeroSouscription.isNotEmpty
                ? sub.numeroSouscription
                : null);
        final validity = _formatValidity(sub, ecard);
        List<Map<String, dynamic>> members = const [];
        try {
          members = await _ecardsService.getMembers(sub.id);
        } catch (_) {}
        if (members.isNotEmpty) {
          for (final m in members) {
            final idx = (m['index'] as num?)?.toInt() ?? 0;
            final isChild = m['role'] == 'child';
            Uint8List? memberPhoto = idx == 0 ? photo : null;
            if (isChild) {
              try {
                final b = await _ecardsService.getMemberPhoto(sub.id, idx);
                if (b != null) memberPhoto = Uint8List.fromList(b);
              } catch (_) {}
            }
            cards.add(_CardEntry(
              subscription: sub,
              holderName: m['name']?.toString() ??
                  ecard?['holder_name']?.toString() ??
                  '',
              policyNumber: policyNumber,
              validity: validity,
              isChild: isChild,
              memberIndex: idx,
              photoBytes: memberPhoto,
            ));
          }
          continue;
        }
        cards.add(_CardEntry(
          subscription: sub,
          holderName: ecard?['holder_name']?.toString() ?? '',
          policyNumber: policyNumber,
          validity: validity,
          isChild: false,
          photoBytes: photo,
        ));
        var childIndex = 0;
        for (final childName in _minorNames(sub)) {
          childIndex++;
          cards.add(_CardEntry(
            subscription: sub,
            holderName: childName,
            policyNumber: policyNumber,
            validity: validity,
            isChild: true,
            memberIndex: childIndex,
          ));
        }
      }
      if (mounted) {
        setState(() {
          _cards = cards;
          _loading = false;
          _currentIndex = 0;
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

  /// « Du … au … » comme sur l'attestation : début = date d'effet de la
  /// souscription, fin = fin de couverture de l'e-carte.
  String? _formatValidity(SubscriptionModel sub, Map<String, dynamic>? ecard) {
    final raw = ecard?['coverage_end_date']?.toString() ??
        ecard?['card_expires_at']?.toString();
    final end = (raw != null ? DateTime.tryParse(raw) : null) ?? sub.dateFin;
    return MhEcard.validityRange(sub.dateDebut, end);
  }

  /// Noms des mineurs rattachés : champ structuré `projet.mineurs`, sinon
  /// rétro-compatibilité avec les notes (« Mineurs accompagnés: … »).
  List<String> _minorNames(SubscriptionModel sub) {
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

  Future<void> _download() async {
    if (_downloading || _currentIndex >= _cards.length) return;
    final entry = _cards[_currentIndex];
    setState(() => _downloading = true);
    try {
      // Chaque membre télécharge SA carte : l'endpoint génère l'e-carte de
      // l'enfant demandé (nom + photo de l'enfant), pas celle du parent.
      final numero = entry.policyNumber ??
          entry.subscription.numeroSouscription;
      final path = await _ecardsService.downloadMemberCard(
        entry.subscription.id,
        entry.memberIndex,
        fileName:
            'ecarte-${numero.isNotEmpty ? numero : entry.subscription.id}-${entry.holderName.isNotEmpty ? entry.holderName : 'assure'}.png',
      );
      if (!mounted) return;
      await OpenFilex.open(path);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(apiErrorToUserMessage(e)),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _downloading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final entry = _currentIndex < _cards.length ? _cards[_currentIndex] : null;
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: MhAppBar(
        title: entry?.isChild == true ? 'Carte de l’enfant' : 'Ma carte d’assurance',
      ),
      body: _loading
          ? const MhLoadingView()
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_error!,
                            style: const TextStyle(color: AppColors.danger)),
                        const SizedBox(height: 12),
                        TextButton.icon(
                          onPressed: _load,
                          icon: const Icon(Icons.refresh, size: 18),
                          label: const Text('Réessayer'),
                        ),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: EdgeInsets.fromLTRB(20, 12, 20, 32 + MediaQuery.of(context).padding.bottom),
                    children: [
                      if (_cards.isEmpty)
                        MhEcardEmpty(
                          onSubscribe: () =>
                              context.push('/subscription/new'),
                        )
                      else ...[
                        SizedBox(
                          height: 176,
                          child: PageView.builder(
                            itemCount: _cards.length,
                            onPageChanged: (i) =>
                                setState(() => _currentIndex = i),
                            itemBuilder: (_, i) {
                              final c = _cards[i];
                              return Padding(
                                padding:
                                    const EdgeInsets.symmetric(horizontal: 4),
                                child: MhEcard(
                                  holderName: c.holderName.isNotEmpty
                                      ? c.holderName
                                      : 'Assuré MHC',
                                  policyNumber: c.policyNumber,
                                  validityLabel: c.validity,
                                  isChild: c.isChild,
                                  photoBytes: c.photoBytes,
                                ),
                              );
                            },
                          ),
                        ),
                        if (_cards.length > 1)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: List.generate(
                                _cards.length,
                                (i) => Container(
                                  width: 8,
                                  height: 8,
                                  margin:
                                      const EdgeInsets.symmetric(horizontal: 3),
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: i == _currentIndex
                                        ? AppColors.brandTeal
                                        : const Color(0xFFDDD4E9),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        const SizedBox(height: 8),
                        MHSurfaceCard(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Identité',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.secondary,
                                  fontSize: 13,
                                ),
                              ),
                              const Divider(height: 18),
                              _row('Nom', entry?.holderName ?? '—'),
                              _row(
                                'Statut',
                                entry?.isChild == true
                                    ? 'Mineur rattaché'
                                    : 'Assuré principal',
                              ),
                              _row(
                                'Produit',
                                entry?.subscription.produitAssurance?.nom ??
                                    '—',
                              ),
                              _row(
                                'Destination',
                                entry?.subscription.projetVoyage
                                        ?.destinationDisplay ??
                                    entry?.subscription.projetVoyage
                                        ?.destination ??
                                    '—',
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                        SizedBox(
                          height: 48,
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: _downloading ? null : _download,
                            style: FilledButton.styleFrom(
                              backgroundColor: AppColors.secondary,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),
                            child: _downloading
                                ? const SizedBox(
                                    width: 22,
                                    height: 22,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2, color: Colors.white),
                                  )
                                : const Text('Télécharger la carte'),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style:
                  const TextStyle(fontSize: 12, color: AppColors.mutedText)),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Color(0xFF332542),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CardEntry {
  final SubscriptionModel subscription;
  final String holderName;
  final String? policyNumber;
  final String? validity;
  final bool isChild;

  /// Index du membre assuré dans /ecard/members — le téléchargement demande
  /// la carte de CE membre (0 = principal/tiers, ≥1 = enfant voyageur).
  final int memberIndex;
  final Uint8List? photoBytes;

  _CardEntry({
    required this.subscription,
    required this.holderName,
    this.policyNumber,
    this.validity,
    required this.isChild,
    this.memberIndex = 0,
    this.photoBytes,
  });
}
