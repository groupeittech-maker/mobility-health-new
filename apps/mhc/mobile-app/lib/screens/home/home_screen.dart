import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_logo_header.dart';
import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';
import 'dashboard_screen.dart';
import 'historique_screen.dart';
import 'sos_screen.dart';

/// Shell après connexion : en-tête logo MOBILITY HealthCare + déconnexion, 3 onglets (Souscription, Alerte SOS, Historique), barre de navigation sombre.
enum _HomeTab { souscription, alerteSos, historique }

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  _HomeTab _currentTab = _HomeTab.souscription;

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

  Widget _buildBody() {
    switch (_currentTab) {
      case _HomeTab.souscription:
        return const DashboardScreen();
      case _HomeTab.alerteSos:
        return const SosScreen();
      case _HomeTab.historique:
        return const HistoriqueScreen();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kMhContentBackground,
      appBar: AppBar(
        toolbarHeight: 84,
        backgroundColor: AppColors.cardBg,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.home_outlined),
          color: const Color(0xFF475569),
          onPressed: () => setState(() => _currentTab = _HomeTab.souscription),
          tooltip: 'Retour à l\'accueil',
        ),
        centerTitle: true,
        title: LayoutBuilder(
          builder: (context, constraints) {
            final maxW = constraints.maxWidth.isFinite ? constraints.maxWidth : 240.0;
            return FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.center,
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: maxW),
                child: const MHOfficialLogo(height: 52),
              ),
            );
          },
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.exit_to_app),
            color: const Color(0xFF475569),
            onPressed: () async {
              await AuthService.instance.logout();
              if (!context.mounted) return;
              context.go('/login');
            },
            tooltip: 'Déconnexion',
          ),
        ],
      ),
      body: _buildBody(),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: Color(0xFF1E293B),
          boxShadow: [
            BoxShadow(
              color: Colors.black26,
              blurRadius: 8,
              offset: Offset(0, -2),
            ),
          ],
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _NavItem(
                  icon: Icons.description_outlined,
                  label: 'Souscription',
                  selected: _currentTab == _HomeTab.souscription,
                  onTap: () {
                    if (_currentTab == _HomeTab.souscription) {
                      context.push('/subscription/new');
                    } else {
                      setState(() => _currentTab = _HomeTab.souscription);
                    }
                  },
                ),
                _NavItem(
                  icon: Icons.notifications_active,
                  label: 'Alerte SOS',
                  selected: _currentTab == _HomeTab.alerteSos,
                  onTap: () => setState(() => _currentTab = _HomeTab.alerteSos),
                  selectedColor: AppColors.danger,
                  alwaysColor: AppColors.danger,
                ),
                _NavItem(
                  icon: Icons.history,
                  label: 'Historique',
                  selected: _currentTab == _HomeTab.historique,
                  onTap: () => setState(() => _currentTab = _HomeTab.historique),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
    this.selectedColor,
    this.alwaysColor,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final Color? selectedColor;
  /// Si défini, utilise cette couleur en permanence (sélectionné ou non).
  final Color? alwaysColor;

  @override
  Widget build(BuildContext context) {
    final color = alwaysColor ?? (selected ? (selectedColor ?? Colors.white) : Colors.white54);
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 26, color: color),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: color,
                fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
