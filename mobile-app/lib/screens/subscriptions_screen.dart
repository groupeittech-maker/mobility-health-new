import 'package:flutter/material.dart';

import '../models/subscription.dart';
import '../services/api_services.dart';

class SubscriptionsScreen extends StatefulWidget {
  const SubscriptionsScreen({super.key});

  @override
  State<SubscriptionsScreen> createState() => _SubscriptionsScreenState();
}

class _SubscriptionsScreenState extends State<SubscriptionsScreen> {
  final SubscriptionsService _subsService = SubscriptionsService();
  List<SubscriptionModel> _list = [];
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
      final list = await _subsService.getSubscriptions();
      setState(() {
        _list = list;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(_error!, textAlign: TextAlign.center, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              const SizedBox(height: 16),
              FilledButton.icon(onPressed: _load, icon: const Icon(Icons.refresh), label: const Text('Réessayer')),
            ],
          ),
        ),
      );
    }
    final active = _list.where((s) => s.isActive).toList();
    final pending = _list.where((s) => s.isPending).toList();
    final expired = _list.where((s) => s.isExpired).toList();
    final other = _list.where((s) => !s.isActive && !s.isPending && !s.isExpired).toList();

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _StatsRow(active: active.length, pending: pending.length, expired: expired.length),
          const SizedBox(height: 16),
          if (_list.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Center(child: Text('Aucune souscription')),
              ),
            )
          else ...[
            if (active.isNotEmpty) _Section(title: 'Actives', items: active),
            if (pending.isNotEmpty) _Section(title: 'En attente', items: pending),
            if (expired.isNotEmpty) _Section(title: 'Expirées', items: expired),
            if (other.isNotEmpty) _Section(title: 'Autres', items: other),
          ],
        ],
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  final int active;
  final int pending;
  final int expired;

  const _StatsRow({required this.active, required this.pending, required this.expired});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Card(
            color: Colors.green.shade50,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                children: [
                  Text('$active', style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: Colors.green)),
                  const Text('Actives', style: TextStyle(fontSize: 12)),
                ],
              ),
            ),
          ),
        ),
        Expanded(
          child: Card(
            color: Colors.orange.shade50,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                children: [
                  Text('$pending', style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: Colors.orange)),
                  const Text('En attente', style: TextStyle(fontSize: 12)),
                ],
              ),
            ),
          ),
        ),
        Expanded(
          child: Card(
            color: Colors.grey.shade200,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                children: [
                  Text('$expired', style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: Colors.grey)),
                  const Text('Expirées', style: TextStyle(fontSize: 12)),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final List<SubscriptionModel> items;

  const _Section({required this.title, required this.items});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Text(title, style: Theme.of(context).textTheme.titleMedium),
        ),
        ...items.map((s) => Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title: Text(s.numeroSouscription.isNotEmpty ? s.numeroSouscription : 'Souscription #${s.id}'),
                subtitle: Text(
                  s.produitAssurance?.nom ?? 'Produit #${s.produitAssuranceId}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: Text(
                  '${s.prixApplique.toStringAsFixed(0)} XAF',
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
              ),
            )),
        const SizedBox(height: 16),
      ],
    );
  }
}
