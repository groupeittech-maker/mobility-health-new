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

/// Titre de section avec surlignage (dashboard mobile).
class MHSectionTitle extends StatelessWidget {
  const MHSectionTitle({
    super.key,
    required this.title,
    this.subtitle,
  });

  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MHTextHighlight(
          child: Text(
            title,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: const Color(0xFF1E293B),
            ),
          ),
        ),
        if (subtitle != null) ...[
          const SizedBox(height: 6),
          MHTextHighlight(
            child: Text(
              subtitle!,
              style: theme.textTheme.bodyLarge?.copyWith(
                color: AppColors.mutedText,
              ),
            ),
          ),
        ],
      ],
    );
  }
}
