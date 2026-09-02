import 'package:flutter/material.dart';

import '../constants/app_colors.dart';

/// Chemins du logo officiel : PNG avec transparence en priorité, JPG en secours.
const String kMhOfficialLogoPng = 'assets/images/logo_officiel_mh.png';
const String kMhOfficialLogoJpg = 'assets/images/logo_officiel_mh.jpg';

/// Logo officiel seul (AppBar, splash, etc.) : PNG transparent d’abord, puis JPG, puis fallback texte.
class MHOfficialLogo extends StatelessWidget {
  const MHOfficialLogo({
    super.key,
    required this.height,
  });

  final double height;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      kMhOfficialLogoPng,
      height: height,
      fit: BoxFit.contain,
      errorBuilder: (_, __, ___) {
        return Image.asset(
          kMhOfficialLogoJpg,
          height: height,
          fit: BoxFit.contain,
          errorBuilder: (_, __, ___) => _FallbackLogo(height: height),
        );
      },
    );
  }
}

/// Logo officiel MH + slogan, pour Connexion / Inscription et en-têtes.
class MHLogoHeader extends StatelessWidget {
  const MHLogoHeader({
    super.key,
    this.height = 100,
    this.showSlogan = false,
    this.compact = false,
  });

  final double height;
  final bool showSlogan;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        MHOfficialLogo(height: height),
        if (showSlogan) ...[
          SizedBox(height: compact ? 6 : 12),
          Text(
            'Travel safe, Live free.',
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
