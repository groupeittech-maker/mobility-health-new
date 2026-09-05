import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:open_filex/open_filex.dart';

import '../../core/utils/json_value.dart';
import '../../services/sinistre_attachment_service.dart';

/// Section certificat de décès hospitalier (fichier joint au dossier).
class ReferentCertificatDecesSection extends StatefulWidget {
  const ReferentCertificatDecesSection({
    super.key,
    required this.sinistreId,
    required this.attachment,
    required this.canUpload,
    required this.onChanged,
  });

  final int sinistreId;
  final Map<String, dynamic>? attachment;
  final bool canUpload;
  final Future<void> Function() onChanged;

  @override
  State<ReferentCertificatDecesSection> createState() => _ReferentCertificatDecesSectionState();
}

class _ReferentCertificatDecesSectionState extends State<ReferentCertificatDecesSection> {
  final _service = SinistreAttachmentService.instance;
  bool _busy = false;

  String? _formatDate(dynamic value) {
    if (value == null) return null;
    try {
      return DateFormat('dd/MM/yyyy HH:mm').format(DateTime.parse(value.toString()).toLocal());
    } catch (_) {
      return value.toString();
    }
  }

  String? _formatSize(dynamic bytes) {
    final n = parseJsonInt(bytes);
    if (n == null) return null;
    if (n < 1024) return '$n o';
    if (n < 1024 * 1024) return '${(n / 1024).toStringAsFixed(1)} Ko';
    return '${(n / (1024 * 1024)).toStringAsFixed(1)} Mo';
  }

  Future<void> _download() async {
    setState(() => _busy = true);
    try {
      final path = await _service.downloadCertificatDeces(
        widget.sinistreId,
        fileName: widget.attachment?['file_name']?.toString(),
      );
      await OpenFilex.open(path);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', '')), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickAndUpload() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf', 'jpg', 'jpeg', 'png'],
      withData: false,
    );
    if (result == null || result.files.isEmpty) return;
    final path = result.files.single.path;
    if (path == null || path.isEmpty) return;

    setState(() => _busy = true);
    try {
      await _service.uploadCertificatDeces(widget.sinistreId, path);
      await widget.onChanged();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Certificat de décès ajouté au dossier.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', '')), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final att = widget.attachment;
    final meta = <String>[
      if (_formatDate(att?['created_at']) != null) 'Ajouté le ${_formatDate(att!['created_at'])}',
      if (_formatSize(att?['file_size']) != null) _formatSize(att!['file_size'])!,
      if (att?['uploaded_by_name'] != null) 'par ${att!['uploaded_by_name']}',
    ].join(' • ');

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Certificat de décès',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const SizedBox(height: 4),
            Text(
              "Joignez le certificat émis par l'hôpital (PDF ou image, max 10 Mo).",
              style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
            ),
            const Divider(height: 20),
            if (att != null) ...[
              Text(att['file_name']?.toString() ?? 'Fichier joint', style: const TextStyle(fontWeight: FontWeight.w600)),
              if (meta.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(meta, style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
                ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _busy ? null : _download,
                icon: _busy
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.download_outlined, size: 18),
                label: const Text('Télécharger'),
              ),
            ] else
              Text('Aucun certificat joint.', style: TextStyle(color: Colors.grey.shade700, fontSize: 13)),
            if (widget.canUpload) ...[
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _busy ? null : _pickAndUpload,
                icon: const Icon(Icons.attach_file),
                label: Text(att != null ? 'Remplacer le fichier' : 'Joindre un fichier'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
