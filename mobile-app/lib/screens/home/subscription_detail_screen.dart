import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';

import '../../core/constants/app_colors.dart';
import '../../models/subscription.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';
import '../pdf_viewer_screen.dart';

/// Détail d'une souscription : identité, récap souscription, attestations, e-carte (si généré).
class SubscriptionDetailScreen extends StatefulWidget {
  const SubscriptionDetailScreen({
    super.key,
    required this.subscription,
  });

  final SubscriptionModel subscription;

  @override
  State<SubscriptionDetailScreen> createState() => _SubscriptionDetailScreenState();
}

class _SubscriptionDetailScreenState extends State<SubscriptionDetailScreen> {
  final AttestationsService _attestationsService = AttestationsService();
  final SubscriptionsService _subscriptionsService = SubscriptionsService();
  late SubscriptionModel _subscription;
  List<Map<String, dynamic>> _attestations = [];
  Map<String, dynamic>? _user;
  bool _loading = true;
  String? _error;
  String? _downloadingId; // 'pdf-{id}' ou 'ecard-{id}'
  bool _resiliationLoading = false;

  @override
  void initState() {
    super.initState();
    _subscription = widget.subscription;
    _load();
  }

  @override
  void didUpdateWidget(covariant SubscriptionDetailScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.subscription.id != widget.subscription.id) {
      _subscription = widget.subscription;
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      Map<String, dynamic>? userMap;
      try {
        final u = await AuthService.instance.getMe();
        userMap = {
          'display_name': u.displayName,
          'email': u.email,
          'telephone': u.telephone ?? '',
        };
      } catch (_) {}
      final att = await _attestationsService.getSubscriptionAttestations(_subscription.id);
      if (!mounted) return;
      setState(() {
        _user = userMap;
        _attestations = att;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _loading = false;
        });
      }
    }
  }

  String _formatDate(dynamic d) {
    if (d == null) return '–';
    if (d is DateTime) return '${d.day}/${d.month}/${d.year}';
    final s = d.toString();
    if (s.length >= 10) return '${s.substring(8, 10)}/${s.substring(5, 7)}/${s.substring(0, 4)}';
    return s;
  }

  /// E-carte disponible si l'API renvoie carte_numerique_url ou carte_numerique_path (attestation définitive).
  bool _hasEcard(Map<String, dynamic> att) {
    final url = att['carte_numerique_url'] ?? att['carteNumeriqueUrl'];
    final path = att['carte_numerique_path'] ?? att['carteNumeriquePath'];
    if (url != null && url.toString().trim().isNotEmpty) return true;
    if (path != null && path.toString().trim().isNotEmpty) return true;
    return false;
  }

  Future<void> _downloadPdf(int id, String numero) async {
    setState(() => _downloadingId = 'pdf-$id');
    try {
      final path = await _attestationsService.downloadAttestationPdf(id, numeroAttestation: numero);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PdfViewerScreen(filePath: path, title: 'Attestation $numero'),
        ),
      );
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

  Future<void> _downloadEcard(int id, String numero) async {
    setState(() => _downloadingId = 'ecard-$id');
    try {
      final path = await _attestationsService.downloadEcard(id, numeroAttestation: numero);
      if (!mounted) return;
      await OpenFilex.open(path);
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

  Future<void> _requestResiliation(String? notes) async {
    setState(() => _resiliationLoading = true);
    try {
      final updated = await _subscriptionsService.requestResiliation(
        _subscription.id,
        notes: notes?.trim().isEmpty == true ? null : notes,
      );
      if (!mounted) return;
      setState(() {
        _subscription = updated;
        _resiliationLoading = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Demande de résiliation envoyée. Elle sera examinée par un agent.'),
            backgroundColor: AppColors.success,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _resiliationLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Erreur : ${e.toString().replaceFirst('Exception: ', '')}'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    }
  }

  void _showResiliationDialog() {
    final controller = TextEditingController();
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 20,
          bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Demande de résiliation',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1E293B),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Indiquez la raison de votre demande (optionnel).',
              style: TextStyle(fontSize: 14, color: Color(0xFF64748B)),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: controller,
              maxLines: 4,
              decoration: const InputDecoration(
                hintText: 'Raison de la demande...',
                border: OutlineInputBorder(),
                alignLabelWithHint: true,
              ),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(ctx),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF64748B),
                      side: const BorderSide(color: Color(0xFFE2E8F0)),
                    ),
                    child: const Text('Annuler'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.pop(ctx);
                      _requestResiliation(controller.text);
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Envoyer'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final s = _subscription;
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    final isResiliee = s.statut == 'resiliee';

    if (isResiliee) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Détail souscription'),
          backgroundColor: Colors.white,
          foregroundColor: const Color(0xFF1E293B),
          elevation: 0,
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.block, size: 64, color: Colors.grey.shade400),
                const SizedBox(height: 20),
                Text(
                  'Souscription résiliée',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: const Color(0xFF1E293B),
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  'L\'accès aux informations de cette souscription n\'est plus disponible.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: const Color(0xFF64748B),
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Détail souscription'),
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF1E293B),
        elevation: 0,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: EdgeInsets.fromLTRB(20, 16, 20, bottomPadding),
                children: [
                  if (_error != null) ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.danger.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(_error!, style: const TextStyle(color: AppColors.danger, fontSize: 13)),
                    ),
                    const SizedBox(height: 16),
                  ],
                  _sectionTitle(theme, 'Identité'),
                  _card([
                    _row('Nom', _user?['display_name'] ?? '–'),
                    _row('Email', _user?['email'] ?? '–'),
                    _row('Téléphone', _user?['telephone'] ?? '–'),
                  ]),
                  const SizedBox(height: 20),
                  _sectionTitle(theme, 'Souscription'),
                  _card([
                    _row('N° souscription', s.numeroSouscription.isNotEmpty ? s.numeroSouscription : '#${s.id}'),
                    _row('Statut', s.statut),
                    _row('Produit', s.produitAssurance?.nom ?? 'Produit #${s.produitAssuranceId}'),
                    _row('Début', _formatDate(s.dateDebut)),
                    _row('Fin', _formatDate(s.dateFin)),
                    _row('Prix', '${s.prixApplique.toStringAsFixed(0)} XAF'),
                  ]),
                  if (s.canRequestResiliation)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: _resiliationLoading ? null : _showResiliationDialog,
                          icon: _resiliationLoading
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                )
                              : const Icon(Icons.cancel_outlined, size: 20),
                          label: Text(_resiliationLoading ? 'Envoi en cours...' : 'Demander la résiliation'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.danger.withValues(alpha: 0.9),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                          ),
                        ),
                      ),
                    ),
                  if (s.hasPendingResiliation)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.orange.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.schedule, color: Colors.orange.shade700, size: 20),
                            const SizedBox(width: 8),
                            const Expanded(
                              child: Text(
                                'Demande de résiliation en cours de traitement.',
                                style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  if (s.demandeResiliation == 'approved')
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.success.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.check_circle, color: AppColors.success, size: 20),
                            const SizedBox(width: 8),
                            const Expanded(
                              child: Text(
                                'Résiliation approuvée.',
                                style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  if (s.demandeResiliation == 'rejected')
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.red.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.cancel, color: Colors.red.shade700, size: 20),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                s.demandeResiliationNotes?.isNotEmpty == true
                                    ? 'Demande refusée. ${s.demandeResiliationNotes}'
                                    : 'Demande de résiliation refusée.',
                                style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                                maxLines: 3,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  const SizedBox(height: 20),
                  _sectionTitle(theme, 'Attestations & E-carte'),
                  if (_attestations.isEmpty)
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: 0.06),
                            blurRadius: 10,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: const Center(
                        child: Text(
                          'Aucune attestation ou e-carte générée pour le moment.',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 14, color: Color(0xFF64748B)),
                        ),
                      ),
                    )
                  else
                    ..._attestations.map((att) {
                      final id = att['id'] as int?;
                      final numero = att['numero_attestation'] as String? ?? '#${att['id']}';
                      final type = att['type_attestation'] as String? ?? 'attestation';
                      final hasEcard = _hasEcard(att);
                      final pdfOpening = id != null && _downloadingId == 'pdf-$id';
                      final ecardOpening = id != null && _downloadingId == 'ecard-$id';
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.06),
                                blurRadius: 10,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: AppColors.primary.withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Icon(
                                  Icons.description,
                                  color: AppColors.primary,
                                  size: 28,
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Attestation $numero',
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 16,
                                        color: Color(0xFF1E293B),
                                      ),
                                    ),
                                    Text(
                                      type,
                                      style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                                    ),
                                  ],
                                ),
                              ),
                              if (id != null) ...[
                                IconButton(
                                  onPressed: pdfOpening ? null : () => _downloadPdf(id, numero),
                                  icon: pdfOpening
                                      ? const SizedBox(
                                          width: 24,
                                          height: 24,
                                          child: CircularProgressIndicator(strokeWidth: 2),
                                        )
                                      : const Icon(Icons.picture_as_pdf, color: AppColors.primary),
                                  tooltip: 'PDF',
                                ),
                                if (hasEcard)
                                  IconButton(
                                    onPressed: ecardOpening ? null : () => _downloadEcard(id, numero),
                                    icon: ecardOpening
                                        ? const SizedBox(
                                            width: 24,
                                            height: 24,
                                            child: CircularProgressIndicator(strokeWidth: 2),
                                          )
                                        : const Icon(Icons.credit_card, color: AppColors.primary),
                                    tooltip: 'E-carte',
                                  ),
                              ],
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

  Widget _sectionTitle(ThemeData theme, String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: theme.textTheme.titleMedium?.copyWith(
          fontWeight: FontWeight.bold,
          color: AppColors.primary,
        ),
      ),
    );
  }

  Widget _card(List<Widget> rows) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: rows,
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: Color(0xFF1E293B)),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
