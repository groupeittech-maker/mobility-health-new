import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants/app_colors.dart';
import '../core/widgets/mh_app_bar.dart';
import '../core/widgets/mh_surface_card.dart';
import '../services/ekyc_session_service.dart';
import '../core/utils/api_error_helper.dart';

/// Hub de vérification d'identité eKYC.
///
/// Crée une session Trusdy via le backend MHC, puis propose :
/// - le parcours web hébergé (document, selfie, vivacité, OTP — sans
///   installation supplémentaire) ;
/// - la lecture NFC native du passeport électronique.
///
/// Route : `/ekyc-verification?subscription=<id optionnel>`.
class EkycVerificationScreen extends StatefulWidget {
  final int? souscriptionId;

  const EkycVerificationScreen({super.key, this.souscriptionId});

  @override
  State<EkycVerificationScreen> createState() => _EkycVerificationScreenState();
}

class _EkycVerificationScreenState extends State<EkycVerificationScreen> {
  final _service = EkycSessionService.instance;

  EkycSession? _session;
  EkycSessionStatus? _status;
  String? _error;
  bool _creating = true;
  Timer? _poller;
  bool _completionDialogShown = false;

  @override
  void initState() {
    super.initState();
    _createSession();
  }

  @override
  void dispose() {
    _poller?.cancel();
    super.dispose();
  }

  Future<void> _createSession() async {
    setState(() {
      _creating = true;
      _error = null;
    });
    try {
      final session =
          await _service.createSession(souscriptionId: widget.souscriptionId);
      if (!mounted) return;
      setState(() {
        _session = session;
        _creating = false;
      });
      _startPolling();
    } catch (e) {
      if (mounted) {
        setState(() {
          _creating = false;
          _error = apiErrorToUserMessage(e);
        });
      }
    }
  }

  void _startPolling() {
    _poller?.cancel();
    _poller = Timer.periodic(const Duration(seconds: 4), (_) => _poll());
  }

  Future<void> _poll() async {
    final session = _session;
    if (session == null) return;
    try {
      final status = await _service.getStatus(session.sessionId);
      if (!mounted) return;
      setState(() => _status = status);
      if (status.isTerminal) {
        _poller?.cancel();
        _showCompletion(status);
      }
    } catch (_) {
      // Le polling est best-effort : une erreur réseau ne bloque pas l'écran.
    }
  }

  Future<void> _openHostedFlow() async {
    final url = _session?.verificationUrl;
    if (url == null) return;
    // Navigateur système (Chrome/Safari) : le mode in-app bloque getUserMedia
    // et les interactions tactile sont erratiques — le parcours eKYC a besoin
    // de la caméra, donc toujours dans le vrai navigateur.
    await launchUrl(
      Uri.parse(url),
      mode: LaunchMode.externalApplication,
    );
    _poll();
  }

  void _openNfc() {
    final url = _session?.verificationUrl;
    if (url == null) return;
    context.push('/ekyc-nfc?url=${Uri.encodeComponent(url)}').then((_) => _poll());
  }

  /// Fin du parcours (pattern AfriPaie) : l'app invite à fermer l'onglet
  /// eKYC du navigateur puis revient à l'accueil — l'utilisateur n'a pas
  /// à naviguer manuellement.
  void _showCompletion(EkycSessionStatus status) {
    if (_completionDialogShown || !mounted) return;
    _completionDialogShown = true;
    final (title, message, icon, color) = switch (status.status) {
      'VERIFIED' => (
          'Identité vérifiée',
          'Votre vérification est terminée. Vous pouvez fermer '
              "l'onglet de vérification dans votre navigateur.",
          Icons.verified,
          AppColors.success,
        ),
      'REVIEW' => (
          'Vérification soumise',
          'Votre dossier est en revue manuelle par nos équipes. '
              "Vous pouvez fermer l'onglet de vérification dans "
              'votre navigateur.',
          Icons.hourglass_top,
          AppColors.warning,
        ),
      'REJECTED' => (
          'Vérification refusée',
          'Votre vérification a été refusée. Vous pouvez fermer '
              "l'onglet de vérification dans votre navigateur.",
          Icons.cancel,
          AppColors.danger,
        ),
      _ => (
          'Session terminée',
          "Vous pouvez fermer l'onglet de vérification dans votre "
              'navigateur.',
          Icons.timer_off,
          AppColors.danger,
        ),
    };
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        icon: Icon(icon, color: color, size: 40),
        title: Text(title, textAlign: TextAlign.center),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(message, textAlign: TextAlign.center),
            if (status.reasons.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                status.reasons.join(', '),
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 12, color: AppColors.mutedText),
              ),
            ],
          ],
        ),
        actionsAlignment: MainAxisAlignment.center,
        actions: [
          if (status.status == 'EXPIRED')
            TextButton(
              onPressed: () {
                Navigator.of(ctx).pop();
                _completionDialogShown = false;
                _createSession();
              },
              child: const Text('Recommencer'),
            ),
          FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
            onPressed: () {
              Navigator.of(ctx).pop();
              if (mounted) context.go('/home');
            },
            icon: const Icon(Icons.home_outlined),
            label: const Text("Retour à l'accueil"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const MhAppBar(title: "Vérification d'identité", showBell: false),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (_creating)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(color: AppColors.primary),
                ),
              )
            else if (_error != null)
              MHSurfaceCard(
                child: Column(
                  children: [
                    Text(_error!,
                        style: const TextStyle(color: AppColors.danger)),
                    const SizedBox(height: 12),
                    OutlinedButton(
                      onPressed: _createSession,
                      child: const Text('Réessayer'),
                    ),
                  ],
                ),
              )
            else ...[
              if (_status != null) _statusCard(_status!),
              const SizedBox(height: 12),
              MHSurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Parcours de vérification',
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Le lien sécurisé ouvre la vérification hébergée : '
                      'consentement, photo du document, selfie et code de '
                      'vérification. La lecture NFC est faite ici, dans l’app.',
                      style: TextStyle(
                          color: AppColors.mutedText, height: 1.35),
                    ),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      style: FilledButton.styleFrom(
                          backgroundColor: AppColors.primary),
                      onPressed: _openHostedFlow,
                      icon: const Icon(Icons.open_in_new),
                      label: const Text('Continuer dans le navigateur sécurisé'),
                    ),
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      onPressed: _openNfc,
                      icon: const Icon(Icons.nfc),
                      label: const Text('Lire la puce NFC du passeport'),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      'Passeport électronique uniquement — la puce est vérifiée '
                      'cryptographiquement sur le serveur.',
                      style: TextStyle(
                          fontSize: 12, color: AppColors.mutedText),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _statusCard(EkycSessionStatus status) {
    final (color, icon, label) = switch (status.status) {
      'VERIFIED' => (AppColors.success, Icons.verified, 'Identité vérifiée'),
      'REJECTED' =>
        (AppColors.danger, Icons.cancel, 'Vérification refusée'),
      'REVIEW' =>
        (AppColors.warning, Icons.hourglass_top, 'Dossier en revue manuelle'),
      'EXPIRED' =>
        (AppColors.danger, Icons.timer_off, 'Session expirée — recommencez'),
      _ => (AppColors.primary, Icons.sync, 'Vérification en cours…'),
    };
    return MHSurfaceCard(
      child: Row(
        children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: TextStyle(
                        color: color, fontWeight: FontWeight.w700)),
                if (status.reasons.isNotEmpty)
                  Text(
                    status.reasons.join(', '),
                    style: const TextStyle(
                        fontSize: 12, color: AppColors.mutedText),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
