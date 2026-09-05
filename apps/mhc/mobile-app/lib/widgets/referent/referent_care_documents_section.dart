import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/utils/json_value.dart';
import '../../models/mhc_care_document.dart';
import '../../screens/pdf_viewer_screen.dart';
import '../../services/mhc_care_document_service.dart';
import 'mhc_care_document_form_helper.dart';

/// Bottom sheet d'émission — contrôleurs possédés par le State (dispose sûr).
class _IssueCareDocumentSheet extends StatefulWidget {
  const _IssueCareDocumentSheet({
    required this.actions,
    required this.sinistreId,
    required this.prefill,
    required this.onIssued,
  });

  final List<String> actions;
  final int sinistreId;
  final Map<String, String> prefill;
  final Future<void> Function() onIssued;

  @override
  State<_IssueCareDocumentSheet> createState() => _IssueCareDocumentSheetState();
}

class _IssueCareDocumentSheetState extends State<_IssueCareDocumentSheet> {
  final _service = MhcCareDocumentService.instance;
  late String _selectedType;
  final _controllers = <String, TextEditingController>{};
  final _selectedRefusalMotifs = <String>{};
  late final TextEditingController _notesController;
  var _issuing = false;

  @override
  void initState() {
    super.initState();
    _selectedType = widget.actions.first;
    _notesController = TextEditingController();
  }

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_issuing) return;
    setState(() => _issuing = true);
    try {
      final payload = MhcCareDocumentFormHelper.collectPayload(
        _selectedType,
        _controllers,
        _selectedRefusalMotifs,
      );
      await _service.issueCareDocument(
        widget.sinistreId,
        documentType: _selectedType,
        payload: payload,
        notes: _notesController.text.trim().isEmpty ? null : _notesController.text.trim(),
      );
      if (!mounted) return;
      Navigator.pop(context);
      await widget.onIssued();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
      setState(() => _issuing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final fields = MhcCareDocumentFormHelper.buildFieldsForType(
      _selectedType,
      _controllers,
      widget.prefill,
      _selectedRefusalMotifs,
      setState,
    );

    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: 16 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Émettre un bon / attestation',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              key: ValueKey(_selectedType),
              initialValue: _selectedType,
              decoration: const InputDecoration(
                labelText: 'Type de document',
                border: OutlineInputBorder(),
              ),
              items: widget.actions
                  .map((t) => DropdownMenuItem(
                        value: t,
                        child: Text(MhcCareDocumentLabels.labelFor(t), style: const TextStyle(fontSize: 13)),
                      ))
                  .toList(),
              onChanged: _issuing
                  ? null
                  : (v) {
                      if (v == null) return;
                      setState(() => _selectedType = v);
                    },
            ),
            const SizedBox(height: 16),
            ...fields,
            TextField(
              controller: _notesController,
              decoration: const InputDecoration(
                labelText: 'Notes internes (optionnel)',
                border: OutlineInputBorder(),
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _issuing ? null : _submit,
              icon: _issuing
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.description_outlined),
              label: Text(_issuing ? 'Émission…' : 'Émettre le document'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Section bons / attestations MHC : liste, émission, PDF (aligné web).
class ReferentCareDocumentsSection extends StatefulWidget {
  const ReferentCareDocumentsSection({
    super.key,
    required this.sinistreId,
    this.alerte,
    this.sinistre,
    this.stay,
    this.onChanged,
  });

  final int sinistreId;
  final Map<String, dynamic>? alerte;
  final Map<String, dynamic>? sinistre;
  final Map<String, dynamic>? stay;
  final VoidCallback? onChanged;

  @override
  State<ReferentCareDocumentsSection> createState() => _ReferentCareDocumentsSectionState();
}

class _ReferentCareDocumentsSectionState extends State<ReferentCareDocumentsSection> {
  final _service = MhcCareDocumentService.instance;
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;
  int? _downloadingId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant ReferentCareDocumentsSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.sinistreId != widget.sinistreId) {
      _load();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _service.fetchCareDocuments(widget.sinistreId);
      if (!mounted) return;
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  List<String> get _actions {
    final raw = _data?['actions_possibles'];
    if (raw is! List) return [];
    return raw.map((e) => e.toString()).toList();
  }

  List<Map<String, dynamic>> get _documents {
    final raw = _data?['documents'];
    if (raw is! List) return [];
    return raw.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
  }

  Future<void> _openPdf(Map<String, dynamic> doc) async {
    final id = doc['id'];
    final docId = id is int ? id : (id is num ? id.toInt() : null);
    if (docId == null) return;
    setState(() => _downloadingId = docId);
    try {
      final path = await _service.downloadCareDocumentPdf(
        docId,
        numero: doc['numero']?.toString(),
      );
      if (!mounted) return;
      final title = doc['titre']?.toString() ?? MhcCareDocumentLabels.labelFor(doc['document_type']?.toString() ?? '');
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PdfViewerScreen(filePath: path, title: title),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _downloadingId = null);
    }
  }

  Future<void> _showIssueSheet() async {
    final actions = _actions;
    if (actions.isEmpty) return;

    final prefill = MhcCareDocumentFormHelper.buildPrefill(
      alerte: widget.alerte,
      sinistre: widget.sinistre,
      stay: widget.stay,
    );

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (ctx) => _IssueCareDocumentSheet(
        actions: actions,
        sinistreId: widget.sinistreId,
        prefill: prefill,
        onIssued: () async {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Document MHC émis.'), backgroundColor: Colors.green),
          );
          await _load();
          widget.onChanged?.call();
        },
      ),
    );
  }

  String _formatDate(dynamic value) {
    if (value == null) return '—';
    final d = DateTime.tryParse(value.toString());
    if (d == null) return value.toString();
    return DateFormat('dd/MM/yyyy HH:mm').format(d.toLocal());
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Text(
                    'Bons et attestations MHC',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: _loading ? null : _load,
                  tooltip: 'Actualiser',
                ),
              ],
            ),
            if (_data?['numero_sinistre'] != null)
              Text(
                'Sinistre ${_data!['numero_sinistre']} — ${_documents.length} document(s)',
                style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
              )
            else
              Text(
                'Le numéro de sinistre sera attribué à la validation médicale.',
                style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
              ),
            const Divider(height: 20),
            if (_loading)
              const Center(child: Padding(padding: EdgeInsets.all(12), child: CircularProgressIndicator()))
            else if (_error != null)
              Text(_error!, style: TextStyle(color: Colors.red.shade700))
            else ...[
              if (_documents.isEmpty)
                Text('Aucun document émis.', style: TextStyle(color: Colors.grey.shade600))
              else
                ..._documents.map((doc) {
                  final docId = parseJsonInt(doc['id']);
                  final type = doc['document_type']?.toString() ?? '';
                  final title = doc['titre']?.toString() ?? MhcCareDocumentLabels.labelFor(type);
                  final loading = docId != null && _downloadingId == docId;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 10),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.grey.shade300),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
                        const SizedBox(height: 4),
                        Text('N° ${doc['numero'] ?? '—'}', style: TextStyle(color: Colors.red.shade700, fontWeight: FontWeight.w700)),
                        Text(
                          'Émis le ${_formatDate(doc['issued_at'])}'
                          '${doc['valid_until'] != null ? ' • valable jusqu\'au ${_formatDate(doc['valid_until'])}' : ''}',
                          style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                        ),
                        const SizedBox(height: 8),
                        OutlinedButton.icon(
                          onPressed: loading || docId == null ? null : () => _openPdf(doc),
                          icon: loading
                              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                              : const Icon(Icons.picture_as_pdf_outlined, size: 18),
                          label: Text(
                            type == 'certificat_deces' ? 'Télécharger le certificat' : 'Voir le PDF',
                          ),
                        ),
                      ],
                    ),
                  );
                }),
              if (_actions.isNotEmpty) ...[
                const SizedBox(height: 8),
                FilledButton.icon(
                  onPressed: _showIssueSheet,
                  icon: const Icon(Icons.add_circle_outline),
                  label: const Text('Émettre un document'),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}
