import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../../core/constants/mh_layout.dart';
import '../../core/constants/app_colors.dart';
import '../../models/medecin_conseil.dart';
import '../../services/api_services.dart';
import '../../services/medecin_conseil_service.dart';
import '../../services/sos_eligibility_service.dart';
import '../../widgets/medecin_conseil_card.dart';

/// Retourne un message d'erreur lisible à partir d'une exception (Dio 400/404/500 ou autre).
String _messageFromError(dynamic e) {
  if (e is DioException) {
    final statusCode = e.response?.statusCode;
    final data = e.response?.data;
    String? detail;
    if (data is Map<String, dynamic> && data['detail'] != null) {
      final d = data['detail'];
      detail = d is String ? d : d.toString();
    }
    if (detail != null && detail.isNotEmpty) return detail;
    if (statusCode == 400) return 'Requête invalide. Vérifiez vos données.';
    if (statusCode == 401) return 'Session expirée. Reconnectez-vous.';
    if (statusCode == 403) return 'Accès refusé.';
    if (statusCode == 404) return 'Ressource introuvable.';
    if (statusCode != null && statusCode >= 500) return 'Erreur serveur. Réessayez plus tard.';
  }
  final s = e.toString().replaceFirst(RegExp(r'^Exception:\s*'), '');
  if (s.length > 120) return '${s.substring(0, 120)}…';
  return s;
}

/// Alertes SOS – bouton rouge pour déclencher une alerte (connecté POST /sos/trigger), liste des alertes (GET /sos/).
class SosScreen extends StatefulWidget {
  const SosScreen({super.key});

  @override
  State<SosScreen> createState() => _SosScreenState();
}

class _SosScreenState extends State<SosScreen> {
  final SosService _sosService = SosService();
  final MedecinConseilService _medecinConseilService = MedecinConseilService();
  List<Map<String, dynamic>> _alertes = [];
  List<MedecinConseilAssignment> _medecinConseil = [];
  bool _medecinConseilFromCache = false;
  bool _loadingAlertes = true;
  bool _sending = false;
  String? _error;
  bool _checkingEligibility = true;
  bool _canTriggerSos = false;

  @override
  void initState() {
    super.initState();
    final peek = SosService.peekSosAlertesCache();
    if (peek != null) {
      _alertes = peek;
      _loadingAlertes = false;
    }
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    await Future.wait([
      _loadEligibility(),
      _loadAlertes(),
      _loadMedecinConseil(),
    ]);
  }

  Future<void> _loadMedecinConseil() async {
    final cached = await _medecinConseilService.loadCached();
    if (mounted && cached.isNotEmpty) {
      setState(() {
        _medecinConseil = cached;
        _medecinConseilFromCache = true;
      });
    }
    try {
      final fresh = await _medecinConseilService.refresh();
      if (mounted) {
        setState(() {
          _medecinConseil = fresh;
          _medecinConseilFromCache = false;
        });
      }
    } catch (_) {
      // Hors ligne : on conserve le cache local déjà affiché.
    }
  }

  Future<void> _loadEligibility() async {
    try {
      final ok = await SosEligibilityService.canTriggerSos();
      if (mounted) {
        setState(() {
          _canTriggerSos = ok;
          _checkingEligibility = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _canTriggerSos = false;
          _checkingEligibility = false;
        });
      }
    }
  }

  Future<void> _loadAlertes({bool forceRefresh = false}) async {
    final hadData = _alertes.isNotEmpty && !forceRefresh;
    if (mounted) {
      setState(() {
        if (!hadData) _loadingAlertes = true;
        _error = null;
      });
    }
    try {
      final list = await _sosService.getAlertes(forceRefresh: forceRefresh);
      if (mounted) {
        setState(() {
          _alertes = list;
          _loadingAlertes = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = _messageFromError(e);
          _loadingAlertes = false;
        });
      }
    }
  }

  Future<void> _onDeclareSos() async {
    if (_sending || !mounted) return;
    if (_checkingEligibility || !_canTriggerSos) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Une attestation définitive est nécessaire pour déclencher une alerte SOS (après validation production).',
          ),
          backgroundColor: AppColors.danger,
          duration: Duration(seconds: 5),
        ),
      );
      return;
    }

    setState(() => _sending = true);
    try {
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled && mounted) {
        setState(() => _sending = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Activez la localisation dans les paramètres du téléphone.'),
            backgroundColor: AppColors.danger,
          ),
        );
        return;
      }
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        if (mounted) {
          setState(() => _sending = false);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Autorisez l\'accès à la position pour envoyer l\'alerte SOS.'),
              backgroundColor: AppColors.danger,
            ),
          );
        }
        return;
      }
      Position? position;
      try {
        position = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.medium,
        );
      } catch (_) {
        position = null;
      }

      if (position == null && mounted) {
        setState(() => _sending = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Impossible d\'obtenir la position. Vérifiez les autorisations.'),
            backgroundColor: AppColors.danger,
          ),
        );
        return;
      }

      await _sosService.triggerSos(
        latitude: position!.latitude,
        longitude: position.longitude,
        description: null,
        priorite: 'normale',
      );

      if (!mounted) return;
      setState(() => _sending = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Alerte SOS envoyée. Vous serez pris en charge.'),
          backgroundColor: AppColors.success,
        ),
      );
      _loadAlertes(forceRefresh: true);
    } catch (e) {
      if (mounted) {
        setState(() => _sending = false);
        final message = _messageFromError(e);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: AppColors.danger,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    final enabled = !_checkingEligibility && _canTriggerSos;
    final gradientColors = _checkingEligibility
        ? [const Color(0xFF94A3B8), const Color(0xFF64748B)]
        : enabled
            ? [AppColors.danger, AppColors.danger.withValues(alpha: 0.85)]
            : [const Color(0xFF94A3B8), const Color(0xFF64748B)];

    return ColoredBox(
      color: kMhContentBackground,
      child: ListView(
        padding: EdgeInsets.fromLTRB(16, 16, 16, bottomPadding),
        children: [
          const SizedBox(height: 16),
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: (_sending || _checkingEligibility) ? null : _onDeclareSos,
              borderRadius: BorderRadius.circular(16),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 24),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: gradientColors,
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: (enabled ? AppColors.danger : const Color(0xFF64748B))
                          .withValues(alpha: enabled ? 0.4 : 0.15),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: _sending
                    ? const Center(
                        child: SizedBox(
                          width: 28,
                          height: 28,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        ),
                      )
                    : _checkingEligibility
                        ? Column(
                            children: [
                              const SizedBox(
                                width: 36,
                                height: 36,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'Vérification de votre couverture…',
                                style: theme.textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w600,
                                  color: Colors.white,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          )
                        : Column(
                            children: [
                              Icon(Icons.emergency, size: 56, color: Colors.white),
                              const SizedBox(height: 12),
                              Text(
                                enabled
                                    ? 'Déclarer une alerte SOS'
                                    : 'SOS non disponible',
                                style: theme.textTheme.titleLarge?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                enabled
                                    ? 'En cas d\'urgence médicale, appuyez sur ce bouton pour déclencher une alerte et vous serez pris en charge rapidement.'
                                    : 'Une attestation définitive est requise (après validation production de votre dossier). Vous pouvez consulter l’état de vos attestations dans le tableau de bord.',
                                style: theme.textTheme.bodySmall?.copyWith(color: Colors.white70),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
              ),
            ),
          ),
          const SizedBox(height: 24),
          MedecinConseilCard(
            assignments: _medecinConseil,
            fromCache: _medecinConseilFromCache,
          ),
          const SizedBox(height: 24),
          Text(
            'Mes alertes',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
              color: const Color(0xFF1E293B),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.danger.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _error!,
                    style: const TextStyle(color: AppColors.danger, fontSize: 13),
                  ),
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: _loadingAlertes ? null : () => _loadAlertes(forceRefresh: true),
                    icon: const Icon(Icons.refresh, size: 18),
                    label: const Text('Réessayer'),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 8),
          _loadingAlertes
              ? const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: CircularProgressIndicator()),
                )
              : _alertes.isEmpty
                  ? Padding(
                      padding: const EdgeInsets.all(16),
                      child: Text(
                        'Aucune alerte pour le moment.',
                        style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.mutedText),
                      ),
                    )
                  : ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: _alertes.length,
                      itemBuilder: (context, i) {
                        final a = _alertes[i];
                        final numero = a['numero_alerte'] ?? 'Alerte #${a['id']}';
                        final statut = (a['statut'] ?? '').toString();
                        final created = a['created_at']?.toString();
                        return Card(
                          margin: const EdgeInsets.only(bottom: 12),
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: AppColors.danger.withValues(alpha: 0.2),
                              child: const Icon(Icons.emergency, color: AppColors.danger, size: 24),
                            ),
                            title: Text(numero),
                            subtitle: Text('$statut${created != null ? ' • $created' : ''}'),
                          ),
                        );
                      },
                    ),
        ],
      ),
    );
  }
}
