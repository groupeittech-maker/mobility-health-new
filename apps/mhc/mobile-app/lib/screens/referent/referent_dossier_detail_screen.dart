import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/utils/json_value.dart';
import '../../models/referent_pipeline.dart';
import '../../services/medecin_referent_service.dart';
import '../../widgets/common/prompt_text_dialog.dart';
import '../../widgets/referent/referent_care_documents_section.dart';
import '../../widgets/referent/referent_certificat_deces_section.dart';
import '../../widgets/referent/referent_dossier_sections.dart';

/// Détail d'une alerte + sinistre : aligné sur hospital-alert-details.html (web).
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
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

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

  List<dynamic> get _workflowSteps {
    final steps = _sinistre?['workflow_steps'];
    if (steps is List) return steps;
    return [];
  }

  bool get _canVerifyUrgence {
    if (_alerte == null || _sinistre == null) return false;
    final step = _workflowSteps.cast<Map?>().firstWhere(
          (s) => s?['step_key'] == 'verification_urgence',
          orElse: () => null,
        );
    if (step != null) {
      final st = step['statut']?.toString();
      if (st == 'completed' || st == 'cancelled') return false;
    }
    return getReferentStep(_alerte!, _sinistre) == ReferentPipelineStep.sinistre;
  }

  bool get _canValidateReport {
    final stay = _stay;
    if (stay == null) return false;
    return (stay['status'] as String?)?.toLowerCase() == 'awaiting_validation';
  }

  bool get _canValidateInvoiceMedical {
    final inv = _invoice;
    if (inv == null) return false;
    final st = inv['statut']?.toString();
    final vm = inv['validation_medicale']?.toString();
    return st == 'pending_medical' && vm != 'approved' && vm != 'rejected';
  }

  Future<void> _decisionUrgence(bool approve) async {
    final sinistreId = parseJsonInt(_sinistre?['id']);
    if (sinistreId == null) return;
    final notes = await _promptNotes(
      title: approve ? 'Valider l\'urgence' : 'Refuser l\'urgence',
      hint: approve ? 'Commentaire (optionnel)' : 'Motif du refus',
    );
    if (!mounted || notes == null) return;
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
          SnackBar(content: const Text('Urgence refusée.'), backgroundColor: Colors.orange.shade800),
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
    final stayId = parseJsonInt(_stay?['id']);
    if (stayId == null) return;
    final notes = await _promptNotes(
      title: approve ? 'Valider le rapport' : 'Refuser le rapport',
      hint: approve ? 'Commentaire (optionnel)' : 'Motif du refus',
    );
    if (!mounted || notes == null) return;
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
          SnackBar(content: const Text('Rapport refusé.'), backgroundColor: Colors.orange.shade800),
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

  Future<void> _decisionInvoice(bool approve) async {
    final id = parseJsonInt(_invoice?['id']);
    if (id == null) return;
    final notes = await _promptNotes(
      title: approve ? 'Valider médicalement la facture' : 'Refuser la facture',
      hint: approve ? 'Commentaire (optionnel)' : 'Motif du refus',
    );
    if (!mounted || notes == null) return;
    setState(() => _actionBusy = true);
    try {
      await _service.validateInvoiceMedical(
        id,
        approve: approve,
        notes: notes.isEmpty ? null : notes,
      );
      if (!mounted) return;
      if (approve) {
        context.go('/referent?tab=2&sub=1');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: const Text('Facture refusée.'), backgroundColor: Colors.orange.shade800),
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

  Future<String?> _promptNotes({required String title, required String hint}) {
    return showPromptTextDialog(context, title: title, hint: hint);
  }

  String _formatDate(dynamic value) {
    if (value == null) return '—';
    final d = DateTime.tryParse(value.toString());
    if (d == null) return value.toString();
    return DateFormat('dd/MM/yyyy HH:mm').format(d.toLocal());
  }

  String? _gps() {
    final lat = formatJsonCoord(_alerte?['latitude']);
    final lng = formatJsonCoord(_alerte?['longitude']);
    if (lat == null || lng == null) return null;
    return '$lat, $lng';
  }

  String? _assignedDoctorName() {
    final doctor = _stay?['assigned_doctor'];
    if (doctor is Map) {
      return doctor['full_name']?.toString() ?? doctor['email']?.toString();
    }
    final id = _stay?['doctor_id'];
    return id != null ? 'Dr #$id' : null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kMhContentBackground,
      appBar: AppBar(
        title: const Text('Dossier sinistre'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loading || _actionBusy ? null : _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _errorView()
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
                            _kv('Créée le', _formatDate(_alerte?['created_at'])),
                            _kv('Statut', _alerte?['statut']?.toString()),
                            _kv('Priorité', _alerte?['priorite']?.toString()),
                            _kv('Adresse', _alerte?['adresse']?.toString()),
                            _kv('Coordonnées GPS', _gps()),
                            _kv('Description', _alerte?['description']?.toString()),
                          ],
                        ),
                        if (_sinistre != null) ...[
                          ReferentMedicalDecisionBanner(workflowSteps: _workflowSteps),
                          _sectionCard(
                            'Sinistre',
                            [
                              _kv('N° sinistre', _sinistre!['numero_sinistre']?.toString() ?? '—'),
                              _kv('Statut', _sinistre!['statut']?.toString()),
                              _kv('Souscription', _sinistre!['numero_souscription']?.toString() ??
                                  (_sinistre!['souscription_id'] != null
                                      ? 'Souscription #${_sinistre!['souscription_id']}'
                                      : null)),
                              _kv('Médecin référent', _sinistre!['medecin_referent_nom']?.toString()),
                              _kv('Agent sinistre', _sinistre!['agent_sinistre_nom']?.toString()),
                            ],
                          ),
                          _hospitalCard(),
                          ReferentPatientDossierSection(alerte: _alerte, sinistre: _sinistre),
                          if (_stay != null) _stayCard(),
                          if (_invoice != null) _invoiceCard(),
                          ReferentCertificatDecesSection(
                            sinistreId: parseJsonInt(_sinistre!['id'])!,
                            attachment: _sinistre!['certificat_deces'] is Map
                                ? Map<String, dynamic>.from(_sinistre!['certificat_deces'] as Map)
                                : null,
                            canUpload: false,
                            onChanged: _refreshDataLight,
                          ),
                          ReferentCareDocumentsSection(
                            sinistreId: parseJsonInt(_sinistre!['id'])!,
                            alerte: _alerte,
                            sinistre: _sinistre,
                            stay: _stay,
                            onChanged: _refreshDataLight,
                          ),
                        ] else
                          const Card(
                            child: Padding(
                              padding: EdgeInsets.all(16),
                              child: Text('Aucun sinistre rattaché à cette alerte.'),
                            ),
                          ),
                        const SizedBox(height: 16),
                        if (_canVerifyUrgence) _urgenceActions(),
                        if (_canValidateReport) _reportActions(),
                        if (_canValidateInvoiceMedical) _invoiceActions(),
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

  Widget _errorView() {
    return SafeArea(
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
    );
  }

  Widget _urgenceActions() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Décision urgence', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: _actionBusy ? null : () => _decisionUrgence(true),
                icon: const Icon(Icons.check_circle_outline),
                label: const Text('Valider l\'urgence'),
                style: FilledButton.styleFrom(backgroundColor: AppColors.success),
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
    );
  }

  Widget _reportActions() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Rapport hospitalier', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
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
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _invoiceActions() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Validation médicale facture', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: _actionBusy ? null : () => _decisionInvoice(true),
                icon: const Icon(Icons.check),
                label: const Text('Accorder'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _actionBusy ? null : () => _decisionInvoice(false),
                icon: const Icon(Icons.close),
                label: const Text('Refuser'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: () {
            final id = parseJsonInt(_invoice?['id']);
            if (id != null) context.push('/referent/facture/$id');
          },
          icon: const Icon(Icons.receipt_long),
          label: const Text('Voir le détail de la facture'),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _sectionCard(String title, List<Widget> children) {
    final visible = children.where((w) => w is! SizedBox).toList();
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const Divider(height: 20),
            ...visible,
          ],
        ),
      ),
    );
  }

  Widget _kv(String k, String? v) {
    if (v == null || v.isEmpty || v == '—') return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 130, child: Text(k, style: TextStyle(color: Colors.grey.shade700, fontSize: 13))),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 14))),
        ],
      ),
    );
  }

  Widget _hospitalCard() {
    final h = _sinistre?['hospital'];
    if (h is! Map) return const SizedBox.shrink();
    final m = Map<String, dynamic>.from(h);
    final location = [m['ville'], m['pays']].where((e) => e != null && e.toString().isNotEmpty).join(', ');
    return _sectionCard(
      'Hôpital',
      [
        _kv('Nom', m['nom']?.toString()),
        if (location.isNotEmpty) _kv('Localisation', location),
        _kv('Téléphone', m['telephone']?.toString()),
        _kv('Adresse', m['adresse']?.toString()),
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
        _kv('Médecin traitant (orientation)', _assignedDoctorName()),
        _kv('Service', s['service_concerne']?.toString()),
        _kv('Chambre', s['chambre']?.toString()),
        _kv('Motif consultation', s['report_motif_consultation']?.toString()),
        _kv('Motif hosp.', s['report_motif_hospitalisation']?.toString()),
        _kv('Durée (h)', s['report_duree_sejour_heures']?.toString()),
        _kv('Résumé', s['report_resume']?.toString()),
        _kv('Observations', s['report_observations']?.toString()),
        if (actes is List && actes.isNotEmpty) _kv('Actes', actes.map((e) => e.toString()).join(', ')),
        if (exams is List && exams.isNotEmpty) _kv('Examens', exams.map((e) => e.toString()).join(', ')),
      ],
    );
  }

  Widget _invoiceCard() {
    final inv = _invoice!;
    final pending = _canValidateInvoiceMedical;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Facture', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const Divider(height: 20),
            _kv('N°', inv['numero_facture']?.toString()),
            _kv('Montant TTC', inv['montant_ttc']?.toString()),
            _kv('Statut', inv['statut']?.toString()),
            _kv('Validation médicale', inv['validation_medicale']?.toString()),
            if (pending)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Validation médicale en attente — utilisez les boutons ci-dessous ou ouvrez le détail.',
                  style: TextStyle(fontSize: 13, color: Colors.orange.shade800),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
