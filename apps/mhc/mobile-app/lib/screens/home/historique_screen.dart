import 'package:flutter/material.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../core/constants/app_colors.dart';
import '../../core/utils/api_error_helper.dart';
import '../../models/subscription.dart';
import '../../services/api_services.dart';
import 'subscription_detail_screen.dart';

/// Historique : souscriptions, alertes, prestations (séjours) – connecté au backend.
class HistoriqueScreen extends StatefulWidget {
  const HistoriqueScreen({super.key});

  @override
  State<HistoriqueScreen> createState() => _HistoriqueScreenState();
}

class _HistoriqueScreenState extends State<HistoriqueScreen> {
  int _selectedTab = 0; // 0 Souscriptions, 1 Alertes, 2 Prestations
  static const _tabs = ['Souscriptions', 'Alertes', 'Prestations'];

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: kMhContentBackground,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
            child: Row(
              children: List.generate(_tabs.length, (i) {
                final selected = _selectedTab == i;
                return Expanded(
                  child: InkWell(
                    onTap: () => setState(() => _selectedTab = i),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          child: Text(
                            _tabs[i],
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
                              color: selected ? AppColors.primary : const Color(0xFF64748B),
                            ),
                          ),
                        ),
                        Container(
                          height: 3,
                          decoration: BoxDecoration(
                            color: selected ? AppColors.primary : Colors.transparent,
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: _selectedTab == 0
                ? _SouscriptionsList()
                : _selectedTab == 1
                    ? _AlertesList()
                    : _HospitalisationsList(),
          ),
        ],
      ),
    );
  }
}

class _SouscriptionsList extends StatefulWidget {
  @override
  State<_SouscriptionsList> createState() => _SouscriptionsListState();
}

class _SouscriptionsListState extends State<_SouscriptionsList> {
  final SubscriptionsService _api = SubscriptionsService();
  List<SubscriptionModel> _list = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    final peek = SubscriptionsService.peekSubscriptionsCache();
    if (peek != null) {
      _list = peek;
      _loading = false;
    }
    _load();
  }

  Future<void> _load({bool forceRefresh = false}) async {
    if (mounted) {
      setState(() {
        _error = null;
        if (_list.isEmpty) _loading = true;
      });
    }
    try {
      final list = await _api.getSubscriptions(forceRefresh: forceRefresh);
      if (mounted) setState(() {
        _list = list;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = apiErrorToUserMessage(e);
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.danger)),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: _loading ? null : () => _load(forceRefresh: true),
                icon: const Icon(Icons.refresh),
                label: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      );
    }
    if (_list.isEmpty) {
      return const Center(child: Text('Aucune souscription'));
    }
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    return RefreshIndicator(
      onRefresh: () => _load(forceRefresh: true),
      child: ListView.builder(
        padding: EdgeInsets.fromLTRB(20, 0, 20, bottomPadding),
        itemCount: _list.length,
        itemBuilder: (context, i) {
          final s = _list[i];
          final statut = s.statut;
          Color statusColor = AppColors.mutedText;
          if (statut == 'active') statusColor = AppColors.success;
          if (statut == 'en_attente' || statut == 'pending') statusColor = AppColors.warning;
          if (statut == 'expiree' || statut == 'expired') statusColor = AppColors.danger;
          if (statut == 'resiliee') statusColor = const Color(0xFF64748B);
          final isResiliee = statut == 'resiliee';
          return Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: isResiliee
                  ? null
                  : () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => SubscriptionDetailScreen(subscription: s),
                        ),
                      );
                    },
              borderRadius: BorderRadius.circular(16),
              splashColor: isResiliee ? null : AppColors.primary.withValues(alpha: 0.2),
              highlightColor: isResiliee ? null : AppColors.primary.withValues(alpha: 0.1),
              child: Opacity(
                opacity: isResiliee ? 0.7 : 1,
                child: _HistoryCard(
                  title: s.numeroSouscription.isNotEmpty ? s.numeroSouscription : 'Souscription #${s.id}',
                  status: statut,
                  statusColor: statusColor,
                  fields: [
                    ('Date', _formatDateStr(s.createdAt)),
                    ('Produit', s.produitAssurance?.nom ?? 'Produit #${s.produitAssuranceId}'),
                    if (s.prixApplique > 0) ('Prix', '${s.prixApplique.toStringAsFixed(0)} XAF'),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

String _formatDateStr(dynamic d) {
  if (d == null) return '–';
  if (d is DateTime) return '${d.day}/${d.month}/${d.year}';
  final s = d.toString();
  if (s.length >= 10) return '${s.substring(8, 10)}/${s.substring(5, 7)}/${s.substring(0, 4)}';
  return s;
}

class _AlertesList extends StatefulWidget {
  @override
  State<_AlertesList> createState() => _AlertesListState();
}

class _AlertesListState extends State<_AlertesList> {
  final SosService _api = SosService();
  List<Map<String, dynamic>> _list = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    final peek = SosService.peekSosAlertesCache();
    if (peek != null) {
      _list = peek;
      _loading = false;
    }
    _load();
  }

  Future<void> _load({bool forceRefresh = false}) async {
    if (mounted) {
      setState(() {
        _error = null;
        if (_list.isEmpty) _loading = true;
      });
    }
    try {
      final list = await _api.getAlertes(forceRefresh: forceRefresh);
      if (mounted) setState(() {
        _list = list;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = apiErrorToUserMessage(e);
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.danger)),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: _loading ? null : () => _load(forceRefresh: true),
                icon: const Icon(Icons.refresh),
                label: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      );
    }
    if (_list.isEmpty) return const Center(child: Text('Aucune alerte'));
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    return RefreshIndicator(
      onRefresh: () => _load(forceRefresh: true),
      child: ListView.builder(
        padding: EdgeInsets.fromLTRB(20, 0, 20, bottomPadding),
        itemCount: _list.length,
        itemBuilder: (context, i) {
          final a = _list[i];
          final numero = a['numero_alerte'] ?? 'Alerte #${a['id']}';
          final statut = (a['statut'] ?? '').toString();
          final created = a['created_at']?.toString() ?? '';
          final dateStr = created.length >= 10
              ? '${created.substring(8, 10)}/${created.substring(5, 7)}/${created.substring(0, 4)}'
              : created;
          Color statusColor = AppColors.mutedText;
          if (statut == 'en_cours') statusColor = AppColors.warning;
          if (statut == 'resolue') statusColor = AppColors.success;
          return _HistoryCard(
            title: numero,
            status: statut,
            statusColor: statusColor,
            fields: [
              ('Date', dateStr),
              ('Type', a['description']?.toString().isNotEmpty == true ? 'Alerte' : 'Urgence'),
            ],
          );
        },
      ),
    );
  }
}

class _HospitalisationsList extends StatefulWidget {
  @override
  State<_HospitalisationsList> createState() => _HospitalisationsListState();
}

class _HospitalisationsListState extends State<_HospitalisationsList> {
  final HospitalStaysService _api = HospitalStaysService();
  List<Map<String, dynamic>> _list = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    final peek = HospitalStaysService.peekHospitalStaysCache();
    if (peek != null) {
      _list = peek;
      _loading = false;
    }
    _load();
  }

  Future<void> _load({bool forceRefresh = false}) async {
    if (mounted) {
      setState(() {
        _error = null;
        if (_list.isEmpty) _loading = true;
      });
    }
    try {
      final list = await _api.getHospitalStays(forceRefresh: forceRefresh);
      if (mounted) setState(() {
        _list = list;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = apiErrorToUserMessage(e);
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.danger)),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: _loading ? null : () => _load(forceRefresh: true),
                icon: const Icon(Icons.refresh),
                label: const Text('Réessayer'),
              ),
            ],
          ),
        ),
      );
    }
    if (_list.isEmpty) return const Center(child: Text('Aucune prestation'));
    final bottomPadding = MediaQuery.of(context).padding.bottom + 24;
    return RefreshIndicator(
      onRefresh: () => _load(forceRefresh: true),
      child: ListView.builder(
        padding: EdgeInsets.fromLTRB(20, 0, 20, bottomPadding),
        itemCount: _list.length,
        itemBuilder: (context, i) {
          final s = _list[i];
          final id = s['id'];
          final status = (s['status'] ?? s['report_status'] ?? '').toString();
          final created = s['created_at']?.toString() ?? '';
          final dateStr = created.length >= 10
              ? '${created.substring(8, 10)}/${created.substring(5, 7)}/${created.substring(0, 4)}'
              : created;
          final hospital = s['hospital'];
          final hospitalName = hospital is Map ? (hospital['nom'] ?? '') : 'Hôpital';
          final lieu = hospital is Map ? (hospital['ville'] ?? hospital['adresse'] ?? 'Non spécifié') : 'Non spécifié';
          return _HistoryCard(
            title: 'Séjour #$id',
            status: status.isNotEmpty ? status : 'Terminé',
            statusColor: const Color(0xFF64748B),
            fields: [
              ('Date', dateStr),
              ('Lieu', lieu),
              ('Hôpital', hospitalName.isNotEmpty ? hospitalName : 'Non spécifié'),
            ],
          );
        },
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({
    required this.title,
    required this.status,
    required this.statusColor,
    required this.fields,
  });

  final String title;
  final String status;
  final Color statusColor;
  final List<(String, String)> fields;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      child: MHSurfaceCard(
        padding: const EdgeInsets.all(16),
        child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1E293B),
                  ),
                  overflow: TextOverflow.ellipsis,
                  maxLines: 1,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  status,
                  style: TextStyle(
                    fontSize: 12,
                    color: statusColor,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...fields.map((f) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 120,
                      child: Text(
                        f.$1,
                        style: const TextStyle(
                          fontSize: 12,
                          color: Color(0xFF64748B),
                        ),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        f.$2,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: Color(0xFF1E293B),
                        ),
                      ),
                    ),
                  ],
                ),
              )),
        ],
        ),
      ),
    );
  }
}
