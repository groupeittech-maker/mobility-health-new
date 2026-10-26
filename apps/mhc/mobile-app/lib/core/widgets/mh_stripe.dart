import 'package:flutter/material.dart';

/// Bande graphique officielle du kit MyMHC (bas de chaque écran).
/// Image « Bar du bas » (assets/images/bande_mhc_bas.png) affichée pleine
/// largeur, ancrée en haut. Par défaut la bande se prolonge dans la zone
/// système du bas (barre de navigation Android) : elle est collée tout en
/// bas de l'écran, sans bande blanche en dessous.
class MhStripe extends StatelessWidget {
  const MhStripe({super.key, this.height = 30, this.fillBottomInset = true});

  final double height;

  /// Étendre la bande sous la barre de navigation système. Les écrans
  /// doivent alors utiliser `SafeArea(bottom: false)`.
  final bool fillBottomInset;

  @override
  Widget build(BuildContext context) {
    final inset =
        fillBottomInset ? MediaQuery.of(context).viewPadding.bottom : 0.0;
    return SizedBox(
      height: height + inset,
      width: double.infinity,
      child: Image.asset(
        'assets/images/bande_mhc_bas.png',
        width: double.infinity,
        height: height + inset,
        fit: BoxFit.cover,
        alignment: Alignment.topCenter,
        errorBuilder: (_, __, ___) => const SizedBox.shrink(),
      ),
    );
  }
}
