import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_colors.dart';
import '../../models/referent_pipeline.dart';
import '../../services/medecin_referent_service.dart';

/// Détail d'une alerte + sinistre : validation urgence, rapport séjour, lien facture.
class ReferentDossierDetailScreen extends StatefulWidget {
  const ReferentDossierDetailScreen({super.key, required this.alerteId});

  final int alerteId;

  @override
  State<ReferentDossierDetailScreen> createState() => _ReferentDossierDetailScreenState();
}

class _ReferentDossierDetailScreenState extends State<ReferentDossierDetailScreen> {
  final _service = MedecinReferentService.instance;
  Map<String, dynamic>? _alerte;
  Map<String, dynamic>? _sinistre;
  bool _loading = true;
  bool _sinistreLoading = false;
  String? _error;
  bool _actionBusy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<Map<String, dynamic>?> _fetchSinistreOptional() async {
    try {
      return await _service.fetchSinistreByAlerte(widget.alerteId);
    } catch (_) {
      return null;
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _sinistre = null;
      _sinistreLoading = false;
    });
    try {
      Map<String, dynamic>? alerteResult;
      Map<String, dynamic>? sinistreResult;
      await Future.wait<void>([
        _service.fetchAlerte(widget.alerteId).then((a) => alerteResult = a),
        _fetchSinistreOptional().then((s) => sinistreResult = s),
      ]);
      if (!mounted) return;
      setState(() {
        _alerte = alerteResult;
        _sinistre = sinistreResult;
        _loading = false;
        _sinistreLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
        _sinistreLoading = false;
      });
    }
  }

  /// Mise à jour sans écran de chargement plein (ex. après refus).
  Future<void> _refreshDataLight() async {
    Map<String, dynamic>? alerteResult;
    Map<String, dynamic>? sinistreResult;
    try {
      await Future.wait<void>([
        _service.fetchAlerte(widget.alerteId).then((a) => alerteResult = a),
        _fetchSinistreOptional().then((s) => sinistreResult = s),
      ]);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
      return;
    }
    if (!mounted) return;
    setState(() {
      _alerte = alerteResult;
      _sinistre = sinistreResult;
    });
  }

  Map<String, dynamic>? get _stay {
    final s = _sinistre?['hospital_stay'];
    if (s is Map) return Map<String, dynamic>.from(s);
    return null;
  }

  Map<String, dynamic>? get _invoice {
    final inv = _stay?['invoice'];
    if (inv is Map) return Map<String, dynamic>.from(inv);
    return null;
  }

  bool get _canVerifyUrgence {
    if (_alerte == null || _sinistreLoading || _sinistre == null) return false;
    return getReferentStep(_alerte!, _sinistre) == ReferentPipelineStep.sinistre;
  }

  bool get _canValidateReport {
    final stay = _stay;
    if (stay == null) return false;
    final st = (stay['status'] as String?)?.toLowerCase();
    return st == 'awaiting_validation';
  }

  Future<void> _decisionUrgence(bool approve) async {
    final sinistreId = _sinistre?['id'] as int?;
    if (sinistreId == null) return;
    final notes = await _promptNotes(
      title: approve ? 'Valider l\'urgence' : 'Refuser l\'urgence',
      hint: approve ? 'Commentaire (optionnel)' : 'Motif du refus',
    );
    if (!mounted) return;
    if (notes == null) return;
    setState(() => _actionBusy = true);
    try {
      await _service.verifyUrgence(
        sinistreId,
        approve: approve,
        notes: notes.isEmpty ? null : notes,
      );
      if (!mounted) return;
      if (approve) {
        context.go('/referent?tab=0&sub=1');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Urgence refusée.'),
            backgroundColor: Colors.orange.shade800,
          ),
        );
        await _refreshDataLight();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _actionBusy = false);
    }
  }

  Future<void> _decisionRapport(bool approve) async {
    final stayId = _stay?['id'] as int?;
    if (stayId == null) return;
    final notes = await _promptNotes(
      title: approve ? 'Valider le rapport' : 'Refuser le rapport',
      hint: approve ? 'Commentaire (optionnel)' : 'Motif du refus',
    );
    if (!mounted) return;
    if (notes == null) return;
    setState(() => _actionBusy = true);
    try {
      await _service.validateHospitalStayReport(
        stayId,
        approve: approve,
        notes: notes.isEmpty ? null : notes,
      );
      if (!mounted) return;
      if (approve) {
        context.go('/referent?tab=1&sub=1');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Rapport refusé.'),
            backgroundColor: Colors.orange.shade800,
          ),
        );
        await _refreshDataLight();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString()), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) setState(() => _actionBusy = false);
    }
  }

  /// Retourne la note saisie, éventuellement vide ; `null` si annulation.
  Future<String?> _promptNotes({required String title, required String hint}) async {
    final controller = TextEditingController();
    final result = await showDialog<String?>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          decoration: InputDecoration(hintText: hint),
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
    return result;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dossier sinistre'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loading || _sinistreLoading || _actionBusy ? null : _load,
          ),
        ],
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
              : SafeArea(
                  top: false,
                  child: SingleChildScrollView(
                    padding: EdgeInsets.fromLTRB(
                      16,
                      16,
                      16,
                      16 + MediaQuery.viewPaddingOf(context).bottom,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _sectionCard(
                        'Alerte',
                        [
                          _kv('N°', _alerte?['numero_alerte']?.toString()),
                          _kv('Statut', _alerte?['statut']?.toString()),
                          _kv('Priorité', _alerte?['priorite']?.toString()),
                          _kv('Adresse', _alerte?['adresse']?.toString()),
                          _kv('Description', _alerte?['description']?.toString()),
                        ],
                      ),
                      if (_sinistreLoading)
                        const Card(
                          child: Padding(
                            padding: EdgeInsets.all(20),
                            child: Row(
                              children: [
                                SizedBox(
                                  width: 24,
                                  height: 24,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                ),
                                SizedBox(width: 16),
                                Expanded(child: Text('Chargement du sinistre…')),
                              ],
                            ),
                          ),
                        )
                      else if (_sinistre != null) ...[
                        _sectionCard(
                          'Sinistre',
                          [
                            _kv('N° sinistre', _sinistre!['numero_sinistre']?.toString() ?? '—'),
                            _kv('Statut', _sinistre!['statut']?.toString()),
                            _kv('Médecin réf. (dossier)', _sinistre!['medecin_referent_nom']?.toString()),
                          ],
                        ),
                        _hospitalCard(),
                        _patientCard(),
                        if (_stay != null) _stayCard(),
                        if (_invoice != null) _invoiceCard(),
                      ] else
                        const Card(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: Text('Aucun sinistre rattaché à cette alerte.'),
                          ),
                        ),
                      const SizedBox(height: 24),
                      if (_canVerifyUrgence) ...[
                        Text(
                          'Décision urgence',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: FilledButton.icon(
                                onPressed: _actionBusy ? null : () => _decisionUrgence(true),
                                icon: const Icon(Icons.check_circle_outline),
                                label: const Text('Valider l\'urgence'),
                                style: FilledButton.styleFrom(
                                  backgroundColor: AppColors.success,
                                ),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: OutlinedButton.icon(
                                onPressed: _actionBusy ? null : () => _decisionUrgence(false),
                                icon: const Icon(Icons.cancel_outlined),
                                label: const Text('Refuser'),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                      ],
                      if (_canValidateReport) ...[
                        Text(
                          'Rapport hospitalier',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: FilledButton.icon(
                                onPressed: _actionBusy ? null : () => _decisionRapport(true),
                                icon: const Icon(Icons.verified_outlined),
                                label: const Text('Valider le rapport'),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: OutlinedButton.icon(
                                onPressed: _actionBusy ? null : () => _decisionRapport(false),
                                icon: const Icon(Icons.undo),
                                label: const Text('Refuser'),
                              ),
                            ),
                          ],
                        ),
                      ],
                      if (_actionBusy)
                        const Padding(
                          padding: EdgeInsets.only(top: 24),
                          child: Center(child: CircularProgressIndicator()),
                        ),
                    ],
                  ),
                ),
                ),
    );
  }

  Widget _sectionCard(String title, List<Widget> children) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const Divider(height: 20),
            ...children,
          ],
        ),
      ),
    );
  }

  Widget _kv(String k, String? v) {
    if (v == null || v.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              k,
              style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
            ),
          ),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 14))),
        ],
      ),
    );
  }

  Widget _hospitalCard() {
    final h = _sinistre?['hospital'];
    if (h is! Map) return const SizedBox.shrink();
    final m = Map<String, dynamic>.from(h);
    return _sectionCard(
      'Hôpital',
      [
        _kv('Nom', m['nom']?.toString()),
        _kv('Ville', m['ville']?.toString()),
        _kv('Téléphone', m['telephone']?.toString()),
        _kv('Adresse', m['adresse']?.toString()),
      ],
    );
  }

  Widget _patientCard() {
    final p = _sinistre?['patient'];
    if (p is! Map) return const SizedBox.shrink();
    final m = Map<String, dynamic>.from(p);
    return _sectionCard(
      'Patient',
      [
        _kv('Nom', m['full_name']?.toString()),
        _kv('Email', m['email']?.toString()),
      ],
    );
  }

  Widget _stayCard() {
    final s = _stay!;
    final actes = s['report_actes'];
    final exams = s['report_examens'];
    return _sectionCard(
      'Séjour hospitalier',
      [
        _kv('Statut séjour', s['status']?.toString()),
        _kv('Rapport', s['report_status']?.toString()),
        _kv('Motif consultation', s['report_motif_consultation']?.toString()),
        _kv('Motif hosp.', s['report_motif_hospitalisation']?.toString()),
        _kv('Durée (h)', s['report_duree_sejour_heures']?.toString()),
        _kv('Résumé', s['report_resume']?.toString()),
        _kv('Observations', s['report_observations']?.toString()),
        if (actes is List && actes.isNotEmpty)
          _kv('Actes', actes.map((e) => e.toString()).join(', ')),
        if (exams is List && exams.isNotEmpty)
          _kv('Examens', exams.map((e) => e.toString()).join(', ')),
      ],
    );
  }

  Widget _invoiceCard() {
    final inv = _invoice!;
    final pending = inv['validation_medicale']?.toString() == 'pending';
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Facture',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            const Divider(height: 20),
            _kv('N°', inv['numero_facture']?.toString()),
            _kv('Montant TTC', inv['montant_ttc']?.toString()),
            _kv('Statut', inv['statut']?.toString()),
            _kv('Validation médicale', inv['validation_medicale']?.toString()),
            if (pending) ...[
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: () {
                  final raw = inv['id'];
                  final id = raw is int ? raw : (raw is num ? raw.toInt() : null);
                  if (id != null) {
                    context.push('/referent/facture/$id');
                  }
                },
                icon: const Icon(Icons.receipt_long),
                label: const Text('Ouvrir pour validation médicale'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
