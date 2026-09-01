import 'package:flutter/material.dart';

import '../models/product.dart';
import '../services/api_services.dart';

class ProductsScreen extends StatefulWidget {
  const ProductsScreen({super.key});

  @override
  State<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends State<ProductsScreen> {
  final ProductsService _productsService = ProductsService();
  List<ProductModel> _list = [];
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
      final list = await _productsService.getProducts();
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
    if (_list.isEmpty) {
      return const Center(child: Text('Aucun produit disponible'));
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _list.length,
        itemBuilder: (context, i) {
          final p = _list[i];
          return Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: ListTile(
              title: Text(p.nom),
              subtitle: Text(
                '${p.cout.toStringAsFixed(0)} ${p.currency ?? 'XAF'}',
                style: TextStyle(color: Colors.teal.shade700, fontWeight: FontWeight.w500),
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => _showProductDetail(context, p),
            ),
          );
        },
      ),
    );
  }

  void _showProductDetail(BuildContext context, ProductModel p) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        maxChildSize: 0.9,
        minChildSize: 0.3,
        expand: false,
        builder: (_, controller) => SingleChildScrollView(
          controller: controller,
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(p.nom, style: Theme.of(ctx).textTheme.titleLarge),
              const SizedBox(height: 8),
              if (p.description != null && p.description!.isNotEmpty) Text(p.description!),
              const SizedBox(height: 12),
              Text('Prix: ${p.cout.toStringAsFixed(0)} ${p.currency ?? 'XAF'}',
                  style: const TextStyle(fontWeight: FontWeight.bold)),
              if (p.dureeMinJours != null || p.dureeMaxJours != null)
                Text('Durée: ${p.dureeMinJours ?? "?"} - ${p.dureeMaxJours ?? "?"} jours'),
            ],
          ),
        ),
      ),
    );
  }
}
