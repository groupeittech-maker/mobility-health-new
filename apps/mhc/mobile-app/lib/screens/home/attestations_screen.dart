import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:open_filex/open_filex.dart';

import '../../core/constants/app_colors.dart';
import '../../services/api_services.dart';

/// Mes attestations – liste et téléchargement PDF / e-carte.
class AttestationsScreen extends StatefulWidget {
  const AttestationsScreen({super.key});

  @override
  State<AttestationsScreen> createState() => _AttestationsScreenState();
}

class _AttestationsScreenState extends State<AttestationsScreen> {
  final AttestationsService _attestationsService = AttestationsService();
  List<Map<String, dynamic>> _attestations = [];
  bool _loading = true;
  String? _error;
  String? _downloadingId; // attestation_id en cours de téléchargement

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool forceRefresh = false}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await _attestationsService.getUserAttestations(forceRefresh: forceRefresh);
      if (mounted) {
        setState(() {
          _attestations = list;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString().replaceFirst('Exception: ', '');
        });
      }
    }
  }

  Future<void> _downloadPdf(Map<String, dynamic> att) async {
    final id = att['id'] as int?;
    if (id == null) return;
    final numero = att['numero_attestation'] as String? ?? '${att['id']}';
    setState(() => _downloadingId = 'pdf-$id');
    try {
      final path = await _attestationsService.downloadAttestationPdf(
        id,
        numeroAttestation: numero,
      );
      if (!mounted) return;
      final result = await OpenFilex.open(path);
      if (!mounted) return;
      if (result.type != ResultType.done) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result.message)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Erreur : ${e.toString().replaceFirst('Exception: ', '')}'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _downloadingId = null);
    }
  }

  Future<void> _downloadEcard(Map<String, dynamic> att) async {
    final id = att['id'] as int?;
    if (id == null) return;
    final numero = att['numero_attestation'] as String? ?? '${att['id']}';
    setState(() => _downloadingId = 'ecard-$id');
    try {
      final path = await _attestationsService.downloadEcard(
        id,
        numeroAttestation: numero,
      );
      if (!mounted) return;
      final result = await OpenFilex.open(path);
      if (!mounted) return;
      if (result.type != ResultType.done) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result.message)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Erreur : ${e.toString().replaceFirst('Exception: ', '')}'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _downloadingId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mes attestations'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () => _load(forceRefresh: true),
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? _buildError(theme)
                : _attestations.isEmpty
                    ? _buildEmpty(theme)
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _attestations.length,
                        itemBuilder: (context, index) {
                          return _AttestationCard(
                            attestation: _attestations[index],
                            onDownloadPdf: _downloadPdf,
                            onDownloadEcard: _downloadEcard,
                            downloadingId: _downloadingId,
                          );
                        },
                      ),
      ),
    );
  }

  Widget _buildError(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: AppColors.danger),
            const SizedBox(height: 16),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.danger),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _load,
              icon: const Icon(Icons.refresh),
              label: const Text('Réessayer'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmpty(ThemeData theme) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.description_outlined, size: 64, color: theme.colorScheme.primary.withValues(alpha: 0.6)),
            const SizedBox(height: 16),
            Text(
              'Aucune attestation',
              style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Vos attestations apparaîtront ici après souscription et validation.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.mutedText),
            ),
          ],
        ),
      ),
    );
  }
}

class _AttestationCard extends StatelessWidget {
  const _AttestationCard({
    required this.attestation,
    required this.onDownloadPdf,
    required this.onDownloadEcard,
    this.downloadingId,
  });

  final Map<String, dynamic> attestation;
  final void Function(Map<String, dynamic>) onDownloadPdf;
  final void Function(Map<String, dynamic>) onDownloadEcard;
  final String? downloadingId;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final id = attestation['id'] as int? ?? 0;
    final numero = attestation['numero_attestation'] as String? ?? '—';
    final type = attestation['type_attestation'] as String? ?? '—';
    final created = attestation['created_at'] as String?;
    final dateStr = created != null
        ? DateFormat('dd/MM/yyyy').format(DateTime.tryParse(created) ?? DateTime.now())
        : '—';
    final isDefinitive = type.toLowerCase() == 'definitive';
    final url = attestation['carte_numerique_url'] ?? attestation['carteNumeriqueUrl'];
    final path = attestation['carte_numerique_path'] ?? attestation['carteNumeriquePath'];
    final hasEcard = isDefinitive && (
        (url != null && url.toString().trim().isNotEmpty) ||
        (path != null && path.toString().trim().isNotEmpty));
    final pdfDownloading = downloadingId == 'pdf-$id';
    final ecardDownloading = downloadingId == 'ecard-$id';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(Icons.description, color: AppColors.primary, size: 28),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        numero,
                        style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Type : $type • $dateStr',
                        style: theme.textTheme.bodySmall?.copyWith(color: AppColors.mutedText),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: pdfDownloading ? null : () => onDownloadPdf(attestation),
                    icon: pdfDownloading
                        ? SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2, color: theme.colorScheme.onPrimary),
                          )
                        : const Icon(Icons.picture_as_pdf, size: 20),
                    label: Text(pdfDownloading ? 'Téléchargement…' : 'PDF'),
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.primary,
                    ),
                  ),
                ),
                if (hasEcard) ...[
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: ecardDownloading ? null : () => onDownloadEcard(attestation),
                      icon: ecardDownloading
                          ? SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: theme.colorScheme.primary,
                              ),
                            )
                          : const Icon(Icons.credit_card, size: 20),
                      label: Text(ecardDownloading ? 'Téléchargement…' : 'E-carte'),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
