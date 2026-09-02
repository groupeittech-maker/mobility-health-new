import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../services/medecin_referent_service.dart';

class ReferentInvoiceDetailScreen extends StatefulWidget {
  const ReferentInvoiceDetailScreen({super.key, required this.invoiceId});

  final int invoiceId;

  @override
  State<ReferentInvoiceDetailScreen> createState() => _ReferentInvoiceDetailScreenState();
}

class _ReferentInvoiceDetailScreenState extends State<ReferentInvoiceDetailScreen> {
  static final _numFr = NumberFormat('#,##0.00', 'fr_FR');

  final _service = MedecinReferentService.instance;
  Map<String, dynamic>? _invoice;
  bool _loading = true;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  /// Montants facture / devis : XAF (affichage FCFA).
  String _formatXaf(dynamic value) {
    if (value == null) return '—';
    final raw = value.toString().trim();
    if (raw.isEmpty) return '—';
    final n = num.tryParse(raw.replaceAll(RegExp(r'[\s\u00a0]'), '').replaceAll(',', '.'));
    if (n == null) return raw;
    return '${_numFr.format(n)} FCFA';
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _service.fetchInvoice(widget.invoiceId);
      if (!mounted) return;
      setState(() {
        _invoice = data;
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

  bool get _canValidateMedical {
    final inv = _invoice;
    if (inv == null) return false;
    final st = inv['statut']?.toString();
    final vm = inv['validation_medicale']?.toString();
    if (st != 'pending_medical') return false;
    if (vm == 'approved' || vm == 'rejected') return false;
    return true;
  }

  Future<void> _submit(bool approve) async {
    final controller = TextEditingController();
    final notes = await showDialog<String?>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(approve ? 'Valider médicalement' : 'Refuser la facture'),
        content: TextField(
          controller: controller,
          decoration: InputDecoration(
            hintText: approve ? 'Commentaire (optionnel)' : 'Motif du refus',
          ),
          maxLines: 3,
          autofocus: true,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Confirmer'),
          ),
        ],
      ),
    );
    if (!mounted || notes == null) return;

    setState(() => _busy = true);
    try {
      await _service.validateInvoiceMedical(
        widget.invoiceId,
        approve: approve,
        notes: notes.isEmpty ? null : notes,
      );
      if (!mounted) return;
      if (approve) {
        context.go('/referent?tab=2&sub=1');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Facture refusée.'),
            backgroundColor: Colors.orange.shade800,
          ),
        );
        await _load();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kMhContentBackground,
      appBar: AppBar(
        title: const Text('Facture'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? SafeArea(
                  top: false,
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(_error!, textAlign: TextAlign.center),
                          const SizedBox(height: 16),
                          FilledButton(onPressed: _load, child: const Text('Réessayer')),
                        ],
                      ),
                    ),
                  ),
                )
              : SafeArea(top: false, child: _buildContent()),
    );
  }

  Widget _buildContent() {
    final inv = _invoice!;
    final items = inv['items'];
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(
        16,
        16,
        16,
        16 + MediaQuery.viewPaddingOf(context).bottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            inv['numero_facture']?.toString() ?? '',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 8),
          Text('Montant HT : ${_formatXaf(inv['montant_ht'])}'),
          Text('TVA : ${_formatXaf(inv['montant_tva'])}'),
          Text('TTC : ${_formatXaf(inv['montant_ttc'])}', style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Text('Statut : ${inv['statut']}'),
          Text('Validation médicale : ${inv['validation_medicale'] ?? '—'}'),
          const Divider(height: 32),
          const Text('Lignes', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          const SizedBox(height: 8),
          if (items is List && items.isNotEmpty)
            ...items.map<Widget>((raw) {
              if (raw is! Map) return const SizedBox.shrink();
              final line = Map<String, dynamic>.from(raw);
              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  title: Text(line['libelle']?.toString() ?? ''),
                  subtitle: Text(
                    'Qté ${line['quantite']} × ${_formatXaf(line['prix_unitaire'])} HT → ${_formatXaf(line['montant_ttc'])} TTC',
                  ),
                ),
              );
            })
          else
            const Text('Aucune ligne détaillée.'),
          const SizedBox(height: 24),
          if (_canValidateMedical) ...[
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _busy ? null : () => _submit(true),
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('Valider (médical)'),
                    style: FilledButton.styleFrom(backgroundColor: AppColors.success),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy ? null : () => _submit(false),
                    icon: const Icon(Icons.cancel_outlined),
                    label: const Text('Refuser'),
                  ),
                ),
              ],
            ),
          ],
          if (_busy) const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator())),
        ],
      ),
    );
  }
}
