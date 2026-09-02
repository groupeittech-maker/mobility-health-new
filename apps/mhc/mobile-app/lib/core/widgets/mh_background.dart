import 'package:flutter/material.dart';

/// Fond d'écran charte Mobility Health Care (motif landmarks Afrique).
class MHBackground extends StatelessWidget {
  const MHBackground({super.key, this.child});

  final Widget? child;

  static const _wallpaperAsset = 'assets/images/wallpaper-brand.jpg';

  /// Décoration réutilisable (splash natif, écrans plein écran).
  static BoxDecoration get decoration => const BoxDecoration(
        color: Colors.white,
        image: DecorationImage(
          image: AssetImage(_wallpaperAsset),
          repeat: ImageRepeat.repeat,
          alignment: Alignment.topCenter,
          scale: 2.2,
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
