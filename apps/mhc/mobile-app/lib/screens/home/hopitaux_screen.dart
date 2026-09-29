import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../core/widgets/mh_text_highlight.dart';
import '../../services/api_services.dart';
import '../../core/utils/api_error_helper.dart';

/// Onglet « Hôpitaux » du kit MyMHC : établissements partenaires groupés par
/// ville, adresse, téléphone avec bouton d'appel.
class HopitauxScreen extends StatefulWidget {
  const HopitauxScreen({super.key});

  @override
  State<HopitauxScreen> createState() => _HopitauxScreenState();
}

class _HopitauxScreenState extends State<HopitauxScreen> {
  final HospitalsService _service = HospitalsService();
  List<Map<String, dynamic>> _hospitals = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _error = null;
      if (_hospitals.isEmpty) _loading = true;
    });
    try {
      final list = await _service.getHospitals();
      if (mounted) {
        setState(() {
          _hospitals =
              list.where((h) => h['est_actif'] != false).toList();
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

  Future<void> _call(String? phone) async {
    if (phone == null || phone.trim().isEmpty) return;
    final uri = Uri(scheme: 'tel', path: phone.trim());
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  Map<String, List<Map<String, dynamic>>> get _byCity {
    final map = <String, List<Map<String, dynamic>>>{};
    for (final h in _hospitals) {
      final ville = (h['ville']?.toString().trim().isNotEmpty == true)
          ? h['ville'].toString().trim()
          : 'Autres';
      map.putIfAbsent(ville, () => []).add(h);
    }
    final keys = map.keys.toList()..sort();
    return {for (final k in keys) k: map[k]!};
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    final groups = _byCity;

    return ColoredBox(
      color: kMhContentBackground,
      child: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: EdgeInsets.fromLTRB(20, 16, 20, bottomPadding),
          children: [
            const MHSectionTitle(
              title: 'Hôpitaux',
              subtitle: 'Des établissements de santé de confiance près de vous.',
            ),
            const SizedBox(height: 20),
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
                      style: const TextStyle(color: AppColors.danger, fontSize: 13),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 12),
                    TextButton.icon(
                      onPressed: _load,
                      icon: const Icon(Icons.refresh, size: 18),
                      label: const Text('Réessayer'),
                    ),
                  ],
                ),
              )
            else if (_hospitals.isEmpty)
              MHSurfaceCard(
                padding: const EdgeInsets.all(20),
                child: Text(
                  'Aucun établissement partenaire n’est référencé pour le moment.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: AppColors.mutedText,
                    height: 1.5,
                  ),
                ),
              )
            else
              ...groups.entries.map((entry) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: MHSurfaceCard(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.location_on,
                                color: AppColors.secondary, size: 18),
                            const SizedBox(width: 6),
                            Text(
                              entry.key,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                color: AppColors.secondary,
                                fontSize: 15,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              '(${entry.value.length} établissement${entry.value.length > 1 ? 's' : ''})',
                              style: const TextStyle(
                                fontSize: 11,
                                color: AppColors.mutedText,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        ...entry.value.map((h) => _HospitalTile(
                              hospital: h,
                              onCall: () => _call(h['telephone']?.toString()),
                            )),
                      ],
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}

class _HospitalTile extends StatelessWidget {
  const _HospitalTile({required this.hospital, required this.onCall});

  final Map<String, dynamic> hospital;
  final VoidCallback onCall;

  @override
  Widget build(BuildContext context) {
    final nom = hospital['nom']?.toString() ?? 'Établissement';
    final adresse = [
      hospital['adresse']?.toString(),
      hospital['code_postal']?.toString(),
      hospital['ville']?.toString(),
      hospital['pays']?.toString(),
    ].where((s) => s != null && s.trim().isNotEmpty).join(', ');
    final phone = hospital['telephone']?.toString();

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF8F6FC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE8E2F0)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: const Color(0xFFEDE9FE),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.local_hospital,
                color: AppColors.secondary, size: 30),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  nom,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: AppColors.secondary,
                    fontSize: 14,
                  ),
                ),
                if (adresse.isNotEmpty) ...[
                  const SizedBox(height: 3),
                  Text(
                    adresse,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.mutedText,
                      height: 1.4,
                    ),
                  ),
                ],
                if (phone != null && phone.isNotEmpty) ...[
                  const SizedBox(height: 3),
                  Text(
                    phone,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.secondary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),
          ),
          IconButton(
            onPressed: (phone == null || phone.isEmpty) ? null : onCall,
            icon: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: AppColors.brandTeal.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.phone, color: AppColors.brandTeal, size: 20),
            ),
          ),
        ],
      ),
    );
  }
}
