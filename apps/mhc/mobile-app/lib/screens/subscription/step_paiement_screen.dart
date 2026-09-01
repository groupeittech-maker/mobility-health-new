import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

import '../../core/constants/app_colors.dart';
import '../../services/api_services.dart';

/// Étape 4 : Paiement – "Payer maintenant" appelle le backend pour confirmer le paiement
/// et générer l'attestation provisoire (une seule source, comme l'app web).
class StepPaiementScreen extends StatefulWidget {
  const StepPaiementScreen({
    super.key,
    required this.subscriptionId,
    required this.montant,
    this.primeAssurance,
    this.fraisServices,
    required this.onContinue,
  });

  final int subscriptionId;
  final double montant;
  final double? primeAssurance;
  final double? fraisServices;
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
        montant = subscription.primeAssurance! + subscription.fraisServices!;
      }
      if (montant <= 0) {
        throw Exception('Montant de paiement invalide pour cette souscription.');
      }
      await _paymentsService.confirm(
        subscriptionId: widget.subscriptionId,
        montant: montant,
        methodePaiement: _selectedMethod,
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
      color: const Color(0xFFE8F0F4),
      child: SingleChildScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: EdgeInsets.fromLTRB(20, 20, 20, mq.padding.bottom + mq.viewInsets.bottom + 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Paiement sécurisé',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: const Color(0xFF1E293B),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Vérifiez le récapitulatif puis choisissez le mode de paiement.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: const Color(0xFF64748B),
              ),
            ),
            const SizedBox(height: 16),
            // Résumé + Montant (comme web)
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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Montant total',
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
                      label: 'Prime d’assurance',
                      value: widget.primeAssurance!,
                    ),
                    const SizedBox(height: 6),
                    _PaiementLigneMontant(
                      label: 'Frais de services',
                      value: widget.fraisServices!,
                    ),
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
            // Mode de paiement (identique au web)
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
                onPressed: _loading ? null : _payNow,
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
                    : const Text('Payer maintenant'),
              ),
            ),
          ],
        ),
      ),
    );
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
