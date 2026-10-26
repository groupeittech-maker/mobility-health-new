import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_bottom_nav.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_services.dart';
import 'account_drawer.dart';
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

  /// Les onglets vivent dans un IndexedStack (initState une seule fois) —
  /// clés pour relancer le chargement quand on revient sur l'onglet.
  final GlobalKey<DashboardScreenState> _dashboardKey =
      GlobalKey<DashboardScreenState>();
  final GlobalKey<SubscriptionsTabScreenState> _subsTabKey =
      GlobalKey<SubscriptionsTabScreenState>();
  final GlobalKey<TeleconsultationScreenState> _teleKey =
      GlobalKey<TeleconsultationScreenState>();
  final GlobalKey<HopitauxScreenState> _hopKey =
      GlobalKey<HopitauxScreenState>();

  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  Uint8List? _accountPhotoBytes;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final u = context.read<AuthProvider>().currentUser;
      if (u != null && u.isMedecinReferentMh && mounted) {
        context.go('/referent');
      }
    });
    _loadAccountPhoto();
  }

  /// Photo du cercle « Compte » : photo de profil choisie par l'assuré,
  /// sinon photo d'identité de l'e-carte de la première souscription active
  /// (fallback sur les initiales du nom).
  Future<void> _loadAccountPhoto() async {
    try {
      final profile = await UsersService().getMyPhoto();
      if (profile != null) {
        if (mounted) setState(() => _accountPhotoBytes = profile);
        return;
      }
    } catch (_) {}
    try {
      final subs = await SubscriptionsService().getSubscriptions(limit: 100);
      final active = subs.where((s) => s.isActive);
      if (active.isEmpty) return;
      final bytes =
          await EcardsService().getUserPhoto(active.first.id);
      if (bytes != null && bytes.isNotEmpty && mounted) {
        setState(() => _accountPhotoBytes = Uint8List.fromList(bytes));
      }
    } catch (_) {}
  }

  String get _accountInitials {
    final u = context.read<AuthProvider>().currentUser;
    final name = (u?.fullName ?? '').trim();
    if (name.isEmpty) return '?';
    final parts = name.split(RegExp(r'\s+')).where((p) => p.isNotEmpty);
    if (parts.isEmpty) return '?';
    return parts.take(2).map((p) => p[0]).join();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: kMhContentBackground,
      drawer: MhAccountDrawer(
        photoBytes: _accountPhotoBytes,
        initials: _accountInitials,
        onPhotoChanged: (bytes) => setState(() => _accountPhotoBytes = bytes),
      ),
      appBar: MhAppBar(
        showBack: false,
        onBell: () => context.push('/notifications'),
        showAccount: true,
        onAccount: () => _scaffoldKey.currentState?.openDrawer(),
        accountImage:
            _accountPhotoBytes != null ? MemoryImage(_accountPhotoBytes!) : null,
        accountInitials: _accountInitials,
      ),
      body: IndexedStack(
        index: _currentTab.index,
        children: [
          DashboardScreen(key: _dashboardKey),
          SubscriptionsTabScreen(key: _subsTabKey),
          const SosScreen(),
          TeleconsultationScreen(key: _teleKey),
          HopitauxScreen(key: _hopKey),
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
          if (tab == MhNavTab.accueil) _dashboardKey.currentState?.refresh();
          if (tab == MhNavTab.souscription) _subsTabKey.currentState?.refresh();
          if (tab == MhNavTab.teleconsultation) _teleKey.currentState?.refresh();
          if (tab == MhNavTab.hopitaux) _hopKey.currentState?.refresh();
        },
      ),
    );
  }
}
