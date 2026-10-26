import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_logo_header.dart';
import '../../core/widgets/mh_stripe.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';
import 'historique_screen.dart';
import 'subscriptions_filtered_screen.dart';

/// Menu « Compte » (ouverture par la gauche) : photo de profil modifiable
/// et accès Profil, Mes cartes, Attestations, Paiements, Historique,
/// Réseau MHC, Sécurité, Aide — anciens raccourcis du tableau de bord.
class MhAccountDrawer extends StatefulWidget {
  const MhAccountDrawer({
    super.key,
    required this.photoBytes,
    required this.initials,
    required this.onPhotoChanged,
  });

  final Uint8List? photoBytes;
  final String initials;
  final ValueChanged<Uint8List> onPhotoChanged;

  @override
  State<MhAccountDrawer> createState() => _MhAccountDrawerState();
}

class _MhAccountDrawerState extends State<MhAccountDrawer> {
  bool _uploading = false;

  Future<void> _changePhoto() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt, color: AppColors.secondary),
              title: const Text('Prendre une photo'),
              onTap: () => Navigator.of(ctx).pop(ImageSource.camera),
            ),
            ListTile(
              leading:
                  const Icon(Icons.photo_library, color: AppColors.secondary),
              title: const Text('Choisir dans la galerie'),
              onTap: () => Navigator.of(ctx).pop(ImageSource.gallery),
            ),
          ],
        ),
      ),
    );
    if (source == null || !mounted) return;
    final xfile = await ImagePicker().pickImage(
      source: source,
      imageQuality: 80,
      maxWidth: 800,
      preferredCameraDevice: CameraDevice.front,
    );
    if (xfile == null || !mounted) return;
    setState(() => _uploading = true);
    try {
      final bytes = await xfile.readAsBytes();
      await UsersService().updateMyPhoto(bytes);
      widget.onPhotoChanged(bytes);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Photo de profil mise à jour')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(apiErrorToUserMessage(e)),
          backgroundColor: AppColors.danger,
        ),
      );
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  void _go(VoidCallback action) {
    Navigator.of(context).pop(); // fermer le menu
    action();
  }

  void _pushPage(Widget page) => _go(() => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => page),
      ));

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().currentUser;
    final photo = widget.photoBytes;
    return Drawer(
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.horizontal(right: Radius.circular(20)),
      ),
      child: Column(
        children: [
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const MHOfficialLogo(),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      GestureDetector(
                        onTap: _uploading ? null : _changePhoto,
                        child: Stack(
                          clipBehavior: Clip.none,
                          children: [
                            CircleAvatar(
                              radius: 34,
                              backgroundColor: const Color(0xFFEDE9FE),
                              backgroundImage:
                                  photo != null ? MemoryImage(photo) : null,
                              child: _uploading
                                  ? const CircularProgressIndicator(
                                      strokeWidth: 2)
                                  : photo == null
                                      ? Text(
                                          widget.initials.toUpperCase(),
                                          style: const TextStyle(
                                            fontSize: 22,
                                            fontWeight: FontWeight.w700,
                                            color: AppColors.secondary,
                                          ),
                                        )
                                      : null,
                            ),
                            Positioned(
                              right: -2,
                              bottom: -2,
                              child: Container(
                                padding: const EdgeInsets.all(5),
                                decoration: BoxDecoration(
                                  color: AppColors.secondary,
                                  shape: BoxShape.circle,
                                  border:
                                      Border.all(color: Colors.white, width: 2),
                                ),
                                child: const Icon(Icons.photo_camera,
                                    size: 14, color: Colors.white),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              user?.displayName ?? '',
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                                color: AppColors.secondary,
                              ),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            Text(
                              user?.email ?? '',
                              style: const TextStyle(
                                  fontSize: 12, color: AppColors.mutedText),
                              overflow: TextOverflow.ellipsis,
                            ),
                            TextButton(
                              onPressed: _uploading ? null : _changePhoto,
                              style: TextButton.styleFrom(
                                padding: EdgeInsets.zero,
                                minimumSize: const Size(0, 28),
                                tapTargetSize:
                                    MaterialTapTargetSize.shrinkWrap,
                                foregroundColor: AppColors.secondary,
                              ),
                              child: const Text(
                                'Changer la photo',
                                style: TextStyle(
                                    fontSize: 12, fontWeight: FontWeight.w600),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const Divider(height: 24),
          Expanded(
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                _item(Icons.person_outline, 'Profil',
                    () => _go(() => context.push('/profile'))),
                _item(Icons.credit_card, 'Mes cartes',
                    () => _go(() => context.push('/ecards'))),
                _item(Icons.description_outlined, 'Attestations',
                    () => _go(() => context.push('/attestations'))),
                _item(
                  Icons.payments_outlined,
                  'Paiements',
                  () => _pushPage(const SubscriptionsFilteredScreen(
                      filter: SubscriptionsFilter.pending)),
                ),
                _item(
                  Icons.history,
                  'Historique',
                  () => _pushPage(const Scaffold(
                    backgroundColor: Colors.transparent,
                    appBar: MhAppBar(title: 'Historique', showBell: false),
                    body: ColoredBox(
                      color: kMhContentBackground,
                      child: HistoriqueScreen(),
                    ),
                  )),
                ),
                _item(Icons.public, 'Réseau MHC',
                    () => _go(() => context.push('/reseau'))),
                _item(Icons.shield_outlined, 'Sécurité',
                    () => _go(() => context.push('/forgot-password'))),
                _item(
                  Icons.help_outline,
                  'Aide',
                  () => _go(() => launchUrl(
                        Uri.parse('https://mobilityhealth-care.com'),
                        mode: LaunchMode.externalApplication,
                      )),
                ),
                const Divider(height: 16),
                _item(
                  Icons.logout,
                  'Déconnexion',
                  () async {
                    final router = GoRouter.of(context);
                    final auth = context.read<AuthProvider>();
                    Navigator.of(context).pop();
                    await AuthService.instance.logout();
                    await auth.checkAuth();
                    router.go('/login');
                  },
                  color: AppColors.danger,
                ),
              ],
            ),
          ),
          const MhStripe(),
        ],
      ),
    );
  }

  Widget _item(IconData icon, String label, VoidCallback onTap,
      {Color color = AppColors.secondary}) {
    return ListTile(
      leading: Icon(icon, color: color),
      title: Text(
        label,
        style: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w500,
          color: color == AppColors.secondary ? const Color(0xFF1E1B4B) : color,
        ),
      ),
      trailing: color == AppColors.secondary
          ? const Icon(Icons.chevron_right, color: AppColors.mutedText)
          : null,
      onTap: onTap,
    );
  }
}
