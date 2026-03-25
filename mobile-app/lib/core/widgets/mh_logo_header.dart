import 'package:flutter/material.dart';

import '../constants/app_colors.dart';

/// Logo officiel MH + slogan, pour Connexion / Inscription et en-têtes.
/// Pour un logo sans fond, ajouter assets/images/logo_officiel_mh.png (PNG avec transparence).
class MHLogoHeader extends StatelessWidget {
  const MHLogoHeader({
    super.key,
    this.height = 100,
    this.showSlogan = true,
    this.compact = false,
    this.transparentBackground = false,
  });

  final double height;
  final bool showSlogan;
  final bool compact;
  /// Si true, utilise le PNG s'il existe (sans fond) ; sinon JPG.
  final bool transparentBackground;

  static const _logoPng = 'assets/images/logo_officiel_mh.png';
  static const _logoJpg = 'assets/images/logo_officiel_mh.jpg';

  @override
  Widget build(BuildContext context) {
    final usePng = transparentBackground;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Image.asset(
          usePng ? _logoPng : _logoJpg,
          height: height,
          fit: BoxFit.contain,
          errorBuilder: (_, __, ___) {
            if (usePng) {
              return Image.asset(
                _logoJpg,
                height: height,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => _FallbackLogo(height: height),
              );
            }
            return _FallbackLogo(height: height);
          },
        ),
        if (showSlogan) ...[
          SizedBox(height: compact ? 6 : 12),
          Text(
            'Travel safe. Life free',
            style: TextStyle(
              color: AppColors.secondary,
              fontSize: compact ? 13 : 16,
              fontWeight: FontWeight.w500,
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ],
    );
  }
}

class _FallbackLogo extends StatelessWidget {
  const _FallbackLogo({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.health_and_safety, size: height * 0.7, color: AppColors.primary),
        const SizedBox(width: 8),
        Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'MOBILITY',
              style: TextStyle(
                fontSize: height * 0.22,
                fontWeight: FontWeight.bold,
                color: AppColors.primary,
              ),
            ),
            Text(
              'HealthCare',
              style: TextStyle(
                fontSize: height * 0.18,
                fontWeight: FontWeight.bold,
                color: AppColors.secondary,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
