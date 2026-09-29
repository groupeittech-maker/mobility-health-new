import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../core/widgets/mh_text_highlight.dart';
import '../../models/medecin_conseil.dart';
import '../../services/medecin_conseil_service.dart';
import '../../core/utils/api_error_helper.dart';

/// Onglet « Téléconsultation » du kit MyMHC : médecins conseils groupés par
/// ville/destination, « Voir les informations » et « Lancer une téléconsultation ».
class TeleconsultationScreen extends StatefulWidget {
  const TeleconsultationScreen({super.key});

  @override
  State<TeleconsultationScreen> createState() => _TeleconsultationScreenState();
}

class _TeleconsultationScreenState extends State<TeleconsultationScreen> {
  final MedecinConseilService _service = MedecinConseilService();
  List<MedecinConseilAssignment> _assignments = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final cached = await _service.loadCached();
    if (mounted && cached.isNotEmpty) {
      setState(() {
        _assignments = cached;
        _loading = false;
      });
    }
    try {
      final fresh = await _service.refresh();
      if (mounted) {
        setState(() {
          _assignments = fresh;
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

  void _showInfos(MedecinConseilContact c, String ville) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              c.nom ?? 'Médecin conseil',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppColors.secondary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Médecin conseil — $ville',
              style: const TextStyle(fontSize: 13, color: AppColors.mutedText),
            ),
            const Divider(height: 28),
            if (c.telephone != null && c.telephone!.isNotEmpty)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.phone_outlined, color: AppColors.brandTeal),
                title: Text(c.telephone!),
                onTap: () => _call(c.telephone),
              ),
            if (c.email != null && c.email!.isNotEmpty)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.mail_outline, color: AppColors.brandTeal),
                title: Text(c.email!),
                onTap: () async {
                  final uri = Uri(scheme: 'mailto', path: c.email);
                  if (await canLaunchUrl(uri)) await launchUrl(uri);
                },
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;

    return ColoredBox(
      color: kMhContentBackground,
      child: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: EdgeInsets.fromLTRB(20, 16, 20, bottomPadding),
          children: [
            const MHSectionTitle(
              title: 'Téléconsultation',
              subtitle: 'Des médecins conseils à votre écoute.',
            ),
            const SizedBox(height: 20),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null && _assignments.isEmpty)
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
            else if (_assignments.where((a) => a.medecinConseil != null).isEmpty)
              MHSurfaceCard(
                padding: const EdgeInsets.all(20),
                child: Text(
                  'Aucun médecin conseil n’est encore affecté à vos souscriptions. '
                  'Le médecin conseil est attribué selon la destination de votre police.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: AppColors.mutedText,
                    height: 1.5,
                  ),
                ),
              )
            else
              ..._assignments
                  .where((a) => a.medecinConseil != null)
                  .map((a) {
                final ville = a.destinationLabel;
                final doc = a.medecinConseil;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: MHSurfaceCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.location_on,
                                color: AppColors.secondary, size: 18),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                ville,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.secondary,
                                  fontSize: 14,
                                ),
                              ),
                            ),
                            if (a.numeroSouscription != null)
                              Text(
                                'Police ${a.numeroSouscription}',
                                style: const TextStyle(
                                  fontSize: 10,
                                  color: AppColors.mutedText,
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            const CircleAvatar(
                              radius: 26,
                              backgroundColor: Color(0xFFEDE9FE),
                              child: Icon(Icons.person,
                                  color: AppColors.secondary, size: 28),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    doc?.nom ?? 'Médecin conseil MHC',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      color: AppColors.secondary,
                                      fontSize: 15,
                                    ),
                                  ),
                                  const Text(
                                    'Médecin conseil — Médecine générale',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: AppColors.mutedText,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  const Row(
                                    children: [
                                      Icon(Icons.circle,
                                          size: 9, color: Color(0xFF10B981)),
                                      SizedBox(width: 5),
                                      Text(
                                        'Disponible pour téléconsultation',
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: Color(0xFF0F766E),
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton.icon(
                                onPressed: doc == null
                                    ? null
                                    : () => _showInfos(doc, ville),
                                icon: const Icon(Icons.info_outline, size: 18),
                                label: const Text('Voir les informations',
                                    style: TextStyle(fontSize: 12)),
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: AppColors.secondary,
                                  side: const BorderSide(
                                      color: Color(0xFFD6CBE2)),
                                  padding: const EdgeInsets.symmetric(
                                      vertical: 12),
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: _GradientActionButton(
                                label: 'Lancer une téléconsultation',
                                icon: Icons.videocam_outlined,
                                onPressed: doc?.telephone == null
                                    ? null
                                    : () => _call(doc!.telephone),
                              ),
                            ),
                          ],
                        ),
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

class _GradientActionButton extends StatelessWidget {
  const _GradientActionButton({
    required this.label,
    required this.icon,
    this.onPressed,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: onPressed == null ? 0.5 : 1,
      child: Container(
        decoration: BoxDecoration(
          gradient: AppTheme.accentGradient,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onPressed,
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, color: Colors.white, size: 18),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      label,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                      maxLines: 2,
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
