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
  final AttestationsService _attestationsService = AttestationsService();

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
        cards.add(_CardEntry(
          subscription: sub,
          holderName: ecard?['holder_name']?.toString() ?? '',
          policyNumber: ecard?['numero_souscription']?.toString() ??
              (sub.numeroSouscription.isNotEmpty ? sub.numeroSouscription : null),
          validity: _formatValidity(ecard),
          isChild: false,
          photoBytes: photo,
        ));
        for (final childName in _minorNames(sub)) {
          cards.add(_CardEntry(
            subscription: sub,
            holderName: childName,
            policyNumber: sub.numeroSouscription.isNotEmpty
                ? sub.numeroSouscription
                : null,
            validity: _formatValidity(ecard),
            isChild: true,
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
          _error = e.toString().replaceFirst('Exception: ', '');
          _loading = false;
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
      final attestations =
          await _attestationsService.getSubscriptionAttestations(entry.subscription.id);
      if (attestations.isEmpty) {
        throw Exception('Aucune attestation disponible pour cette police.');
      }
      final att = attestations.first;
      final id = att['id'] as int?;
      if (id == null) throw Exception('Attestation invalide.');
      final path = await _attestationsService.downloadEcard(
        id,
        numeroAttestation: att['numero_attestation']?.toString(),
      );
      if (!mounted) return;
      await OpenFilex.open(path);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(e.toString().replaceFirst('Exception: ', '')),
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
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
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
  final Uint8List? photoBytes;

  _CardEntry({
    required this.subscription,
    required this.holderName,
    this.policyNumber,
    this.validity,
    required this.isChild,
    this.photoBytes,
  });
}
