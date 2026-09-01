import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../models/product.dart';
import '../../models/subscription_quote.dart';
import '../../services/api_services.dart';

/// Page « Voir les détails » : fiche produit + bloc devis (prime, frais, contexte voyage).
class ProductDetailScreen extends StatefulWidget {
  const ProductDetailScreen({
    super.key,
    required this.productId,
    this.productName,
    this.assureur,
    this.quoteLine,
    this.currency = 'XAF',
    this.subscriberAge,
    this.residenceCountryName,
    this.destinationCountryName,
    this.voyageDureeJours,
    this.surprimesAge = const [],
    this.fraisSurPrimePct = 15,
  });

  final int productId;
  final String? productName;
  final String? assureur;
  final SubscriptionQuoteLine? quoteLine;
  final String currency;
  final int? subscriberAge;
  final String? residenceCountryName;
  final String? destinationCountryName;
  final int? voyageDureeJours;
  final List<SurprimeAgeRow> surprimesAge;
  final double fraisSurPrimePct;

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
    final cur = p.currency ?? widget.currency;
    final q = widget.quoteLine;
    final hasDevisContext = q != null ||
        widget.subscriberAge != null ||
        (widget.residenceCountryName != null && widget.residenceCountryName!.trim().isNotEmpty) ||
        (widget.destinationCountryName != null && widget.destinationCountryName!.trim().isNotEmpty) ||
        (widget.voyageDureeJours != null && widget.voyageDureeJours! > 0);

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Détails du produit'),
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF1E293B),
        elevation: 0,
      ),
      body: SafeArea(
        top: false,
        bottom: true,
        minimum: const EdgeInsets.only(bottom: 20),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
          children: [
          if (widget.productName != null && widget.productName!.isNotEmpty) ...[
            Text(
              widget.productName!,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: AppColors.primary,
              ),
            ),
            if (widget.assureur != null && widget.assureur!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  widget.assureur!,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: AppColors.primary,
                  ),
                ),
              ),
            const SizedBox(height: 20),
          ],
          if (hasDevisContext) ...[
            const _SectionTitle('Informations du devis'),
            const SizedBox(height: 8),
            _SectionValue(_devisContextLines(q)),
            const SizedBox(height: 20),
          ],
          if (q != null && q.hasBreakdown) ...[
            const _SectionTitle('Prime et frais de service'),
            const SizedBox(height: 8),
            _TableQuoteBreakdown(line: q, currency: cur),
            const SizedBox(height: 8),
            Text(
              'Règle appliquée : frais de service ≈ ${widget.fraisSurPrimePct.toStringAsFixed(0)} % de la prime d’assurance.',
              style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
            ),
            const SizedBox(height: 20),
          ] else if (q != null) ...[
            const _SectionTitle('Montant du devis'),
            const SizedBox(height: 8),
            _SectionValue('Total à payer : ${q.prixApplique.toStringAsFixed(0)} $cur'),
            const SizedBox(height: 20),
          ],
          if (widget.surprimesAge.isNotEmpty) ...[
            const _SectionTitle('Surprimes par âge (référence)'),
            const SizedBox(height: 8),
            _TableSurprimesAge(rows: widget.surprimesAge),
            const SizedBox(height: 20),
          ],
          const _SectionTitle('Garanties principales'),
          _TableGaranties(garanties: p.garanties),
          const SizedBox(height: 20),
          const _SectionTitle('Exclusions générales'),
          _ExclusionsBlock(exclusions: p.exclusionsGenerales),
        ],
        ),
      ),
    );
  }

  String _devisContextLines(SubscriptionQuoteLine? q) {
    final parts = <String>[];
    if (widget.subscriberAge != null) {
      parts.add('Âge du souscripteur : ${widget.subscriberAge} ans');
    } else {
      parts.add('Âge du souscripteur : non renseigné');
    }
    final zone = q?.zoneLibelleFr?.trim().isNotEmpty == true
        ? q!.zoneLibelleFr!.trim()
        : (q?.zoneGeographiqueCode?.trim().isNotEmpty == true ? 'Code zone : ${q!.zoneGeographiqueCode}' : null);
    if (zone != null) {
      parts.add('Zone tarifaire : $zone');
    } else {
      parts.add('Zone tarifaire : selon grille produit');
    }
    final res = widget.residenceCountryName?.trim();
    final dest = widget.destinationCountryName?.trim();
    parts.add('Pays de résidence : ${res != null && res.isNotEmpty ? res : '—'}');
    parts.add('Pays de destination : ${dest != null && dest.isNotEmpty ? dest : '—'}');
    final d = widget.voyageDureeJours;
    if (d != null && d > 0) {
      parts.add('Durée du voyage : $d jour${d > 1 ? 's' : ''}');
    } else {
      parts.add('Durée du voyage : —');
    }
    final tr = q?.trancheDureeLabelFr;
    if (tr != null && tr.isNotEmpty) {
      parts.add('Tranche durée (grille) : $tr');
    }
    return parts.join('\n');
  }

}

class _TableQuoteBreakdown extends StatelessWidget {
  const _TableQuoteBreakdown({required this.line, required this.currency});

  final SubscriptionQuoteLine line;
  final String currency;

  @override
  Widget build(BuildContext context) {
    const headerColor = Color(0xFF0d9488);
    final rows = <List<String>>[
      ['Prime d’assurance', '${line.primeAssurance!.toStringAsFixed(0)} $currency'],
      ['Frais de services', '${line.fraisServices!.toStringAsFixed(0)} $currency'],
      ['Total à payer', '${line.prixApplique.toStringAsFixed(0)} $currency'],
    ];
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Table(
        columnWidths: const {
          0: FlexColumnWidth(1.4),
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
            final isTotal = e.value[0] == 'Total à payer';
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
                      color: isTotal ? AppColors.primary : const Color(0xFF1E293B),
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

class _TableSurprimesAge extends StatelessWidget {
  const _TableSurprimesAge({required this.rows});

  final List<SurprimeAgeRow> rows;

  @override
  Widget build(BuildContext context) {
    const headerColor = Color(0xFF0d9488);
    if (rows.isEmpty) {
      return const _SectionValue('Aucune surprime par âge renseignée.');
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
        },
        children: [
          TableRow(
            decoration: const BoxDecoration(color: headerColor),
            children: [
              _hCell('Tranche d’âge'),
              _hCell('Surprime (%)'),
            ],
          ),
          ...rows.asMap().entries.map((e) {
            final r = e.value;
            return TableRow(
              decoration: BoxDecoration(
                color: e.key.isEven ? Colors.white : const Color(0xFFF8FAFC),
              ),
              children: [
                _cCell(r.tranche),
                _cCell('${r.pct.toStringAsFixed(r.pct == r.pct.roundToDouble() ? 0 : 1)} %'),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _hCell(String t) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Text(
          t,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: Colors.white,
          ),
        ),
      );

  Widget _cCell(String t) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Text(
          t,
          style: const TextStyle(fontSize: 12, color: Color(0xFF1E293B)),
        ),
      );
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
        height: 1.4,
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
      final nom = g['titre'] ??
          g['nom'] ??
          g['libelle'] ??
          g['garantie'] ??
          g['name'] ??
          '—';
      var capitaux = _str(g['capitaux']) ??
          _str(g['montant_max']) ??
          _str(g['plafond']) ??
          _str(g['montant']);
      if (capitaux == null || capitaux.isEmpty) {
        capitaux = _str(g['description']) ??
            _str(g['detail']) ??
            _str(g['texte']) ??
            _str(g['description_detail']) ??
            _str(g['commentaire']);
      }
      rows.add([
        nom.toString(),
        (capitaux == null || capitaux.isEmpty) ? '—' : capitaux,
      ]);
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
          0: FlexColumnWidth(1.4),
          1: FlexColumnWidth(1.6),
        },
        children: [
          TableRow(
            decoration: const BoxDecoration(color: headerColor),
            children: [
              _tableCell('Garantie', true),
              _tableCell('Capitaux', true),
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

  static String? _str(dynamic v) {
    if (v == null) return null;
    return v.toString();
  }

  Widget _tableCell(String text, bool isHeader) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 11,
          fontWeight: isHeader ? FontWeight.w600 : FontWeight.normal,
          color: isHeader ? Colors.white : const Color(0xFF1E293B),
          height: 1.25,
        ),
      ),
    );
  }
}

/// Exclusions : même logique que le web (`product-detail.js` / admin : `reference`+`exclusion`, ou anciens `cle`/`valeur`).
class _ExclusionsBlock extends StatelessWidget {
  const _ExclusionsBlock({this.exclusions});

  final List<Map<String, dynamic>>? exclusions;

  static String _normalizeLine(Map<String, dynamic> e) {
    var ref = (e['reference'] ?? e['libelle'] ?? e['cle'] ?? '').toString().trim();
    var exc = (e['exclusion'] ?? e['valeur'] ?? '').toString().trim();
    if (ref.isEmpty) {
      ref = (e['titre'] ?? e['nom'] ?? '').toString().trim();
    }
    if (exc.isEmpty) {
      exc = (e['description'] ?? e['detail'] ?? '').toString().trim();
    }
    if (ref.isNotEmpty && exc.isNotEmpty) return '$ref — $exc';
    if (ref.isNotEmpty) return ref;
    if (exc.isNotEmpty) return exc;
    return '';
  }

  @override
  Widget build(BuildContext context) {
    const headerColor = Color(0xFF0d9488);
    final lines = <String>[];
    for (final raw in exclusions ?? const <Map<String, dynamic>>[]) {
      final line = _normalizeLine(raw);
      if (line.isNotEmpty) lines.add(line);
    }
    if (lines.isEmpty) {
      return const _SectionValue('Aucune exclusion définie.');
    }
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Table(
        columnWidths: const {0: FlexColumnWidth(1)},
        children: [
          TableRow(
            decoration: const BoxDecoration(color: headerColor),
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                child: Text(
                  'Exclusion',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          ...lines.asMap().entries.map((e) {
            return TableRow(
              decoration: BoxDecoration(
                color: e.key.isEven ? Colors.white : const Color(0xFFF8FAFC),
              ),
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  child: Text(
                    e.value,
                    style: const TextStyle(
                      fontSize: 12,
                      color: Color(0xFF1E293B),
                      height: 1.35,
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
}
