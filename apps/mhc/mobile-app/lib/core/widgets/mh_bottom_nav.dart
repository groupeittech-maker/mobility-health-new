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
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, -2)),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SafeArea(
            top: false,
            bottom: false,
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
          const MhStripe(),
          SizedBox(height: MediaQuery.of(context).padding.bottom),
        ],
      ),
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
            Icon(icon, size: 24, color: AppColors.secondary),
            const SizedBox(height: 3),
            Text(
              label,
              style: const TextStyle(fontSize: 9.5, color: AppColors.secondary),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              height: 3,
              width: selected ? 34 : 0,
              decoration: BoxDecoration(
                color: AppColors.secondary,
                borderRadius: BorderRadius.circular(2),
              ),
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
