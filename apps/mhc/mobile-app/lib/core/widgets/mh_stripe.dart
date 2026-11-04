import 'package:flutter/material.dart';

const String kMhStripeAsset = 'assets/images/bande_mhc_bas.png';

/// Hauteur visible de la bande graphique (« Bar du bas » du kit).
const double kMhStripeHeight = 28;

/// Bande graphique officielle du kit MyMHC (bas de chaque écran).
class MhStripe extends StatelessWidget {
  const MhStripe({super.key, this.height = kMhStripeHeight});

  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: height,
      width: double.infinity,
      child: Image.asset(
        kMhStripeAsset,
        width: double.infinity,
        height: height,
        fit: BoxFit.cover,
        alignment: Alignment.topCenter,
        errorBuilder: (_, __, ___) => const SizedBox.shrink(),
      ),
    );
  }
}

/// Place la bande en bas de TOUS les écrans de l'application (une seule
/// fois, au niveau de MaterialApp.builder) : les pages poussées, dialogues
/// plein écran et onglets l'ont toutes, avec la même hauteur fine.
///
/// - Navigation gestuelle (petite zone système) : la bande est collée tout
///   en bas et recouvre cette zone.
/// - Navigation 3 boutons (grande zone système) : la bande reste fine,
///   juste au-dessus de la barre système (pas de bloc épais sous les boutons).
/// - Clavier ouvert : la bande est masquée pour ne pas réduire l'espace.
class MhStripeFrame extends StatelessWidget {
  const MhStripeFrame({super.key, required this.child});

  final Widget child;

  /// Au-delà, la zone système est une barre à boutons, pas une poignée gestuelle.
  static const double _gestureInsetMax = 32;

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);
    if (media.viewInsets.bottom > 0) return child;
    final inset = media.viewPadding.bottom;
    final gesture = inset <= _gestureInsetMax;
    final stripeHeight = gesture && inset > kMhStripeHeight ? inset : kMhStripeHeight;
    return Column(
      children: [
        Expanded(
          child: MediaQuery.removePadding(
            context: context,
            removeBottom: true,
            child: child,
          ),
        ),
        MhStripe(height: stripeHeight),
        if (!gesture) ColoredBox(color: Colors.white, child: SizedBox(height: inset, width: double.infinity)),
      ],
    );
  }
}
