import 'package:flutter/material.dart';

import '../constants/app_colors.dart';

/// Carte / panneau lisible sur le fond wallpaper (aligné frontend web).
class MHSurfaceCard extends StatelessWidget {
  const MHSurfaceCard({
    super.key,
    required this.child,
    this.padding,
    this.borderRadius = 16,
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final double borderRadius;
  final VoidCallback? onTap;

  static BoxDecoration decoration({double borderRadius = 16}) => BoxDecoration(
        color: AppColors.surfaceCard,
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(color: AppColors.surfaceCardBorder, width: 1),
        boxShadow: AppColors.surfaceCardShadow,
      );

  @override
  Widget build(BuildContext context) {
    Widget content = Container(
      padding: padding,
      decoration: decoration(borderRadius: borderRadius),
      child: child,
    );
    if (onTap != null) {
      content = Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(borderRadius),
          child: content,
        ),
      );
    }
    return content;
  }
}
