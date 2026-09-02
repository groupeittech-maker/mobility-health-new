import 'package:flutter/material.dart';

import '../constants/app_colors.dart';

/// Fond surligné lavande pour texte lisible sur le wallpaper brand.
class MHTextHighlight extends StatelessWidget {
  const MHTextHighlight({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    this.borderRadius = 6,
    this.inline = false,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final double borderRadius;
  final bool inline;

  static const Color _highlightBg = Color(0xEBEDE9FE);

  @override
  Widget build(BuildContext context) {
    final decoration = BoxDecoration(
      color: _highlightBg,
      borderRadius: BorderRadius.circular(borderRadius),
    );

    if (inline) {
      return Container(
        padding: padding,
        decoration: decoration,
        child: child,
      );
    }

    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        padding: padding,
        decoration: decoration,
        child: child,
      ),
    );
  }
}

/// Titre de section sur wallpaper (sans surlignage, couleur brand).
class MHSectionTitle extends StatelessWidget {
  const MHSectionTitle({
    super.key,
    required this.title,
    this.subtitle,
  });

  final String title;
  final String? subtitle;

  static TextStyle titleStyle(BuildContext context) {
    return Theme.of(context).textTheme.headlineSmall!.copyWith(
          fontWeight: FontWeight.bold,
          color: AppColors.secondary,
        );
  }

  static TextStyle subtitleStyle(BuildContext context) {
    return Theme.of(context).textTheme.bodyLarge!.copyWith(
          color: AppColors.secondary,
          fontWeight: FontWeight.w500,
        );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: titleStyle(context)),
        if (subtitle != null) ...[
          const SizedBox(height: 6),
          Text(subtitle!, style: subtitleStyle(context)),
        ],
      ],
    );
  }
}
