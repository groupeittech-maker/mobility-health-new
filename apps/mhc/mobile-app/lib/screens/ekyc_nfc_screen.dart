import 'package:flutter/material.dart';

import '../core/constants/app_colors.dart';
import '../core/widgets/mh_app_bar.dart';
import '../core/widgets/mh_surface_card.dart';
import '../services/ekyc_service.dart';
import '../services/mrz_scan_service.dart';
import '../services/passport_nfc_service.dart';

/// Lecture NFC du passeport électronique dans un parcours eKYC Trusdy.
///
/// Ouvert depuis le lien `verification_url` (paramètre `?url=` de la route
/// `/ekyc-nfc`). Le serveur re-vérifie tout : l'écran collecte les clés BAC
/// (issues du MRZ), lit la puce et envoie les octets bruts. Verdicts affichés
/// tels que retournés : VALID / INVALID / INDETERMINATE.
class EkycNfcScreen extends StatefulWidget {
  final String verificationUrl;

  const EkycNfcScreen({super.key, required this.verificationUrl});

  @override
  State<EkycNfcScreen> createState() => _EkycNfcScreenState();
}

class _EkycNfcScreenState extends State<EkycNfcScreen> {
  final _nfc = PassportNfcService();
  final _ekyc = EkycService();
  final _mrzScanner = MrzScanService();
  bool _scanningMrz = false;

  final _docNumberCtrl = TextEditingController();
  DateTime? _birthDate;
  DateTime? _expiryDate;

  EkycSessionRef? _session;
  bool _reading = false;
  int _progress = 0;
  String _progressMessage = '';
  String? _error;
  NfcSubmissionResult? _result;

  @override
  void initState() {
    super.initState();
    _session = EkycSessionRef.parse(widget.verificationUrl);
    if (_session == null) {
      _error = 'Lien de vérification invalide ou expiré.';
    }
  }

  @override
  void dispose() {
    _docNumberCtrl.dispose();
    _ekyc.close();
    super.dispose();
  }

  Future<void> _pickDate({
    required DateTime? current,
    required void Function(DateTime) onPicked,
    DateTime? firstDate,
    DateTime? lastDate,
  }) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime(1990),
      firstDate: firstDate ?? DateTime(1920),
      lastDate: lastDate ?? DateTime(2100),
    );
    if (picked != null) onPicked(picked);
  }

  bool get _formReady =>
      _docNumberCtrl.text.trim().length >= 6 &&
      _birthDate != null &&
      _expiryDate != null;

  /// Photographie la zone MRZ et pré-remplit les trois clés BAC — la saisie
  /// manuelle reste possible si le scan échoue.
  Future<void> _scanMrz() async {
    setState(() {
      _scanningMrz = true;
      _error = null;
    });
    try {
      final result = await _mrzScanner.scanFromCamera();
      if (result != null && mounted) {
        setState(() {
          _docNumberCtrl.text = result.documentNumber;
          _birthDate = result.birthDate;
          _expiryDate = result.expiryDate;
        });
      }
    } on MrzScanException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (e) {
      if (mounted) {
        setState(() => _error = 'Scan impossible : $e — saisissez les champs à la main.');
      }
    } finally {
      if (mounted) setState(() => _scanningMrz = false);
    }
  }

  Future<void> _readAndSubmit() async {
    final session = _session;
    if (session == null || !_formReady) return;
    setState(() {
      _reading = true;
      _error = null;
      _result = null;
      _progress = 0;
    });
    try {
      final data = await _nfc.readPassport(
        PassportBacKeys(
          documentNumber: _docNumberCtrl.text.trim(),
          birthDate: _birthDate!,
          expiryDate: _expiryDate!,
        ),
        onProgress: (percent, message) {
          if (mounted) {
            setState(() {
              _progress = percent;
              _progressMessage = message;
            });
          }
        },
      );
      final result = await _ekyc.submitNfc(
        session,
        efCom: data.efCom,
        efSod: data.efSod,
        dg1: data.dg1,
        dg2: data.dg2,
      );
      if (mounted) setState(() => _result = result);
    } on PassportNfcException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } on EkycApiException catch (e) {
      if (mounted) setState(() => _error = 'Échec de l’envoi : ${e.detail}');
    } catch (e) {
      if (mounted) setState(() => _error = 'Erreur inattendue : $e');
    } finally {
      if (mounted) setState(() => _reading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const MhAppBar(title: 'Passeport électronique', showBell: false),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            MHSurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Lecture de la puce NFC',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'La puce de votre passeport électronique est vérifiée '
                    'cryptographiquement par le serveur. Saisissez les trois '
                    'éléments du bas de la page photo (MRZ), puis posez le '
                    'passeport sous le téléphone.',
                    style: TextStyle(color: AppColors.mutedText, height: 1.35),
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    onPressed: _scanningMrz ? null : _scanMrz,
                    icon: const Icon(Icons.document_scanner_outlined),
                    label: Text(_scanningMrz
                        ? 'Analyse du MRZ…'
                        : 'Scanner la zone MRZ avec la caméra'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _docNumberCtrl,
                    textCapitalization: TextCapitalization.characters,
                    decoration: const InputDecoration(
                      labelText: 'Numéro de document',
                      hintText: 'ex. AB1234567',
                    ),
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 8),
                  _dateField(
                    label: 'Date de naissance (JJ/MM/AAAA)',
                    value: _birthDate,
                    onTap: () => _pickDate(
                      current: _birthDate,
                      onPicked: (d) => setState(() => _birthDate = d),
                    ),
                  ),
                  const SizedBox(height: 8),
                  _dateField(
                    label: "Date d'expiration (JJ/MM/AAAA)",
                    value: _expiryDate,
                    onTap: () => _pickDate(
                      current: _expiryDate ?? DateTime(2030),
                      onPicked: (d) => setState(() => _expiryDate = d),
                      firstDate: DateTime(2000),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            if (_error != null)
              MHSurfaceCard(
                child: Text(
                  _error!,
                  style: const TextStyle(color: AppColors.danger),
                ),
              ),
            if (_result != null) _resultCard(_result!),
            const SizedBox(height: 12),
            if (_reading) ...[
              LinearProgressIndicator(
                value: _progress / 100,
                color: AppColors.primary,
                backgroundColor: AppColors.surfaceFieldBorder,
              ),
              const SizedBox(height: 8),
              Text(_progressMessage, textAlign: TextAlign.center),
              const SizedBox(height: 8),
              const Text(
                'Ne bougez ni le téléphone ni le passeport.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.mutedText),
              ),
            ] else
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: AppColors.primary),
                onPressed: _formReady ? _readAndSubmit : null,
                icon: const Icon(Icons.nfc),
                label: const Text('Lire la puce du passeport'),
              ),
          ],
        ),
      ),
    );
  }

  Widget _dateField({
    required String label,
    required DateTime? value,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      child: InputDecorator(
        decoration: InputDecoration(labelText: label),
        child: Text(
          value == null
              ? 'Choisir'
              : '${value.day.toString().padLeft(2, '0')}/'
                  '${value.month.toString().padLeft(2, '0')}/${value.year}',
        ),
      ),
    );
  }

  Widget _resultCard(NfcSubmissionResult result) {
    final (color, icon, text) = switch (result.nfcStatus) {
      'VALID' => (
          AppColors.success,
          Icons.verified,
          'Puce vérifiée cryptographiquement. Vous pouvez poursuivre la vérification.',
        ),
        'INVALID' => (
          AppColors.danger,
          Icons.gpp_bad,
          'La puce n’a pas pu être authentifiée (${result.reason}). Le dossier est bloqué.',
        ),
        _ => (
          AppColors.warning,
          Icons.help_center,
          'Vérification impossible pour l’instant (${result.reason}). '
              'Votre dossier passera en revue manuelle.',
        ),
    };
    return MHSurfaceCard(
      child: Row(
        children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(width: 12),
          Expanded(child: Text(text, style: const TextStyle(height: 1.35))),
        ],
      ),
    );
  }
}
