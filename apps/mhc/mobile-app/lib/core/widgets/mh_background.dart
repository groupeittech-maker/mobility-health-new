import 'package:flutter/material.dart';

/// Fond d'écran charte MyMHC : chevrons pâles en dégradé (wallpaper du kit).
class MHBackground extends StatelessWidget {
  const MHBackground({super.key, this.child});

  final Widget? child;

  static const _wallpaperAsset = 'assets/images/wallpaper-chevrons.png';

  /// Décoration réutilisable (splash natif, écrans plein écran).
  static BoxDecoration get decoration => const BoxDecoration(
        color: Colors.white,
        image: DecorationImage(
          image: AssetImage(_wallpaperAsset),
          repeat: ImageRepeat.repeat,
          alignment: Alignment.topCenter,
          scale: 1.6,
        ),
      );

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: decoration,
      child: child,
    );
  }
}
