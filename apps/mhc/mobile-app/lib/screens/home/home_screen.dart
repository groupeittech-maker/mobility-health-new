import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_bottom_nav.dart';
import '../../providers/auth_provider.dart';
import 'dashboard_screen.dart';
import 'hopitaux_screen.dart';
import 'sos_screen.dart';
import 'subscriptions_tab_screen.dart';
import 'teleconsultation_screen.dart';

/// Shell après connexion (kit MyMHC) : en-tête logo + 5 onglets —
/// Accueil, Souscription, SOS (rouge central), Téléconsultation, Hôpitaux —
/// barre blanche et bande graphique chevron en bas.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, this.initialTab = 0});

  /// Onglet affiché à l'ouverture (0 Accueil, 1 Souscription, 2 SOS,
  /// 3 Téléconsultation, 4 Hôpitaux).
  final int initialTab;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late MhNavTab _currentTab =
      MhNavTab.values[widget.initialTab.clamp(0, MhNavTab.values.length - 1)];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final u = context.read<AuthProvider>().currentUser;
      if (u != null && u.isMedecinReferentMh && mounted) {
        context.go('/referent');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kMhContentBackground,
      appBar: MhAppBar(
        showBack: false,
        onBell: () => context.push('/attestations'),
      ),
      body: IndexedStack(
        index: _currentTab.index,
        children: const [
          DashboardScreen(),
          SubscriptionsTabScreen(),
          SosScreen(),
          TeleconsultationScreen(),
          HopitauxScreen(),
        ],
      ),
      bottomNavigationBar: MhBottomNav(
        current: _currentTab,
        onTabSelected: (tab) {
          if (tab == MhNavTab.souscription && _currentTab == MhNavTab.souscription) {
            context.push('/subscription/new');
            return;
          }
          setState(() => _currentTab = tab);
        },
      ),
    );
  }
}
