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
    this.showAccount = false,
    this.onAccount,
    this.accountImage,
    this.accountInitials,
  });

  final bool showBack;
  final VoidCallback? onBack;
  final bool showBell;
  final VoidCallback? onBell;
  /// Titre affiché sous le logo (style kit : centré, violet).
  final String? title;
  /// Affiche un cercle « Compte » à droite de la cloche (accès au profil,
  /// photo de l'assuré si disponible).
  final bool showAccount;
  final VoidCallback? onAccount;
  final ImageProvider? accountImage;
  final String? accountInitials;

  @override
  Size get preferredSize => Size.fromHeight(title == null ? 64 : 96);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      toolbarHeight: title == null ? 64 : 96,
      backgroundColor: Colors.white,
      elevation: 0,
      automaticallyImplyLeading: false,
      leadingWidth: ((showBack ? 48 : 0) + (showAccount ? 64 : 0)).toDouble(),
      leading: (showBack || showAccount)
          ? Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (showBack)
                  IconButton(
                    icon: const Icon(Icons.arrow_back_ios_new, size: 20),
                    color: AppColors.secondary,
                    onPressed: onBack ?? () => context.pop(),
                  ),
                if (showAccount) _buildAccountButton(),
              ],
            )
          : null,
      centerTitle: true,
      title: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const MHOfficialLogo(),
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
          // Compense visuellement le côté gauche (retour et/ou compte)
          // pour garder le logo centré.
          SizedBox(
              width: ((showBack ? 48 : 0) + (showAccount ? 64 : 0))
                  .toDouble()),
      ],
    );
  }

  Widget _buildAccountButton() {
    // Décalage à gauche aligné sur la marge du contenu (texte « Bonjour »).
    return Padding(
      padding: const EdgeInsets.only(left: 20),
      child: InkWell(
        onTap: onAccount ?? () {},
        borderRadius: BorderRadius.circular(24),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 2),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border:
                      Border.all(color: const Color(0xFFD6CBE2), width: 1),
                ),
                child: CircleAvatar(
                  radius: 17,
                  backgroundColor: const Color(0xFFEDE9FE),
                  backgroundImage: accountImage,
                  child: accountImage == null
                      ? Text(
                          (accountInitials ?? '?').toUpperCase(),
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: AppColors.secondary,
                          ),
                        )
                      : null,
                ),
              ),
              const SizedBox(height: 1),
              const Text(
                'Compte',
                style: TextStyle(
                  fontSize: 9,
                  color: AppColors.secondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
