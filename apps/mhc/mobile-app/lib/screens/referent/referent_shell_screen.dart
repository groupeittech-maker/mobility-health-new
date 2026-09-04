import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_logo_header.dart';
import '../../models/referent_pipeline.dart';
import '../../providers/auth_provider.dart';
import '../../services/medecin_referent_service.dart';
import 'referent_pipeline_section_page.dart';

/// Espace médecin référent MH — pied de page aligné sur le web : Sinistre, Rapport, Facture, Dossier résolu.
class ReferentShellScreen extends StatefulWidget {
  const ReferentShellScreen({
    super.key,
    this.initialNavIndex = 0,
    this.initialSubTab = 0,
  });

  /// Onglet pied de page : 0 Sinistre, 1 Rapport, 2 Facture, 3 Résolu ([GoRoute] `?tab=`).
  final int initialNavIndex;

  /// Sous-onglet « À valider » / « Validé » ([GoRoute] `?sub=` 0 ou 1).
  final int initialSubTab;

  /// Aligné sur le web (review-dashboard.js : limit=200).
  static const int pageSize = 200;

  @override
  State<ReferentShellScreen> createState() => _ReferentShellScreenState();
}

class _ReferentShellScreenState extends State<ReferentShellScreen> {
  late int _navIndex;
  List<ReferentDossierItem> _dossiers = [];
  Map<String, int> _serverCounts = {};
  bool _loading = true;
  bool _loadingMore = false;
  bool _hasMore = true;
  int _nextSkip = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    _navIndex = widget.initialNavIndex.clamp(0, 3);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final u = context.read<AuthProvider>().currentUser;
      if (u == null || !u.isMedecinReferentMh) {
        context.go('/login');
      }
    });
    _refresh();
  }

  Future<void> _refresh() async {
    setState(() {
      _loading = true;
      _error = null;
      _hasMore = true;
      _nextSkip = 0;
    });
    try {
      final results = await Future.wait([
        MedecinReferentService.instance.loadEnrichedDossiersPage(
          skip: 0,
          limit: ReferentShellScreen.pageSize,
        ),
        MedecinReferentService.instance.fetchReferentPipelineCounts(),
      ]);
      final list = results[0] as List<ReferentDossierItem>;
      final counts = results[1] as Map<String, int>;
      if (!mounted) return;
      setState(() {
        _dossiers = list;
        _serverCounts = counts;
        _nextSkip = list.length;
        _hasMore = list.length >= ReferentShellScreen.pageSize;
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

  Future<void> _loadMore() async {
    if (!_hasMore || _loadingMore || _loading) return;
    setState(() => _loadingMore = true);
    try {
      final list = await MedecinReferentService.instance.loadEnrichedDossiersPage(
        skip: _nextSkip,
        limit: ReferentShellScreen.pageSize,
      );
      if (!mounted) return;
      setState(() {
        _dossiers = [..._dossiers, ...list];
        _nextSkip += list.length;
        _hasMore = list.length >= ReferentShellScreen.pageSize;
        _loadingMore = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loadingMore = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Chargement : ${e.toString()}')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kMhContentBackground,
      appBar: AppBar(
        toolbarHeight: 76,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const MHOfficialLogo(height: 40),
            const SizedBox(width: 10),
            const Flexible(
              child: Text(
                'Médecin référent',
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        backgroundColor: AppColors.cardBg,
        foregroundColor: AppColors.primary,
        elevation: 0.5,
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            tooltip: 'Notifications',
            onPressed: () => context
                .push('/referent/notifications')
                .then((_) => _refresh()),
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
            initialSubTab: widget.initialNavIndex == 0 ? widget.initialSubTab : null,
            items: _dossiers,
            serverCounts: _serverCounts,
            loading: _loading,
            error: _error,
            onRefresh: _refresh,
            hasMore: _hasMore,
            loadingMore: _loadingMore,
            onLoadMore: _loadMore,
          ),
          ReferentPipelineSectionPage(
            section: ReferentFooterSection.rapport,
            initialSubTab: widget.initialNavIndex == 1 ? widget.initialSubTab : null,
            items: _dossiers,
            serverCounts: _serverCounts,
            loading: _loading,
            error: _error,
            onRefresh: _refresh,
            hasMore: _hasMore,
            loadingMore: _loadingMore,
            onLoadMore: _loadMore,
          ),
          ReferentPipelineSectionPage(
            section: ReferentFooterSection.facture,
            initialSubTab: widget.initialNavIndex == 2 ? widget.initialSubTab : null,
            items: _dossiers,
            serverCounts: _serverCounts,
            loading: _loading,
            error: _error,
            onRefresh: _refresh,
            hasMore: _hasMore,
            loadingMore: _loadingMore,
            onLoadMore: _loadMore,
          ),
          ReferentPipelineSectionPage(
            section: ReferentFooterSection.resolu,
            initialSubTab: widget.initialNavIndex == 3 ? widget.initialSubTab : null,
            items: _dossiers,
            serverCounts: _serverCounts,
            loading: _loading,
            error: _error,
            onRefresh: _refresh,
            hasMore: _hasMore,
            loadingMore: _loadingMore,
            onLoadMore: _loadMore,
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
