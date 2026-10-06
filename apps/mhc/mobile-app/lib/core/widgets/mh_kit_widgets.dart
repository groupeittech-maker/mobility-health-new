import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../constants/app_colors.dart';

/// Bouton plein du kit MyMHC : couleur unie + flèche « → ».
/// Utilisé pour les CTA des écrans d'onboarding et formulaires
/// (Créer un compte / Se connecter / Suivant).
class MhSolidButton extends StatelessWidget {
  const MhSolidButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.color = AppColors.brandPurple,
    this.loading = false,
    this.height = 52,
  });

  final String label;
  final VoidCallback? onPressed;
  final Color color;
  final bool loading;
  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: height,
      child: ElevatedButton(
        onPressed: loading ? null : onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: color,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
        child: loading
            ? const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 16,
                    ),
                  ),
                  const SizedBox(width: 10),
                  const Icon(Icons.arrow_forward, size: 18),
                ],
              ),
      ),
    );
  }
}

/// Bouton contour du kit MyMHC : bordure violette + flèche « → ».
class MhOutlineArrowButton extends StatelessWidget {
  const MhOutlineArrowButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.height = 52,
  });

  final String label;
  final VoidCallback? onPressed;
  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: height,
      child: OutlinedButton(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.secondary,
          side: const BorderSide(color: AppColors.brandPurple, width: 1.2),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              label,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
                fontSize: 16,
              ),
            ),
            const SizedBox(width: 10),
            const Icon(Icons.arrow_forward, size: 18),
          ],
        ),
      ),
    );
  }
}

/// Bloc « ou continuer avec » + boutons sociaux Google / Apple / Microsoft
/// du kit MyMHC (Bienvenue, Connexion).
class MhSocialLogin extends StatelessWidget {
  const MhSocialLogin({super.key, this.onProvider});

  /// Appelé avec 'google', 'apple' ou 'microsoft'. Null = boutons désactivés.
  final void Function(String provider)? onProvider;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            const Expanded(child: Divider(color: Color(0xFFD6CBE2))),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text(
                'ou continuer avec',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
              ),
            ),
            const Expanded(child: Divider(color: Color(0xFFD6CBE2))),
          ],
        ),
        const SizedBox(height: 14),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _SocialButton(
              asset: 'assets/images/google.svg',
              provider: 'google',
              onTap: onProvider,
            ),
            const SizedBox(width: 18),
            _SocialButton(
              asset: 'assets/images/apple.svg',
              provider: 'apple',
              onTap: onProvider,
            ),
            const SizedBox(width: 18),
            _SocialButton(
              asset: 'assets/images/microsoft.svg',
              provider: 'microsoft',
              onTap: onProvider,
            ),
          ],
        ),
      ],
    );
  }
}

class _SocialButton extends StatelessWidget {
  const _SocialButton({
    required this.asset,
    required this.provider,
    this.onTap,
  });

  final String asset;
  final String provider;
  final void Function(String provider)? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap == null ? null : () => onTap!(provider),
      borderRadius: BorderRadius.circular(12),
      child: Opacity(
        opacity: onTap == null ? 0.85 : 1,
        child: Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFE3DCEE)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 6,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Center(
            child: SvgPicture.asset(asset, width: 24, height: 24),
          ),
        ),
      ),
    );
  }
}

/// Libellé de champ au-dessus de la boîte (style kit : violet, gras).
class MhFieldLabel extends StatelessWidget {
  const MhFieldLabel(this.text, {super.key, this.required_ = false});

  final String text;
  final bool required_;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Text(
        required_ ? '$text *' : text,
        style: const TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w600,
          color: AppColors.secondary,
        ),
      ),
    );
  }
}
