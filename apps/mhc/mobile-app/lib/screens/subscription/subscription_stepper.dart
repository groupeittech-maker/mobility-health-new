import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

/// Stepper 5 étapes (aligné frontend) : Voyage, Produit, Médical, Paiement, Attestation.
class SubscriptionStepper extends StatelessWidget {
  const SubscriptionStepper({
    super.key,
    required this.currentStep,
  });

  final int currentStep;

  static const steps = ['Voyage', 'Produit', 'Médical', 'Paiement', 'Attestation'];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
      child: Row(
        children: List.generate(steps.length * 2 - 1, (i) {
          if (i.isOdd) {
            return Expanded(
              child: Container(
                height: 2,
                margin: const EdgeInsets.only(bottom: 20),
                color: (i ~/ 2) + 1 <= currentStep
                    ? AppColors.primary
                    : const Color(0xFFE2E8F0),
              ),
            );
          }
          final stepIndex = i ~/ 2;
          final isCompleted = stepIndex + 1 < currentStep;
          final isActive = stepIndex + 1 == currentStep;
          return Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isCompleted
                      ? AppColors.primary
                      : isActive
                          ? AppColors.primary
                          : const Color(0xFFE2E8F0),
                ),
                child: isCompleted
                    ? const Icon(Icons.check, color: Colors.white, size: 18)
                    : Center(
                        child: Text(
                          '${stepIndex + 1}',
                          style: TextStyle(
                            color: isActive ? Colors.white : const Color(0xFF64748B),
                            fontWeight: FontWeight.w600,
                            fontSize: 12,
                          ),
                        ),
                      ),
              ),
              const SizedBox(height: 4),
              Text(
                steps[stepIndex],
                style: TextStyle(
                  fontSize: 10,
                  color: isActive || isCompleted
                      ? AppColors.primary
                      : const Color(0xFF64748B),
                  fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
            ],
          );
        }),
      ),
    );
  }
}
