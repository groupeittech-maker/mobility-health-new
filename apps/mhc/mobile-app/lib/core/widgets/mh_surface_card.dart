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

  static InputDecoration input({
    String? labelText,
    String? hintText,
    Widget? suffixIcon,
    Widget? prefixIcon,
    bool isDense = false,
    EdgeInsetsGeometry? contentPadding,
    TextStyle? labelStyle,
    String? errorText,
  }) {
    return InputDecoration(
      labelText: labelText,
      hintText: hintText,
      suffixIcon: suffixIcon,
      prefixIcon: prefixIcon,
      isDense: isDense,
      labelStyle: labelStyle,
      errorText: errorText,
      filled: true,
      fillColor: AppColors.surfaceFieldFill,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.surfaceCardBorder),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.surfaceCardBorder),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: AppColors.primary, width: 2),
      ),
      contentPadding: contentPadding ?? const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    );
  }

  static InputDecorationTheme get surfaceInputDecorationTheme => InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surfaceFieldFill,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.surfaceCardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.surfaceCardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.danger),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: AppColors.danger, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      );

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
