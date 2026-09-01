import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../services/api_services.dart';
import '../pdf_viewer_screen.dart';

/// Étape 5 : Attestation – liste des attestations de la souscription, téléchargement PDF dans l'app.
class StepAttestationScreen extends StatefulWidget {
  const StepAttestationScreen({
    super.key,
    required this.subscriptionId,
    this.onDone,
  });

  final int subscriptionId;
  final VoidCallback? onDone;

  @override
  State<StepAttestationScreen> createState() => _StepAttestationScreenState();
}

class _StepAttestationScreenState extends State<StepAttestationScreen> {
  final AttestationsService _attestationsService = AttestationsService();
  List<Map<String, dynamic>> _attestations = [];
  bool _loading = true;
  String? _error;
  String? _openingPdfId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await _attestationsService.getSubscriptionAttestations(widget.subscriptionId);
      if (mounted) {
        setState(() {
          _attestations = list;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);

    return Container(
      color: const Color(0xFFE8F0F4),
      child: SingleChildScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: EdgeInsets.fromLTRB(20, 20, 20, mq.padding.bottom + mq.viewInsets.bottom + 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Vos attestations',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: const Color(0xFF1E293B),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Téléchargez et consultez vos attestations d\'assurance.',
              style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.mutedText),
            ),
            const SizedBox(height: 24),
            if (_loading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(color: AppColors.primary),
                ),
              )
            else if (_error != null)
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: AppColors.danger, size: 24),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        _error!,
                        style: const TextStyle(color: AppColors.danger, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              )
            else if (_attestations.isEmpty)
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(32),
                  child: Text(
                    'Aucune attestation pour cette souscription.',
                    style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.mutedText),
                  ),
                ),
              )
            else
              ..._attestations.map((att) {
                final id = att['id'] as int?;
                final numero = att['numero_attestation'] as String? ?? '${att['id']}';
                final statut = att['statut'] as String? ?? '';
                final opening = _openingPdfId == 'pdf-$id';
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Attestation $numero',
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  color: Color(0xFF1E293B),
                                ),
                              ),
                              if (statut.isNotEmpty)
                                Text(
                                  statut,
                                  style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                                ),
                            ],
                          ),
                        ),
                        if (id != null)
                          SizedBox(
                            width: 48,
                            height: 48,
                            child: IconButton(
                              onPressed: opening
                                  ? null
                                  : () async {
                                      setState(() => _openingPdfId = 'pdf-$id');
                                      try {
                                        final path = await _attestationsService.downloadAttestationPdf(
                                          id,
                                          numeroAttestation: numero,
                                        );
                                        if (!mounted) return;
                                        await Navigator.of(context).push(
                                          MaterialPageRoute(
                                            builder: (_) => PdfViewerScreen(
                                              filePath: path,
                                              title: 'Attestation $numero',
                                            ),
                                          ),
                                        );
                                      } catch (e) {
                                        if (mounted) {
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            SnackBar(
                                              content: Text(
                                                'Erreur : ${e.toString().replaceFirst('Exception: ', '')}',
                                              ),
                                              backgroundColor: AppColors.danger,
                                            ),
                                          );
                                        }
                                      } finally {
                                        if (mounted) setState(() => _openingPdfId = null);
                                      }
                                    },
                              icon: opening
                                  ? const SizedBox(
                                      width: 24,
                                      height: 24,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.picture_as_pdf, color: AppColors.primary),
                              tooltip: 'Voir le PDF',
                            ),
                          ),
                      ],
                    ),
                  ),
                );
              }),
            if (widget.onDone != null) ...[
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: widget.onDone,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text('Terminer'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
