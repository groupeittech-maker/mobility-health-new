import 'package:flutter/material.dart';
import '../../models/product.dart';
import '../../services/api_services.dart';

/// Page "Voir les détails" du produit : données issues du back-office (garanties, primes, exclusions).
class ProductDetailScreen extends StatefulWidget {
  const ProductDetailScreen({
    super.key,
    required this.productId,
    this.productName,
    this.assureur,
  });

  final int productId;
  final String? productName;
  final String? assureur;

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  ProductModel? _product;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadProduct();
  }

  Future<void> _loadProduct() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final product = await ProductsService().getProduct(widget.productId);
      if (mounted) {
        setState(() {
          _product = product;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Détails du produit'),
          backgroundColor: Colors.white,
          foregroundColor: const Color(0xFF1E293B),
          elevation: 0,
        ),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Détails du produit'),
          backgroundColor: Colors.white,
          foregroundColor: const Color(0xFF1E293B),
          elevation: 0,
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, size: 48, color: Colors.red),
                const SizedBox(height: 16),
                Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Color(0xFF64748B)),
                ),
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: _loadProduct,
                  child: const Text('Réessayer'),
                ),
              ],
            ),
          ),
        ),
      );
    }
    final p = _product!;
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Détails du produit'),
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF1E293B),
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const _SectionTitle('Reconduction possible'),
          _SectionValue(p.reconductionPossible ? 'Oui' : 'Non'),
          const SizedBox(height: 16),
          const _SectionTitle('Âge'),
          _SectionValue(_formatAge(p)),
          const SizedBox(height: 16),
          const _SectionTitle('Zones couvertes'),
          _SectionValue(_formatZones(p)),
          const SizedBox(height: 20),
          const _SectionTitle('Garanties principales'),
          _TableGaranties(garanties: p.garanties),
          const SizedBox(height: 20),
          const _SectionTitle('Primes générées'),
          _TablePrimes(primes: p.primesGenerees, currency: p.currency ?? 'XAF'),
          const SizedBox(height: 20),
          const _SectionTitle('Exclusions générales'),
          _TableExclusions(exclusions: p.exclusionsGenerales),
        ],
      ),
    );
  }

  String _formatAge(ProductModel p) {
    final min = p.ageMinimum;
    final max = p.ageMaximum;
    if (min != null && max != null) return 'Min: $min ans - Max: $max ans';
    if (min != null) return 'Min: $min ans';
    if (max != null) return 'Max: $max ans';
    return 'Non spécifié';
  }

  String _formatZones(ProductModel p) {
    final zg = p.zonesGeographiques;
    if (zg == null) return 'Non spécifié';
    final zones = zg['zones'];
    if (zones is List && zones.isNotEmpty) {
      return zones.map((e) => e?.toString() ?? '').where((s) => s.isNotEmpty).join(', ');
    }
    final pays = zg['pays_eligibles'];
    if (pays is List && pays.isNotEmpty) {
      return pays.map((e) => e?.toString() ?? '').where((s) => s.isNotEmpty).join(', ');
    }
    return zg.toString();
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.bold,
        color: Color(0xFF1E293B),
      ),
    );
  }
}

class _SectionValue extends StatelessWidget {
  const _SectionValue(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 14,
        color: Color(0xFF475569),
      ),
    );
  }
}

class _TableGaranties extends StatelessWidget {
  const _TableGaranties({this.garanties});

  final List<Map<String, dynamic>>? garanties;

  @override
  Widget build(BuildContext context) {
    const headerColor = Color(0xFF0d9488);
    final rows = <List<String>>[];
    final list = garanties ?? [];
    for (final g in list) {
      final nom = g['titre'] ?? g['nom'] ?? g['libelle'] ?? g['garantie'] ?? g['name'] ?? g['description'] ?? '—';
      final franchise = _str(g['franchise']) ?? '0';
      final capitaux = _str(g['capitaux']) ?? _str(g['montant_max']) ?? _str(g['plafond']) ?? _str(g['montant']) ?? '—';
      final obl = g['obligatoire'];
      final oblStr = _isTrue(obl) ? 'Oui' : 'Non';
      rows.add([nom.toString(), franchise, capitaux, oblStr]);
    }
    if (rows.isEmpty) {
      return const _SectionValue('Aucune garantie définie.');
    }
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Table(
        columnWidths: const {
          0: FlexColumnWidth(2),
          1: FlexColumnWidth(1),
          2: FlexColumnWidth(1),
          3: FlexColumnWidth(0.8),
        },
        children: [
          TableRow(
            decoration: const BoxDecoration(color: headerColor),
            children: [
              _tableCell('Garantie', true),
              _tableCell('Franchise', true),
              _tableCell('Capitaux', true),
              _tableCell('Obligatoire', true),
            ],
          ),
          ...rows.asMap().entries.map((e) {
            return TableRow(
              decoration: BoxDecoration(
                color: e.key.isEven ? Colors.white : const Color(0xFFF8FAFC),
              ),
              children: [
                _tableCell(e.value[0], false),
                _tableCell(e.value[1], false),
                _tableCell(e.value[2], false),
                _tableCell(e.value[3], false),
              ],
            );
          }),
        ],
      ),
    );
  }

  static String? _str(dynamic v) {
    if (v == null) return null;
    return v.toString();
  }

  static bool _isTrue(dynamic v) {
    if (v == true) return true;
    if (v is String) return ['oui', 'yes', 'true', '1'].contains(v.toLowerCase());
    return false;
  }

  Widget _tableCell(String text, bool isHeader) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 12,
          fontWeight: isHeader ? FontWeight.w600 : FontWeight.normal,
          color: isHeader ? Colors.white : const Color(0xFF1E293B),
        ),
      ),
    );
  }
}

class _TablePrimes extends StatelessWidget {
  const _TablePrimes({this.primes, this.currency = 'XAF'});

  final Map<String, dynamic>? primes;
  final String currency;

  static const _displayLabels = {
    'prime_nette': 'Prime nette',
    'accessoire': 'Accessoire',
    'taxes': 'Taxes',
    'prime_total': 'Prime total',
  };

  static String _formatKey(String k) => k
      .replaceAll('_', ' ')
      .split(' ')
      .map((s) => s.isEmpty ? s : '${s[0].toUpperCase()}${s.length > 1 ? s.substring(1).toLowerCase() : ''}')
      .join(' ');

  @override
  Widget build(BuildContext context) {
    const headerColor = Color(0xFF0d9488);
    final rows = <List<String>>[];
    final p = primes ?? {};
    final order = ['prime_nette', 'accessoire', 'taxes', 'prime_total'];
    for (final k in order) {
      final v = p[k];
      if (v != null) {
        final s = v is num ? '${v.toStringAsFixed(0)} $currency' : '$v $currency';
        rows.add([_displayLabels[k] ?? _formatKey(k), s]);
      }
    }
    for (final e in p.entries) {
      if (!order.contains(e.key) && e.value != null) {
        final v = e.value;
        final s = v is num ? '${v.toStringAsFixed(0)} $currency' : '$v $currency';
        rows.add([_formatKey(e.key), s]);
      }
    }
    if (rows.isEmpty) {
      return const _SectionValue('Aucune prime définie.');
    }
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Table(
        columnWidths: const {
          0: FlexColumnWidth(1.5),
          1: FlexColumnWidth(1),
        },
        children: [
          TableRow(
            decoration: const BoxDecoration(color: headerColor),
            children: [
              _tableCell('Libellé', true),
              _tableCell('Montant', true),
            ],
          ),
          ...rows.asMap().entries.map((e) {
            final isTotal = e.value[0] == 'Prime total';
            return TableRow(
              decoration: BoxDecoration(
                color: e.key.isEven ? Colors.white : const Color(0xFFF8FAFC),
              ),
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  child: Text(
                    e.value[0],
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isTotal ? FontWeight.bold : FontWeight.normal,
                      color: const Color(0xFF1E293B),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  child: Text(
                    e.value[1],
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isTotal ? FontWeight.bold : FontWeight.normal,
                      color: const Color(0xFF1E293B),
                    ),
                  ),
                ),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _tableCell(String text, bool isHeader) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 12,
          fontWeight: isHeader ? FontWeight.w600 : FontWeight.normal,
          color: isHeader ? Colors.white : const Color(0xFF1E293B),
        ),
      ),
    );
  }
}

class _TableExclusions extends StatelessWidget {
  const _TableExclusions({this.exclusions});

  final List<Map<String, dynamic>>? exclusions;

  @override
  Widget build(BuildContext context) {
    const headerColor = Color(0xFF0d9488);
    final rows = <List<String>>[];
    final list = exclusions ?? [];
    for (final e in list) {
      final cle = e['cle'] ?? e['titre'] ?? e['nom'] ?? '';
      final valeur = e['valeur'] ?? e['description'] ?? '';
      if (cle.toString().isNotEmpty || valeur.toString().isNotEmpty) {
        rows.add([cle.toString(), valeur.toString()]);
      }
    }
    if (rows.isEmpty) {
      return const _SectionValue('Aucune exclusion définie.');
    }
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Table(
        columnWidths: const {
          0: FlexColumnWidth(1),
          1: FlexColumnWidth(2),
        },
        children: [
          TableRow(
            decoration: const BoxDecoration(color: headerColor),
            children: [
              _tableCell('Clé', true),
              _tableCell('Valeur', true),
            ],
          ),
          ...rows.asMap().entries.map((e) {
            return TableRow(
              decoration: BoxDecoration(
                color: e.key.isEven ? Colors.white : const Color(0xFFF8FAFC),
              ),
              children: [
                _tableCell(e.value[0], false),
                _tableCell(e.value[1], false),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _tableCell(String text, bool isHeader) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 12,
          fontWeight: isHeader ? FontWeight.w600 : FontWeight.normal,
          color: isHeader ? Colors.white : const Color(0xFF1E293B),
        ),
      ),
    );
  }
}
