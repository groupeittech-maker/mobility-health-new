import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../../core/constants/app_colors.dart';
import '../../services/api_services.dart';

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
  List<Map<String, dynamic>> _alertes = [];
  bool _loadingAlertes = true;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadAlertes();
  }

  Future<void> _loadAlertes() async {
    setState(() {
      _loadingAlertes = true;
      _error = null;
    });
    try {
      final list = await _sosService.getAlertes();
      if (mounted) setState(() {
        _alertes = list;
        _loadingAlertes = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = _messageFromError(e);
        _loadingAlertes = false;
      });
    }
  }

  Future<void> _onDeclareSos() async {
    if (_sending || !mounted) return;

    setState(() => _sending = true);
    try {
      // Activer / demander la géolocalisation avant d'envoyer l'alerte
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
      _loadAlertes();
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
    return Container(
      color: const Color(0xFFE8F0F4),
      child: ListView(
        padding: EdgeInsets.fromLTRB(16, 16, 16, bottomPadding),
        children: [
          const SizedBox(height: 16),
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: _sending ? null : _onDeclareSos,
              borderRadius: BorderRadius.circular(16),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 24),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      AppColors.danger,
                      AppColors.danger.withValues(alpha: 0.85),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.danger.withValues(alpha: 0.4),
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
                    : Column(
                        children: [
                          Icon(Icons.emergency, size: 56, color: Colors.white),
                          const SizedBox(height: 12),
                          Text(
                            'Déclarer une alerte SOS',
                            style: theme.textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'En cas d\'urgence, créez une alerte pour être pris en charge.',
                            style: theme.textTheme.bodySmall?.copyWith(color: Colors.white70),
                            textAlign: TextAlign.center,
                          ),
                        ],
                      ),
              ),
            ),
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
                    onPressed: _loadingAlertes ? null : _loadAlertes,
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
