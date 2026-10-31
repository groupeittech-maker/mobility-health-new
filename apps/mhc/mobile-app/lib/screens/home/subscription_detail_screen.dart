import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:open_filex/open_filex.dart';

import '../../core/widgets/mh_surface_card.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../models/medecin_conseil.dart';
import '../../models/subscription.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';
import '../../services/ekyc_session_service.dart';
import '../../services/medecin_conseil_service.dart';
import '../../widgets/medecin_conseil_card.dart';
import 'policy_actions_section.dart';
import '../pdf_viewer_screen.dart';
import '../subscription/step_paiement_screen.dart';
import '../../core/utils/api_error_helper.dart';

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
  final MedecinConseilService _medecinConseilService = MedecinConseilService();
  late SubscriptionModel _subscription;
  List<Map<String, dynamic>> _attestations = [];
  List<MedecinConseilAssignment> _medecinConseil = [];
  bool _medecinConseilFromCache = false;
  EkycSession? _ekycSession;
  Map<String, dynamic>? _user;
  bool _loading = true;
  String? _error;
  String? _downloadingId; // 'pdf-{id}' ou 'ecard-{id}'
  bool _evaluating = false;

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
      // Recharger la souscription : le statut peut avoir évolué (paiement,
      // décision automatique, suspension…) — sinon l'écran reste figé sur
      // l'ancien statut après un retour de paiement.
      try {
        _subscription =
            await _subscriptionsService.getSubscription(_subscription.id);
      } catch (_) {}
      final att = await _attestationsService.getSubscriptionAttestations(_subscription.id);
      // Souscription voyage : la session eKYC (auto-créée par le backend)
      // pilote le CTA « Vérifier mon identité » — jamais bloquant si
      // l'endpoint est indisponible.
      if (_subscription.projetVoyageId != null) {
        try {
          _ekycSession = await EkycSessionService.instance
              .getLatestForSouscription(_subscription.id);
        } catch (_) {}
      }
      final cachedConseil = await _medecinConseilService.loadCached();
      final cachedForSub = cachedConseil
          .where((item) => item.souscriptionId == _subscription.id)
          .toList();
      List<MedecinConseilAssignment> conseil = cachedForSub;
      var conseilFromCache = cachedForSub.isNotEmpty;
      try {
        conseil = await _medecinConseilService.refresh(souscriptionId: _subscription.id);
        conseilFromCache = false;
      } catch (_) {
        // Hors ligne : on conserve le cache local.
      }
      if (!mounted) return;
      setState(() {
        _user = userMap;
        _attestations = att;
        _medecinConseil = conseil;
        _medecinConseilFromCache = conseilFromCache;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = apiErrorToUserMessage(e);
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
            content: Text('Erreur : ${apiErrorToUserMessage(e)}'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _downloadingId = null);
    }
  }

  void _showErrorSnackBar(Object e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Erreur : ${apiErrorToUserMessage(e)}'),
        backgroundColor: AppColors.danger,
      ),
    );
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
            content: Text('Erreur : ${apiErrorToUserMessage(e)}'),
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
    final s = _subscription;
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    final isResiliee = s.statut == 'resiliee';

    if (isResiliee) {
      return Scaffold(
        backgroundColor: kMhContentBackground,
        appBar: AppBar(
          title: const Text('Détail souscription'),
          backgroundColor: AppColors.cardBg,
          foregroundColor: const Color(0xFF1E293B),
          elevation: 0,
        ),
        // Police annulée : plus de garanties, mais l'avenant d'annulation et le
        // suivi du remboursement restent consultables.
        body: ListView(
          padding: EdgeInsets.fromLTRB(24, 32, 24, bottomPadding),
          children: [
            Icon(Icons.block, size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 20),
            Text(
              'Police annulée',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: const Color(0xFF1E293B),
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            Text(
              'Aucune garantie ne peut plus être activée au titre de cette police.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: const Color(0xFF64748B),
              ),
              textAlign: TextAlign.center,
            ),
            PolicyActionsSection(subscription: s, onChanged: _load),
          ],
        ),
      );
    }

    return Scaffold(
      backgroundColor: kMhContentBackground,
      appBar: AppBar(
        title: const Text('Détail souscription'),
        backgroundColor: AppColors.cardBg,
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
                    if (s.projetVoyage != null)
                      _row('Destination',
                          s.projetVoyage!.destinationDisplay ?? s.projetVoyage!.destination),
                    _row('Début', _formatDate(s.dateDebut)),
                    _row('Fin', _formatDate(s.dateFin)),
                    _row('Prix', '${s.prixApplique.toStringAsFixed(0)} XAF'),
                  ]),
                  if (s.statut == 'en_attente' || s.statut == 'en_attente_paiement')
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: _pendingDossierCard(s),
                    ),
                  if (s.projetVoyageId != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: _ekycCard(s),
                    ),
                  if (s.infoDemandeeMessage != null &&
                      s.infoDemandeeMessage!.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: _infoRequestCard(s),
                    ),
                  const SizedBox(height: 20),
                  MedecinConseilCard(
                    assignments: _medecinConseil,
                    fromCache: _medecinConseilFromCache,
                  ),
                  PolicyActionsSection(
                    subscription: s,
                    onChanged: _load,
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
                                'Annulation en cours de traitement.',
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

  /// Carte eKYC sur souscription voyage : visible tant que la dernière
  /// session n'est pas VERIFIED (ou si aucune session n'existe encore) —
  /// la session auto-créée par le backend est reprise par le CTA.
  Widget _ekycCard(SubscriptionModel s) {
    final verified = _ekycSession?.isVerified == true;
    if (verified) {
      return MHSurfaceCard(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(Icons.verified_user, color: Colors.green.shade600),
            const SizedBox(width: 10),
            const Expanded(
              child: Text('Identité vérifiée (eKYC)',
                  style: TextStyle(fontWeight: FontWeight.w500)),
            ),
          ],
        ),
      );
    }
    final status = _ekycSession?.status;
    return MHSurfaceCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.badge_outlined, color: AppColors.secondary),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Vérification d\'identité requise',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            status == 'REVIEW' || status == 'REJECTED'
                ? 'Votre vérification est en revue manuelle — vous serez notifié du résultat.'
                : 'Votre souscription nécessite une vérification d\'identité. Quelques minutes suffisent.',
            style: const TextStyle(fontSize: 13, color: Color(0xFF64748B), height: 1.4),
          ),
          if (status != 'REVIEW' && status != 'REJECTED') ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => context
                    .push('/ekyc-verification?subscription=${s.id}')
                    .then((_) => _load()),
                icon: const Icon(Icons.verified_user_outlined, size: 18),
                label: Text(
                  _ekycSession == null
                      ? 'Vérifier mon identité (eKYC)'
                      : 'Reprendre la vérification',
                ),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.secondary,
                  side: const BorderSide(color: AppColors.secondary),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// Carte « dossier à finaliser » : un dossier resté en_attente (soumission
  /// interrompue côté réseau) peut être re-soumis au moteur de décision, puis
  /// payé — sinon il restait bloqué sans possibilité de reprise.
  Widget _pendingDossierCard(SubscriptionModel s) {
    final awaitingPayment = s.statut == 'en_attente_paiement';
    return MHSurfaceCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.pending_actions, color: Colors.orange.shade700),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  awaitingPayment
                      ? 'Dossier approuvé — reste à payer'
                      : 'Dossier non encore soumis à décision',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: AppColors.secondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            awaitingPayment
                ? 'Votre dossier a été accepté automatiquement. Finalisez le paiement pour obtenir votre attestation.'
                : 'La soumission a été interrompue (connexion). Renvoyez le dossier pour décision automatique.',
            style: const TextStyle(fontSize: 13, color: Color(0xFF64748B), height: 1.4),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => context.push('/ekyc-verification?subscription=${s.id}'),
              icon: const Icon(Icons.verified_user_outlined, size: 18),
              label: const Text('Vérifier mon identité (eKYC)'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.secondary,
                side: const BorderSide(color: AppColors.secondary),
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _evaluating
                  ? null
                  : (awaitingPayment ? _goToPayment : _submitForDecision),
              icon: _evaluating
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : Icon(awaitingPayment ? Icons.payment : Icons.send, size: 18),
              label: Text(
                _evaluating
                    ? 'Décision en cours…'
                    : (awaitingPayment
                        ? 'Procéder au paiement'
                        : 'Soumettre pour décision'),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.secondary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Carte « MHC vous demande des précisions » (§4.2) : réponse sous 48 h,
  /// faute de quoi le dossier est refusé automatiquement.
  Widget _infoRequestCard(SubscriptionModel s) {
    return MHSurfaceCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.help_outline, color: Colors.orange.shade700),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(
                  'MHC vous demande des précisions',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: AppColors.secondary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            s.infoDemandeeMessage!,
            style: const TextStyle(fontSize: 13, color: Color(0xFF334155), height: 1.4),
          ),
          const SizedBox(height: 6),
          const Text(
            'Répondez sous 48 h : sans réponse, votre dossier sera refusé automatiquement.',
            style: TextStyle(fontSize: 12, color: Color(0xFF64748B), height: 1.4),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _evaluating ? null : () => _replyToInfoRequest(s),
              icon: const Icon(Icons.reply, size: 18),
              label: const Text('Répondre'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.secondary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _replyToInfoRequest(SubscriptionModel s) async {
    final ctrl = TextEditingController();
    final reponse = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Votre réponse'),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          maxLines: 4,
          decoration: const InputDecoration(
            hintText: 'Précisez les informations demandées…',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
          FilledButton(
            onPressed: () {
              final v = ctrl.text.trim();
              if (v.isNotEmpty) Navigator.pop(ctx, v);
            },
            child: const Text('Envoyer'),
          ),
        ],
      ),
    );
    ctrl.dispose();
    if (reponse == null) return;
    setState(() => _evaluating = true);
    try {
      await _subscriptionsService.submitInfoResponse(s.id, reponse);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Réponse transmise à MHC.'),
        backgroundColor: AppColors.success,
      ));
      await _load();
    } catch (e) {
      if (mounted) _showErrorSnackBar(e);
    } finally {
      if (mounted) setState(() => _evaluating = false);
    }
  }

  Future<void> _submitForDecision() async {
    setState(() {
      _evaluating = true;
      _error = null;
    });
    try {
      final result =
          await _subscriptionsService.evaluateSubscription(_subscription.id);
      if (!mounted) return;
      // Recharger la souscription complète — le statut peut avoir changé
      // (approve → en_attente_paiement, review → en_attente_validation…).
      try {
        _subscription =
            await _subscriptionsService.getSubscription(_subscription.id);
      } catch (_) {}
      if (!mounted) return;
      setState(() => _evaluating = false);
      final decision = (result['decision'] ?? '').toString();
      if (decision == 'approve') {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Dossier accepté automatiquement — vous pouvez payer.'),
            backgroundColor: AppColors.success,
          ),
        );
      } else if (decision == 'review') {
        final steps = (result['review_steps'] as List?)?.join(', ') ?? '';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Dossier en revue ($steps). Vous serez notifié.'),
          ),
        );
      } else if (decision == 'reject') {
        final reasons = (result['reasons'] as List?)?.join(' ') ?? '';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Dossier refusé. $reasons'),
            backgroundColor: AppColors.danger,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _evaluating = false;
          _error = apiErrorToUserMessage(e);
        });
      }
    }
  }

  void _goToPayment() {
    final s = _subscription;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: const Text('Paiement')),
          body: StepPaiementScreen(
            subscriptionId: s.id,
            montant: s.prixApplique,
            recapProduit: s.produitAssurance?.nom,
            recapAssure: _user?['display_name'],
            onContinue: () {
              Navigator.of(context).pop();
              _load();
            },
          ),
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
    return MHSurfaceCard(
      padding: const EdgeInsets.all(16),
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
