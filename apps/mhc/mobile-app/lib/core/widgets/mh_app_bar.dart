import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../constants/app_colors.dart';
import 'mh_logo_header.dart';

/// En-tête type kit MyMHC : flèche retour, logo centré, cloche notifications.
class MhAppBar extends StatelessWidget implements PreferredSizeWidget {
  const MhAppBar({
    super.key,
    this.showBack = true,
    this.onBack,
    this.showBell = true,
    this.onBell,
    this.title,
  });

  final bool showBack;
  final VoidCallback? onBack;
  final bool showBell;
  final VoidCallback? onBell;
  /// Titre affiché sous le logo (style kit : centré, violet).
  final String? title;

  @override
  Size get preferredSize => Size.fromHeight(title == null ? 64 : 96);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      toolbarHeight: title == null ? 64 : 96,
      backgroundColor: Colors.white,
      elevation: 0,
      automaticallyImplyLeading: false,
      leading: showBack
          ? IconButton(
              icon: const Icon(Icons.arrow_back_ios_new, size: 20),
              color: AppColors.secondary,
              onPressed: onBack ?? () => context.pop(),
            )
          : null,
      centerTitle: true,
      title: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const MHOfficialLogo(height: 34),
          if (title != null) ...[
            const SizedBox(height: 8),
            Text(
              title!,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: AppColors.secondary,
              ),
            ),
          ],
        ],
      ),
      actions: [
        if (showBell)
          IconButton(
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                const Icon(Icons.notifications_none, size: 26),
                Positioned(
                  right: 0,
                  top: 0,
                  child: Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: Color(0xFFF03E4D),
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              ],
            ),
            color: AppColors.secondary,
            onPressed: onBell ?? () {},
          )
        else
          const SizedBox(width: 48),
      ],
    );
  }
}
