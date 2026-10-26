import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/destination.dart';
import '../../services/api_services.dart';
import '../../core/utils/api_error_helper.dart';

/// « Notre réseau » (kit) : pays du réseau MHC avec rappel explicite que la
/// couverture de la police dépend de sa zone et de ses conditions.
class ReseauMhcScreen extends StatefulWidget {
  const ReseauMhcScreen({super.key});

  @override
  State<ReseauMhcScreen> createState() => _ReseauMhcScreenState();
}

class _ReseauMhcScreenState extends State<ReseauMhcScreen> {
  final DestinationsService _service = DestinationsService();
  List<DestinationCountryModel> _countries = const [];
  bool _loading = true;
  String? _error;
  String _query = '';

  /// Regroupement indicatif par grande zone (le pays reste soumis à la police).
  static const _zoneByCode = <String, String>{
    'CG': 'Afrique', 'CD': 'Afrique', 'CM': 'Afrique', 'GA': 'Afrique',
    'CI': 'Afrique', 'SN': 'Afrique', 'BJ': 'Afrique', 'TG': 'Afrique',
    'BF': 'Afrique', 'ML': 'Afrique', 'NE': 'Afrique', 'GN': 'Afrique',
    'MA': 'Maghreb', 'DZ': 'Maghreb', 'TN': 'Maghreb', 'MR': 'Maghreb',
    'LY': 'Maghreb', 'EG': 'Maghreb',
    'FR': 'Europe', 'BE': 'Europe', 'CH': 'Europe', 'DE': 'Europe',
    'ES': 'Europe', 'IT': 'Europe', 'PT': 'Europe', 'GB': 'Europe',
    'NL': 'Europe', 'TR': 'Europe',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _error = null;
      if (_countries.isEmpty) _loading = true;
    });
    try {
      final list = await _service.getDestinationCountries();
      list.sort((a, b) => a.nom.compareTo(b.nom));
      if (mounted) {
        setState(() {
          _countries = list;
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

  Map<String, List<DestinationCountryModel>> get _grouped {
    final filtered = _countries.where((c) {
      if (_query.trim().isEmpty) return true;
      return c.nom.toLowerCase().contains(_query.trim().toLowerCase());
    });
    final map = <String, List<DestinationCountryModel>>{};
    for (final c in filtered) {
      final zone = _zoneByCode[c.code.toUpperCase()] ?? 'Autres pays';
      map.putIfAbsent(zone, () => []).add(c);
    }
    final order = ['Afrique', 'Maghreb', 'Europe', 'Autres pays'];
    final keys = map.keys.toList()
      ..sort((a, b) => order.indexOf(a).compareTo(order.indexOf(b)));
    return {for (final k in keys) k: map[k]!};
  }

  /// Fiche pays : carte visuelle du pays avec les villes couvertes par le
  /// réseau MHC mises en évidence.
  void _showCountryDetails(DestinationCountryModel c) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _CountryDetailSheet(country: c),
    );
  }

  @override
  Widget build(BuildContext context) {
    final groups = _grouped;
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Notre réseau'),
      body: _loading
          ? const MhLoadingView()
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
                children: [
                  MHSurfaceCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Réseau d’assistance MHC',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: AppColors.secondary,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Consultez les pays où MHC dispose d’un réseau de prise en charge.',
                          style: TextStyle(fontSize: 12, color: AppColors.mutedText, height: 1.4),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          onChanged: (v) => setState(() => _query = v),
                          decoration: MHSurfaceCard.input(
                            labelText: 'Rechercher un pays',
                            prefixIcon: const Icon(Icons.search, size: 20),
                            isDense: true,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  if (_error != null && _countries.isEmpty)
                    MHSurfaceCard(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        children: [
                          Text(_error!,
                              style: const TextStyle(color: AppColors.danger, fontSize: 13)),
                          TextButton.icon(
                            onPressed: _load,
                            icon: const Icon(Icons.refresh, size: 18),
                            label: const Text('Réessayer'),
                          ),
                        ],
                      ),
                    )
                  else
                    ...groups.entries.map(
                      (e) => MHSurfaceCard(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              e.key,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                color: AppColors.brandTeal,
                                fontSize: 12,
                                letterSpacing: 0.6,
                              ),
                            ),
                            const Divider(height: 16),
                            ...e.value.map(
                              (c) => InkWell(
                                borderRadius: BorderRadius.circular(8),
                                onTap: () => _showCountryDetails(c),
                                child: Padding(
                                  padding:
                                      const EdgeInsets.symmetric(vertical: 6),
                                  child: Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          c.nom,
                                          style: const TextStyle(
                                            fontSize: 13,
                                            color: Color(0xFF352A42),
                                          ),
                                        ),
                                      ),
                                      Text(
                                        c.villes.isEmpty
                                            ? c.code
                                            : '${c.villes.length} ville${c.villes.length > 1 ? 's' : ''}',
                                        style: const TextStyle(
                                          fontSize: 11,
                                          color: AppColors.mutedText,
                                        ),
                                      ),
                                      const SizedBox(width: 6),
                                      const Icon(
                                        Icons.chevron_right,
                                        size: 18,
                                        color: AppColors.secondary,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEAFAF7),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFD7F1EC)),
                    ),
                    child: const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Votre couverture personnelle',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: AppColors.secondary,
                            fontSize: 13,
                          ),
                        ),
                        SizedBox(height: 6),
                        Text(
                          'La présence d’un pays dans le réseau MHC ne signifie pas que votre police le couvre. '
                          'Vérifiez la zone souscrite, les pays exclus et les conditions de votre contrat.',
                          style: TextStyle(fontSize: 11, color: AppColors.mutedText, height: 1.45),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

/// Fiche pays du réseau MHC : en-tête « carte » violet/teal avec repère et
/// liste des villes couvertes en surbrillance.
class _CountryDetailSheet extends StatelessWidget {
  const _CountryDetailSheet({required this.country});

  final DestinationCountryModel country;

  @override
  Widget build(BuildContext context) {
    final villes = country.villes;
    return DraggableScrollableSheet(
      initialChildSize: 0.6,
      minChildSize: 0.4,
      maxChildSize: 0.9,
      builder: (_, controller) {
        return Material(
          color: Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          clipBehavior: Clip.antiAlias,
          child: ListView(
            controller: controller,
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
            children: [
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE2E8F0),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              // « Carte » stylisée du pays : dégradé charte + repère central.
              Container(
                height: 150,
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Color(0xFF4E267C), Color(0xFF14AE98)],
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Stack(
                  children: [
                    Positioned.fill(
                      child: CustomPaint(painter: _GridPainter()),
                    ),
                    Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.location_on,
                            color: Colors.white,
                            size: 42,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            country.nom,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            '${villes.length} ville${villes.length > 1 ? 's' : ''} couverte${villes.length > 1 ? 's' : ''}',
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Villes couvertes',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: AppColors.secondary,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 10),
              if (villes.isEmpty)
                const Text(
                  'Aucune ville référencée pour ce pays.',
                  style: TextStyle(color: AppColors.mutedText, fontSize: 12),
                )
              else
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: villes
                      .map(
                        (v) => Chip(
                          avatar: const Icon(
                            Icons.location_on,
                            size: 16,
                            color: AppColors.brandTeal,
                          ),
                          label: Text(
                            v.nom,
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: AppColors.secondary,
                            ),
                          ),
                          backgroundColor: const Color(0xFFEDE9FE),
                          side: const BorderSide(color: Color(0xFFD8CCED)),
                        ),
                      )
                      .toList(),
                ),
              const SizedBox(height: 16),
              const Text(
                'La présence d’une ville dans le réseau MHC ne garantit pas sa '
                'couverture par votre police : vérifiez la zone et les '
                'conditions de votre contrat.',
                style: TextStyle(
                  fontSize: 11,
                  color: AppColors.mutedText,
                  height: 1.4,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

/// Quadrillage discret pour l'en-tête « carte ».
class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.08)
      ..strokeWidth = 1;
    const step = 28.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
