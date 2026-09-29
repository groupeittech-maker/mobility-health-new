import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_text_highlight.dart';
import '../../services/api_services.dart';

/// Étape 4 : Paiement – "Payer maintenant" appelle le backend pour confirmer le paiement
/// et générer l'attestation provisoire (une seule source, comme l'app web).
class StepPaiementScreen extends StatefulWidget {
  const StepPaiementScreen({
    super.key,
    required this.subscriptionId,
    required this.montant,
    this.primeAssurance,
    this.coutPolice,
    this.fraisServices,
    this.taxesTotal,
    this.taxes,
    this.age,
    this.recapAssureur,
    this.recapProduit,
    this.recapDestination,
    this.recapDates,
    this.recapAssure,
    this.recapLogoUrl,
    this.onDossierStateChanged,
    required this.onContinue,
  });

  final int subscriptionId;
  final double montant;
  final double? primeAssurance;
  final double? coutPolice;
  final double? fraisServices;
  final double? taxesTotal;
  final List<Map<String, dynamic>>? taxes;
  final int? age;
  /// Récapitulatif de souscription (kit) : assureur et logo, destination,
  /// dates, assuré — affiché avant le décompte et le paiement.
  final String? recapAssureur;
  final String? recapProduit;
  final String? recapDestination;
  final String? recapDates;
  final String? recapAssure;
  final String? recapLogoUrl;
  /// Notifie le parent quand le dossier passe en revue/approuvé/refusé —
  /// les étapes précédentes du formulaire sont alors verrouillées.
  final void Function(String? dossierState)? onDossierStateChanged;
  final VoidCallback onContinue;

  @override
  State<StepPaiementScreen> createState() => _StepPaiementScreenState();
}

/// Moyens de paiement (alignés sur le web payment-checkout.html)
const _paymentMethods = [
  MapEntry('carte_bancaire', 'Carte bancaire'),
  MapEntry('mobile_money_mtn', 'Mobile Money (MTN)'),
  MapEntry('mobile_money_orange', 'Mobile Money (Orange)'),
  MapEntry('virement', 'Virement bancaire'),
];

class _StepPaiementScreenState extends State<StepPaiementScreen> {
  final PaymentsService _paymentsService = PaymentsService();
  final SubscriptionsService _subscriptionsService = SubscriptionsService();
  bool _loading = false;
  String? _error;
  String _selectedMethod = 'carte_bancaire';
  /// Acceptation explicite des conditions (kit) : conditionne le passage
  /// au paiement (« Soumettre le dossier » reste bloqué tant qu'elle
  /// n'est pas cochée).
  bool _acceptConditions = false;

  /// État du dossier : to_submit | approved | in_review | refused
  String _dossierState = 'to_submit';
  List<String> _decisionReasons = const [];

  @override
  void initState() {
    super.initState();
    _syncDossierState();
  }

  /// Resynchronise l'état du dossier avec le statut serveur (ré-ouverture écran
  /// ou vérification manuelle — une revue humaine peut prendre plusieurs jours).
  Future<void> _syncDossierState({bool showFeedback = false}) async {
    try {
      final sub = await _subscriptionsService.getSubscription(widget.subscriptionId);
      if (!mounted) return;
      final previous = _dossierState;
      setState(() {
        if (sub.statut == 'en_attente_paiement') {
          _dossierState = 'approved';
        } else if (sub.statut == 'en_attente_validation') {
          _dossierState = 'in_review';
        } else if (sub.statut == 'refusee') {
          _dossierState = 'refused';
        }
      });
      widget.onDossierStateChanged?.call(_dossierState);
      if (showFeedback && _dossierState == 'in_review' && previous == 'in_review') {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Le dossier est toujours en cours de validation.'),
          ),
        );
      }
    } catch (e) {
      if (mounted && showFeedback) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Impossible de vérifier le statut pour le moment.')),
        );
      }
    }
  }

  /// « Soumettre le dossier » : le moteur de décision évalue le dossier.
  /// approve → le paiement devient disponible ; review → validation humaine ;
  /// reject → dossier refusé.
  Future<void> _submitDossier() async {
    setState(() {
      _loading = true;
      _error = null;
      _decisionReasons = const [];
    });
    try {
      final result = await _subscriptionsService.evaluateSubscription(
        widget.subscriptionId,
        voyageurAge: widget.age,
      );
      final decision = (result['decision'] ?? '').toString();
      final reasons = (result['reasons'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const <String>[];
      if (!mounted) return;
      setState(() {
        _loading = false;
        _decisionReasons = reasons;
        if (decision == 'approve') {
          _dossierState = 'approved';
        } else if (decision == 'review') {
          _dossierState = 'in_review';
        } else {
          _dossierState = 'refused';
        }
      });
      widget.onDossierStateChanged?.call(_dossierState);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e is Exception ? e.toString().replaceFirst('Exception: ', '') : e.toString();
      });
    }
  }

  /// Confirme le paiement côté backend : crée le paiement et l'attestation provisoire (comme le web).
  Future<void> _payNow() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final subscription = await _subscriptionsService.getSubscription(widget.subscriptionId);
      double montant = subscription.prixApplique > 0 ? subscription.prixApplique : widget.montant;
      if (montant <= 0 &&
          subscription.primeAssurance != null &&
          subscription.fraisServices != null) {
        montant = subscription.primeAssurance! +
            (subscription.coutPolice ?? 0) +
            subscription.fraisServices! +
            (subscription.taxesTotal ?? 0);
      }
      if (montant <= 0) {
        throw Exception('Montant de paiement invalide pour cette souscription.');
      }
      await _paymentsService.confirm(
        subscriptionId: widget.subscriptionId,
        montant: montant,
        methodePaiement: _selectedMethod,
        age: widget.age,
      );
      SubscriptionsService.clearSubscriptionsCache();
      AttestationsService.clearUserAttestationsCache();
      if (mounted) {
        setState(() => _loading = false);
        widget.onContinue();
      }
    } catch (e) {
      if (mounted) {
        String message = e is Exception ? e.toString().replaceFirst('Exception: ', '') : e.toString();
        if (e is DioException) {
          final detail = e.response?.data is Map<String, dynamic>
              ? (e.response?.data as Map<String, dynamic>)['detail']
              : null;
          if (detail is String && detail.trim().isNotEmpty) {
            message = detail;
          }
        }
        setState(() {
          _loading = false;
          _error = message;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);
    return Container(
      color: kMhContentBackground,
      child: SingleChildScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: EdgeInsets.fromLTRB(20, 20, 20, mq.padding.bottom + mq.viewInsets.bottom + 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const MHSectionTitle(
              title: 'Récapitulatif de souscription',
              subtitle: 'Vérifiez votre sélection avant de payer.',
            ),
            const SizedBox(height: 16),
            _buildRecapCard(),
            // Résumé + Montant (comme web)
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.surfaceCard,
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
                children: [
                  const Text(
                    'Décompte de la prime',
                    style: TextStyle(
                      fontSize: 14,
                      color: Color(0xFF64748B),
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (widget.primeAssurance != null &&
                      widget.fraisServices != null &&
                      widget.fraisServices! > 0) ...[
                    _PaiementLigneMontant(
                      label: 'Prime Nette',
                      value: widget.primeAssurance!,
                    ),
                    const SizedBox(height: 6),
                    _PaiementLigneMontant(
                      label: 'Coût de Police',
                      value: widget.coutPolice ?? 0,
                    ),
                    const SizedBox(height: 6),
                    _PaiementLigneMontant(
                      label: 'Taxe',
                      value: widget.fraisServices!,
                    ),
                    const SizedBox(height: 6),
                    ..._taxRows(),
                    const SizedBox(height: 10),
                    const Divider(height: 1),
                    const SizedBox(height: 8),
                  ],
                  Text(
                    '${widget.montant.toStringAsFixed(0)} XAF',
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: AppColors.primary,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            if (_dossierState == 'in_review') _buildReviewNotice(),
            if (_dossierState == 'refused') _buildRefusedNotice(),
            if (_dossierState == 'to_submit')
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(
                  color: AppColors.surfaceCard,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: CheckboxListTile(
                  value: _acceptConditions,
                  onChanged: (v) =>
                      setState(() => _acceptConditions = v ?? false),
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  activeColor: AppColors.primary,
                  title: const Text(
                    "J'ai lu et j'accepte les conditions générales et les exclusions.",
                    style: TextStyle(fontSize: 13, color: Color(0xFF1E293B)),
                  ),
                ),
              ),
            if (_dossierState == 'approved')
              // Mode de paiement (identique au web) — visible uniquement après approbation
              Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.surfaceCard,
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
                children: [
                  Text(
                    'Mode de paiement',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: const Color(0xFF1E293B),
                    ),
                  ),
                  const SizedBox(height: 12),
                  ..._paymentMethods.map((e) => RadioListTile<String>(
                    value: e.key,
                    groupValue: _selectedMethod,
                    onChanged: (v) => setState(() => _selectedMethod = v ?? e.key),
                    title: Text(e.value, style: const TextStyle(fontSize: 15)),
                    activeColor: AppColors.primary,
                  )),
                ],
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _error!,
                  style: const TextStyle(color: AppColors.danger, fontSize: 13),
                ),
              ),
            ],
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _loading
                    ? null
                    : (_dossierState == 'to_submit'
                        ? (_acceptConditions ? _submitDossier : null)
                        : _dossierState == 'approved' ? _payNow
                        : null),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: _loading
                    ? const SizedBox(
                        height: 24,
                        width: 24,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : Text(_dossierState == 'to_submit' ? 'Soumettre le dossier' : 'Payer maintenant'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// « Récapitulatif de souscription » (kit) : assureur/logo, destination,
  /// dates, assuré, montant.
  Widget _buildRecapCard() {
    final logo = widget.recapLogoUrl;
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceCard,
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
        children: [
          Row(
            children: [
              if (logo != null && logo.isNotEmpty)
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.network(
                    logo,
                    width: 52,
                    height: 52,
                    fit: BoxFit.contain,
                    errorBuilder: (_, __, ___) => _logoFallback(),
                  ),
                )
              else
                _logoFallback(),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.recapAssureur ?? 'Assureur MHC',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFF352A42),
                      ),
                    ),
                    if (widget.recapProduit != null)
                      Text(
                        widget.recapProduit!,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF64748B),
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                  ],
                ),
              ),
            ],
          ),
          const Divider(height: 24),
          _recapRow('Destination', widget.recapDestination),
          _recapRow('Dates', widget.recapDates),
          _recapRow('Assuré', widget.recapAssure),
          _recapRow(
            'Montant',
            '${widget.montant.toStringAsFixed(0)} XAF',
            valueBold: true,
          ),
        ],
      ),
    );
  }

  Widget _logoFallback() {
    return Container(
      width: 52,
      height: 52,
      decoration: BoxDecoration(
        color: const Color(0xFFEDE9FE),
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Icon(Icons.shield_outlined, color: Color(0xFF4E267C)),
    );
  }

  Widget _recapRow(String label, String? value, {bool valueBold = false}) {
    if (value == null || value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: TextStyle(
                fontSize: 12,
                color: const Color(0xFF1E293B),
                fontWeight: valueBold ? FontWeight.bold : FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReviewNotice() {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFFDBA74)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.hourglass_top, color: Color(0xFFEA580C)),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Dossier en cours de validation',
                  style: TextStyle(fontWeight: FontWeight.w700, color: Color(0xFF9A3412)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Votre dossier a été soumis à une validation humaine — cela peut prendre '
            'plusieurs jours le temps de l\'enquête. Vous serez informé dès qu\'il '
            'est approuvé : le paiement sera alors disponible et vous pourrez '
            'reprendre ici.',
            style: TextStyle(fontSize: 13, color: Color(0xFF7C2D12)),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => _syncDossierState(showFeedback: true),
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Vérifier le statut'),
              style: TextButton.styleFrom(
                foregroundColor: const Color(0xFF9A3412),
                padding: EdgeInsets.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ),
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => context.go('/home?tab=2'),
              icon: const Icon(Icons.history, size: 18),
              label: const Text('Voir dans l\'historique'),
              style: TextButton.styleFrom(
                foregroundColor: const Color(0xFF9A3412),
                padding: EdgeInsets.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ),
          ),
          if (_decisionReasons.isNotEmpty) ...[
            const SizedBox(height: 8),
            ..._decisionReasons.map((r) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('• $r', style: const TextStyle(fontSize: 12, color: Color(0xFF7C2D12))),
                )),
          ],
        ],
      ),
    );
  }

  Widget _buildRefusedNotice() {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.danger.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.danger.withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.cancel_outlined, color: AppColors.danger),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Dossier refusé',
                  style: TextStyle(fontWeight: FontWeight.w700, color: AppColors.danger),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Votre dossier ne peut pas donner lieu à une souscription. '
            'Contactez le service client pour plus d\'informations.',
            style: TextStyle(fontSize: 13, color: Color(0xFF7F1D1D)),
          ),
          if (_decisionReasons.isNotEmpty) ...[
            const SizedBox(height: 8),
            ..._decisionReasons.map((r) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('• $r', style: const TextStyle(fontSize: 12, color: Color(0xFF7F1D1D))),
                )),
          ],
        ],
      ),
    );
  }

  List<Widget> _taxRows() {
    final rows = <Widget>[];
    if (widget.taxesTotal != null && widget.taxesTotal! > 0) {
      for (final t in widget.taxes ?? []) {
        final nom = t['nom']?.toString() ?? 'Taxe';
        final montant = (t['montant'] as num?)?.toDouble() ?? 0;
        if (montant > 0) {
          rows.add(_PaiementLigneMontant(label: 'Taxe additionnelle ($nom)', value: montant));
          rows.add(const SizedBox(height: 6));
        }
      }
    }
    return rows;
  }
}

class _PaiementLigneMontant extends StatelessWidget {
  const _PaiementLigneMontant({required this.label, required this.value});

  final String label;
  final double value;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
        ),
        Text(
          '${value.toStringAsFixed(0)} XAF',
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFF1E293B)),
        ),
      ],
    );
  }
}
