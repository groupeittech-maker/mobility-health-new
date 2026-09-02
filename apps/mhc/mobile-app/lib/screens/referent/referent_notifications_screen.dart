import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../services/medecin_referent_service.dart';
import '../../services/referent_navigation.dart';

class ReferentNotificationsScreen extends StatefulWidget {
  const ReferentNotificationsScreen({super.key});

  @override
  State<ReferentNotificationsScreen> createState() => _ReferentNotificationsScreenState();
}

class _ReferentNotificationsScreenState extends State<ReferentNotificationsScreen> {
  final _service = MedecinReferentService.instance;
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await _service.fetchNotifications(limit: 100);
      if (!mounted) return;
      final filtered = list
          .where((n) => (n['type_notification']?.toString() ?? '') != 'email_error')
          .toList();
      setState(() {
        _items = filtered;
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

  Future<void> _onTap(Map<String, dynamic> n) async {
    final id = n['id'] as int?;
    if (id == null) return;
    final read = n['is_read'] == true;
    final route = referentRouteForNotificationRow(n);

    if (!read) {
      try {
        await _service.markNotificationRead(id);
      } catch (_) {}
    }

    if (!mounted) return;
    if (route != null) {
      context.push(route);
    }
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Text(
            'Notifications',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppColors.primary,
                ),
          ),
        ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _load,
            child: _buildBody(),
          ),
        ),
      ],
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 120),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }
    if (_error != null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          Text(_error!, textAlign: TextAlign.center),
          const SizedBox(height: 16),
          Center(child: FilledButton(onPressed: _load, child: const Text('Réessayer'))),
        ],
      );
    }
    if (_items.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 80),
          Center(child: Text('Aucune notification.')),
        ],
      );
    }
    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
      itemCount: _items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, i) {
        final n = _items[i];
        final read = n['is_read'] == true;
        return Material(
          color: read ? Colors.grey.shade100 : Colors.teal.shade50,
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => _onTap(n),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          n['titre']?.toString() ?? 'Notification',
                          style: TextStyle(
                            fontWeight: read ? FontWeight.w500 : FontWeight.bold,
                            fontSize: 15,
                          ),
                        ),
                      ),
                      if (!read)
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: AppColors.primary,
                            shape: BoxShape.circle,
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    n['message']?.toString() ?? '',
                    style: TextStyle(fontSize: 13, color: Colors.grey.shade800),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    n['type_notification']?.toString() ?? '',
                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

/// Page autonome avec retour (barre d’app du référent).
class ReferentNotificationsPage extends StatelessWidget {
  const ReferentNotificationsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kMhContentBackground,
      appBar: AppBar(
        title: const Text('Notifications'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        backgroundColor: AppColors.cardBg,
        foregroundColor: AppColors.primary,
        elevation: 0.5,
      ),
      body: SafeArea(
        top: false,
        child: const ReferentNotificationsScreen(),
      ),
    );
  }
}
