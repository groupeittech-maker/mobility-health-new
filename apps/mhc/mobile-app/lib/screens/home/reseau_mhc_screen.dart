import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/destination.dart';
import '../../services/api_services.dart';

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
          _error = e.toString().replaceFirst('Exception: ', '');
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
                              (c) => Padding(
                                padding: const EdgeInsets.symmetric(vertical: 6),
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
                                  ],
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
