import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../services/account_service.dart';

/// Modification des informations d'identité (workflow V3 §3.3) : la demande
/// est validée par MHC. Nom, naissance et pièce d'identité exigent le
/// téléversement d'une pièce justificative.
class ProfileChangeScreen extends StatefulWidget {
  const ProfileChangeScreen({super.key});

  @override
  State<ProfileChangeScreen> createState() => _ProfileChangeScreenState();
}

class _ProfileChangeScreenState extends State<ProfileChangeScreen> {
  static const _fields = {
    'full_name': ('Nom et prénom', true),
    'date_naissance': ('Date de naissance (AAAA-MM-JJ)', true),
    'nationalite': ('Nationalité', false),
    'pays_residence': ('Pays de résidence', false),
    'numero_passeport': ('N° de pièce d’identité', true),
    'validite_passeport': ('Validité de la pièce (AAAA-MM-JJ)', true),
  };

  final _service = ProfileChangeService.instance;
  List<Map<String, dynamic>> _requests = [];
  bool _loading = true;
  String? _error;

  final Map<String, bool> _selected = {for (final k in _fields.keys) k: false};
  final Map<String, TextEditingController> _ctrls = {
    for (final k in _fields.keys) k: TextEditingController()
  };
  String? _piecePath;
  bool _sending = false;

  bool get _hasPending =>
      _requests.any((r) => r['statut'] == 'pending');

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in _ctrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final list = await _service.myRequests();
      if (mounted) {
        setState(() {
          _requests = list;
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

  bool get _needsPiece => _selected.entries
      .any((e) => e.value && _fields[e.key]!.$2);

  Future<void> _pickPiece() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png'],
    );
    final path = result?.files.single.path;
    if (path != null) setState(() => _piecePath = path);
  }

  Future<String?> _pieceDataUrl() async {
    if (_piecePath == null) return null;
    final bytes = await File(_piecePath!).readAsBytes();
    if (bytes.length > 5 * 1024 * 1024) {
      throw Exception('Pièce d’identité : 5 Mo maximum.');
    }
    final ext = _piecePath!.split('.').last.toLowerCase();
    final mime = ext == 'pdf'
        ? 'application/pdf'
        : ext == 'png'
            ? 'image/png'
            : 'image/jpeg';
    return 'data:$mime;base64,${base64Encode(bytes)}';
  }

  Future<void> _submit() async {
    final champs = <String, String>{};
    for (final e in _selected.entries) {
      if (!e.value) continue;
      final v = _ctrls[e.key]!.text.trim();
      if (v.isNotEmpty) champs[e.key] = v;
    }
    if (champs.isEmpty) {
      setState(() => _error = 'Sélectionnez au moins une information à modifier et saisissez la nouvelle valeur.');
      return;
    }
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      await _service.createRequest(
        champs: champs,
        pieceIdentiteNom: _piecePath?.split(RegExp(r'[\\/]')).last,
        pieceIdentiteDataUrl: await _pieceDataUrl(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Demande envoyée. Elle sera validée par MHC.'),
        backgroundColor: AppColors.success,
      ));
      for (final c in _ctrls.values) {
        c.clear();
      }
      _selected.updateAll((_, __) => false);
      _piecePath = null;
      _load();
    } catch (e) {
      if (mounted) {
        setState(() {
          _sending = false;
          _error = apiErrorToUserMessage(e);
        });
      }
      return;
    }
    if (mounted) setState(() => _sending = false);
  }

  String _date(dynamic v) {
    final d = DateTime.tryParse('${v ?? ''}');
    if (d == null) return '';
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  }

  Color _statusColor(String s) => switch (s) {
        'approved' => AppColors.success,
        'rejected' => AppColors.danger,
        _ => Colors.orange.shade700,
      };

  String _statusLabel(String s) => switch (s) {
        'approved' => 'Validée',
        'rejected' => 'Refusée',
        _ => 'En attente MHC',
      };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Modifier mes informations'),
      body: _loading
          ? const MhLoadingView()
          : _error != null && _requests.isEmpty && !_sending
              ? MhOfflineView(onRetry: _load)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
                  children: [
                    const Text(
                      'Les informations d’identité sont modifiées uniquement après '
                      'validation par MHC. Vos polices en cours ne sont pas modifiées '
                      'rétroactivement.',
                      style: TextStyle(
                          fontSize: 12, color: AppColors.mutedText, height: 1.45),
                    ),
                    if (_hasPending) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.orange.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Text(
                          'Une demande est déjà en attente de validation. Vos données '
                          'actuelles restent appliquées en attendant la décision.',
                          style: TextStyle(fontSize: 12, height: 1.4),
                        ),
                      ),
                    ],
                    const SizedBox(height: 14),
                    MHSurfaceCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Nouvelle demande',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: AppColors.secondary,
                                  fontSize: 14)),
                          ..._fields.entries.map((e) {
                            final key = e.key;
                            final (label, needsDoc) = e.value;
                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                CheckboxListTile(
                                  dense: true,
                                  contentPadding: EdgeInsets.zero,
                                  controlAffinity: ListTileControlAffinity.leading,
                                  value: _selected[key],
                                  onChanged: _hasPending || _sending
                                      ? null
                                      : (v) => setState(() => _selected[key] = v == true),
                                  title: Text(
                                    '$label${needsDoc ? ' (pièce requise)' : ''}',
                                    style: const TextStyle(fontSize: 13),
                                  ),
                                ),
                                if (_selected[key] == true)
                                  Padding(
                                    padding: const EdgeInsets.only(left: 12, bottom: 8),
                                    child: TextField(
                                      controller: _ctrls[key],
                                      enabled: !_sending,
                                      decoration: MHSurfaceCard.input(
                                        labelText: 'Nouvelle valeur',
                                        isDense: true,
                                      ),
                                    ),
                                  ),
                              ],
                            );
                          }),
                          if (_needsPiece) ...[
                            const SizedBox(height: 6),
                            InkWell(
                              onTap: _sending ? null : _pickPiece,
                              borderRadius: BorderRadius.circular(10),
                              child: InputDecorator(
                                decoration: MHSurfaceCard.input(
                                  labelText: 'Pièce d’identité *',
                                  suffixIcon: const Icon(Icons.attach_file,
                                      color: AppColors.mutedText),
                                ),
                                child: Text(
                                  _piecePath == null
                                      ? 'Joindre le document (PDF ou image, 5 Mo max)'
                                      : _piecePath!.split(RegExp(r'[\\/]')).last,
                                  style: TextStyle(
                                    color: _piecePath == null
                                        ? AppColors.mutedText
                                        : const Color(0xFF332542),
                                    fontSize: 13,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ),
                          ],
                          if (_error != null) ...[
                            const SizedBox(height: 8),
                            Text(_error!,
                                style: const TextStyle(
                                    color: AppColors.danger, fontSize: 13)),
                          ],
                          const SizedBox(height: 12),
                          MHGradientButton(
                            label: 'Envoyer la demande',
                            loading: _sending,
                            onPressed: _hasPending ? null : _submit,
                          ),
                        ],
                      ),
                    ),
                    if (_requests.isNotEmpty) ...[
                      const SizedBox(height: 18),
                      const Text('Mes demandes',
                          style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: AppColors.secondary,
                              fontSize: 14)),
                      const SizedBox(height: 8),
                      ..._requests.map((r) {
                        final libelles =
                            (r['libelles'] as Map?)?.values.join(', ') ?? '';
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: MHSurfaceCard(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(libelles,
                                          style: const TextStyle(
                                              fontWeight: FontWeight.w600,
                                              fontSize: 13)),
                                    ),
                                    Text(
                                      _statusLabel(r['statut']?.toString() ?? ''),
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: _statusColor(
                                            r['statut']?.toString() ?? ''),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 2),
                                Text('Demandée le ${_date(r['created_at'])}',
                                    style: const TextStyle(
                                        fontSize: 11, color: AppColors.mutedText)),
                                if (r['motif_refus'] != null)
                                  Padding(
                                    padding: const EdgeInsets.only(top: 4),
                                    child: Text(
                                      'Motif du refus : ${r['motif_refus']}',
                                      style: const TextStyle(
                                          fontSize: 12, color: AppColors.danger),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        );
                      }),
                    ],
                  ],
                ),
    );
  }
}
