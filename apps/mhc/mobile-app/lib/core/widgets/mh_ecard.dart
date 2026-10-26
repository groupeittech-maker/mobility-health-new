import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../constants/app_colors.dart';

/// Fond officiel de l'e-carte et logo blanc MHC (charte V3).
const String kMhEcardBackground = 'assets/images/fond_carte_mhc.jpg';
const String kMhLogoWhite = 'assets/images/logo_mhc_blanc.png';

/// E-carte MyMHC : fond de carte officiel MHC pour l'adulte (turquoise
/// pour un mineur), logo blanc, portrait en bas à droite.
class MhEcard extends StatelessWidget {
  const MhEcard({
    super.key,
    required this.holderName,
    this.policyNumber,
    this.validityLabel,
    this.isChild = false,
    this.photoBytes,
    this.photoUrl,
  });

  final String holderName;
  final String? policyNumber;
  /// Période de validité, ex. « Du 02/11/2026 au 16/11/2026 »
  /// (voir [MhEcard.validityRange]).
  final String? validityLabel;
  final bool isChild;
  final Uint8List? photoBytes;
  final String? photoUrl;

  static String _fmt(DateTime d) =>
      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  /// Libellé « Du … au … » identique à l'attestation d'assurance.
  static String? validityRange(DateTime? from, DateTime? to) {
    if (from == null && to == null) return null;
    if (from == null) return 'Jusqu’au ${_fmt(to!)}';
    if (to == null) return 'Dès le ${_fmt(from)}';
    return 'Du ${_fmt(from)} au ${_fmt(to)}';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 170,
      decoration: BoxDecoration(
        gradient: isChild
            ? const LinearGradient(
                colors: [AppColors.brandTeal, Color(0xFF06767F)],
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
              )
            : null,
        color: isChild ? null : AppColors.brandPurple,
        image: isChild
            ? null
            : const DecorationImage(
                image: AssetImage(kMhEcardBackground),
                fit: BoxFit.cover,
              ),
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: (isChild ? AppColors.brandTeal : AppColors.brandPurple)
                .withValues(alpha: 0.35),
            blurRadius: 14,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'STANDARD',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 10,
                        letterSpacing: 2,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (isChild) ...[
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.85),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.person_outline,
                                size: 12, color: AppColors.brandTeal),
                            SizedBox(width: 3),
                            Text(
                              'Mineur',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                color: AppColors.brandTeal,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const Spacer(),
                    _MiniLogo(),
                  ],
                ),
                const Spacer(),
                Text(
                  holderName.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.4,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Police N°  ${policyNumber ?? 'À attribuer'}\n'
                  'Validité  ${validityLabel ?? 'À confirmer'}',
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 10,
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
          Positioned(
            right: 14,
            bottom: 12,
            child: Container(
              width: 52,
              height: 64,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.25),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.white38),
              ),
              clipBehavior: Clip.antiAlias,
              child: photoBytes != null
                  ? Image.memory(
                      photoBytes!,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => _photoPlaceholder(),
                    )
                  : photoUrl != null
                      ? Image.network(
                          photoUrl!,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => _photoPlaceholder(),
                        )
                      : _photoPlaceholder(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _photoPlaceholder() {
    return const Center(
      child: Icon(Icons.person, color: Colors.white70, size: 30),
    );
  }
}

class _MiniLogo extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: 0.95,
      child: Image.asset(
        kMhLogoWhite, // logo blanc MHC (charte V3)
        height: 24,
        fit: BoxFit.contain,
        errorBuilder: (_, __, ___) => const Text(
          'MOBILITY\nHealthCare',
          textAlign: TextAlign.right,
          style: TextStyle(
            color: Colors.white,
            fontSize: 7,
            fontWeight: FontWeight.bold,
            height: 1.2,
          ),
        ),
      ),
    );
  }
}

/// Carte vide affichée quand l'utilisateur n'a pas encore de police.
class MhEcardEmpty extends StatelessWidget {
  const MhEcardEmpty({super.key, this.onSubscribe});

  final VoidCallback? onSubscribe;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 170,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFDDD4E9), width: 1.4),
      ),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.credit_card_off_outlined,
                size: 36, color: AppColors.mutedText),
            const SizedBox(height: 10),
            const Text(
              'Aucune police active',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppColors.secondary,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              'Souscrivez une assurance voyage pour obtenir votre carte.',
              style: TextStyle(fontSize: 11, color: AppColors.mutedText),
            ),
            if (onSubscribe != null) ...[
              const SizedBox(height: 12),
              TextButton(
                onPressed: onSubscribe,
                child: const Text('Souscrire une assurance'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
