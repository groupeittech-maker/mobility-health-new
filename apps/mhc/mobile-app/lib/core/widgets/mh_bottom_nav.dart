import 'package:flutter/material.dart';

import '../constants/app_colors.dart';
import 'mh_stripe.dart';

/// Barre de navigation du kit MyMHC : fond blanc, 5 entrées
/// (Accueil, Souscription, SOS central rouge, Téléconsultation, Hôpitaux),
/// soulignement violet sur l'onglet actif, bande chevron en bas.
enum MhNavTab { accueil, souscription, sos, teleconsultation, hopitaux }

class MhBottomNav extends StatelessWidget {
  const MhBottomNav({
    super.key,
    required this.current,
    required this.onTabSelected,
  });

  final MhNavTab current;
  final ValueChanged<MhNavTab> onTabSelected;

  static const _sosRed = Color(0xFFF03E4D);

  @override
  Widget build(BuildContext context) {
    // Barre « flottante » façon WhatsApp : pill arrondie détachée du bas,
    // onglet actif surligné en lavande, bande MHC en dessous.
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 0, 14, 6),
          child: Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(32),
              boxShadow: const [
                BoxShadow(
                  color: Colors.black26,
                  blurRadius: 16,
                  offset: Offset(0, 6),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(32),
              child: SizedBox(
                height: 64,
                child: Row(
                  children: [
                    _item(MhNavTab.accueil, Icons.home_rounded, 'Accueil'),
                    _item(MhNavTab.souscription, Icons.verified_user_outlined, 'Souscription'),
                    _sosItem(),
                    _item(MhNavTab.teleconsultation, Icons.medical_services_outlined, 'Téléconsult.'),
                    _item(MhNavTab.hopitaux, Icons.local_hospital_outlined, 'Hôpitaux'),
                  ],
                ),
              ),
            ),
          ),
        ),
        const MhStripe(),
      ],
    );
  }

  Widget _item(MhNavTab tab, IconData icon, String label) {
    final selected = current == tab;
    return Expanded(
      child: InkWell(
        onTap: () => onTabSelected(tab),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              decoration: BoxDecoration(
                color: selected
                    ? const Color(0xFFEDE9FE)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(18),
              ),
              child: Icon(icon, size: 24, color: AppColors.secondary),
            ),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                fontSize: 9.5,
                color: AppColors.secondary,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  Widget _sosItem() {
    final selected = current == MhNavTab.sos;
    return Expanded(
      child: InkWell(
        onTap: () => onTabSelected(MhNavTab.sos),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: _sosRed,
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 3),
                boxShadow: [
                  BoxShadow(
                    color: _sosRed.withValues(alpha: selected ? 0.5 : 0.3),
                    blurRadius: 10,
                  ),
                ],
              ),
              child: const Icon(Icons.phone_in_talk, color: Colors.white, size: 22),
            ),
            const SizedBox(height: 2),
            const Text(
              'SOS',
              style: TextStyle(
                fontSize: 9.5,
                fontWeight: FontWeight.w700,
                color: _sosRed,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
