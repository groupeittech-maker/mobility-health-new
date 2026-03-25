import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../models/referent_pipeline.dart';
import '../../providers/auth_provider.dart';
import '../../services/medecin_referent_service.dart';
import 'referent_pipeline_section_page.dart';

/// Espace médecin référent MH — pied de page aligné sur le web : Sinistre, Rapport, Facture, Dossier résolu.
class ReferentShellScreen extends StatefulWidget {
  const ReferentShellScreen({super.key});

  @override
  State<ReferentShellScreen> createState() => _ReferentShellScreenState();
}

class _ReferentShellScreenState extends State<ReferentShellScreen> {
  int _navIndex = 0;
  List<ReferentDossierItem> _dossiers = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final u = context.read<AuthProvider>().currentUser;
      if (u == null || !u.isMedecinReferentMh) {
        context.go('/login');
      }
    });
    _loadDossiers();
  }

  Future<void> _loadDossiers() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await MedecinReferentService.instance.loadEnrichedDossiers();
      if (!mounted) return;
      setState(() {
        _dossiers = list;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset(
              'assets/images/logo_officiel_mh.jpg',
              height: 36,
              errorBuilder: (_, __, ___) => const Text('MH'),
            ),
            const SizedBox(width: 10),
            const Flexible(
              child: Text(
                'Médecin référent',
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        backgroundColor: Colors.white,
        foregroundColor: AppColors.primary,
        elevation: 0.5,
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            tooltip: 'Notifications',
            onPressed: () => context
                .push('/referent/notifications')
                .then((_) => _loadDossiers()),
          ),
          IconButton(
            icon: const Icon(Icons.person_outline),
            tooltip: 'Profil',
            onPressed: () => context.push('/referent/profil'),
          ),
        ],
      ),
      body: IndexedStack(
        index: _navIndex,
        children: [
          ReferentPipelineSectionPage(
            section: ReferentFooterSection.sinistre,
            items: _dossiers,
            loading: _loading,
            error: _error,
            onRefresh: _loadDossiers,
          ),
          ReferentPipelineSectionPage(
            section: ReferentFooterSection.rapport,
            items: _dossiers,
            loading: _loading,
            error: _error,
            onRefresh: _loadDossiers,
          ),
          ReferentPipelineSectionPage(
            section: ReferentFooterSection.facture,
            items: _dossiers,
            loading: _loading,
            error: _error,
            onRefresh: _loadDossiers,
          ),
          ReferentPipelineSectionPage(
            section: ReferentFooterSection.resolu,
            items: _dossiers,
            loading: _loading,
            error: _error,
            onRefresh: _loadDossiers,
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _navIndex,
        onDestinationSelected: (i) => setState(() => _navIndex = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.emergency_outlined),
            selectedIcon: Icon(Icons.emergency),
            label: 'Sinistre',
            tooltip: 'Sinistre à valider / validé',
          ),
          NavigationDestination(
            icon: Icon(Icons.description_outlined),
            selectedIcon: Icon(Icons.description),
            label: 'Rapport',
            tooltip: 'Rapport à valider / validé',
          ),
          NavigationDestination(
            icon: Icon(Icons.receipt_long_outlined),
            selectedIcon: Icon(Icons.receipt_long),
            label: 'Facture',
            tooltip: 'Facture à valider / validée',
          ),
          NavigationDestination(
            icon: Icon(Icons.task_alt_outlined),
            selectedIcon: Icon(Icons.task_alt),
            label: 'Résolu',
            tooltip: 'Dossier résolu',
          ),
        ],
      ),
    );
  }
}
