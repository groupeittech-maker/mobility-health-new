import 'package:flutter/material.dart';

/// Couleurs officielles Mobility Health Care (#4e267c violet, #14AE98 teal).
class AppColors {
  static const Color brandPurple = Color(0xFF4e267c);
  static const Color brandTeal = Color(0xFF14AE98);

  static const Color primary = brandTeal;
  static const Color primaryDark = Color(0xFF109681);
  static const Color primaryLight = Color(0xFF6fd4c8);
  static const Color secondary = brandPurple;
  static const Color secondaryDark = Color(0xFF3d1e62);
  static const Color success = Color(0xFF10b981);
  static const Color danger = Color(0xFFef4444);
  static const Color warning = Color(0xFFf59e0b);
  static const Color mutedText = Color(0xFF64748b);
  /// Header / AppBar — blanc opaque.
  static const Color cardBg = Color(0xFFFFFFFF);
  /// Cartes / panneaux sur wallpaper — blanc quasi opaque (~98 %).
  static const Color surfaceCard = Color(0xFAFFFFFF);
  /// Champs à l'intérieur d'une carte — blanc 100 % pour contraste maximal.
  static const Color surfaceFieldFill = Color(0xFFFFFFFF);
  /// Bordure carte — violet brand ~20 %.
  static const Color surfaceCardBorder = Color(0x334E267C);
  /// Bordure champ au repos — neutre.
  static const Color surfaceFieldBorder = Color(0xFFE2E8F0);
  static List<BoxShadow> get surfaceCardShadow => [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.1),
          blurRadius: 16,
          offset: const Offset(0, 4),
        ),
      ];
  /// Fond surligné lavande (lisibilité sur wallpaper).
  static const Color textHighlight = Color(0xEBEDE9FE);
}
