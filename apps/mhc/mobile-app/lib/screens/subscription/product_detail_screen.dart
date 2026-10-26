import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/garanties_officielles.dart';
import '../../core/utils/api_error_helper.dart';
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
  bool _readExclusions = false;

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
          _error = apiErrorToUserMessage(e);
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
          backgroundColor: AppColors.cardBg,
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
          backgroundColor: AppColors.cardBg,
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
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('Détails du produit'),
        backgroundColor: AppColors.cardBg,
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
            _TableKeyValue(
              headerLeft: 'Libellé',
              headerRight: 'Valeur',
              rows: _devisContextRows(q),
            ),
            const SizedBox(height: 20),
          ],
          if (q != null && q.hasBreakdown) ...[
            const _SectionTitle('Décompte de la prime'),
            const SizedBox(height: 8),
            _TableQuoteBreakdown(line: q, currency: cur),
            const SizedBox(height: 20),
          ] else if (q != null) ...[
            const _SectionTitle('Montant du devis'),
            const SizedBox(height: 8),
            _TableKeyValue(
              headerLeft: 'Libellé',
              headerRight: 'Montant',
              rows: [
                ['Total à payer', '${q.prixApplique.toStringAsFixed(0)} $cur'],
              ],
            ),
            const SizedBox(height: 20),
          ],
          const _SectionTitle('Conditions de couverture'),
          const SizedBox(height: 8),
          const _OfficialGarantiesTable(),
          const SizedBox(height: 20),
          const _SectionTitle('Exclusions générales'),
          const SizedBox(height: 8),
          const _OfficialExclusionsBlock(),
          const SizedBox(height: 16),
          CheckboxListTile(
            value: _readExclusions,
            onChanged: (v) => setState(() => _readExclusions = v ?? false),
            title: const Text(
              'J\'ai lu les exclusions',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Color(0xFF1E293B)),
            ),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
            activeColor: AppColors.primary,
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton(
              onPressed: _readExclusions ? () => Navigator.of(context).pop(true) : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.secondary,
                foregroundColor: Colors.white,
              ),
              child: const Text('Valider et revenir au choix du produit'),
            ),
          ),
        ],
        ),
      ),
    );
  }

  List<List<String>> _devisContextRows(SubscriptionQuoteLine? q) {
    final rows = <List<String>>[];
    if (widget.subscriberAge != null) {
      rows.add(['Âge du souscripteur', '${widget.subscriberAge} ans']);
    } else {
      rows.add(['Âge du souscripteur', 'Non renseigné']);
    }
    final zone = q?.zoneLibelleFr?.trim().isNotEmpty == true
        ? q!.zoneLibelleFr!.trim()
        : (q?.zoneGeographiqueCode?.trim().isNotEmpty == true ? 'Code zone : ${q!.zoneGeographiqueCode}' : null);
    rows.add(['Zone tarifaire', zone ?? 'Selon grille produit']);
    final res = widget.residenceCountryName?.trim();
    final dest = widget.destinationCountryName?.trim();
    rows.add(['Pays de résidence', (res != null && res.isNotEmpty) ? res : '—']);
    rows.add(['Pays de destination', (dest != null && dest.isNotEmpty) ? dest : '—']);
    final d = widget.voyageDureeJours;
    if (d != null && d > 0) {
      rows.add(['Durée du voyage', '$d jour${d > 1 ? 's' : ''}']);
    } else {
      rows.add(['Durée du voyage', '—']);
    }
    final tr = q?.trancheDureeLabelFr;
    if (tr != null && tr.isNotEmpty) {
      rows.add(['Tranche durée (grille)', tr]);
    }
    return rows;
  }

}

class _TableKeyValue extends StatelessWidget {
  const _TableKeyValue({
    required this.headerLeft,
    required this.headerRight,
    required this.rows,
  });

  final String headerLeft;
  final String headerRight;
  final List<List<String>> rows;

  @override
  Widget build(BuildContext context) {
    const headerColor = AppColors.secondary;
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Table(
        columnWidths: const {
          0: FlexColumnWidth(1.4),
          1: FlexColumnWidth(1),
        },
        children: [
          TableRow(
            decoration: const BoxDecoration(color: headerColor),
            children: [
              _cell(headerLeft, isHeader: true),
              _cell(headerRight, isHeader: true),
            ],
          ),
          ...rows.asMap().entries.map((e) {
            return TableRow(
              decoration: BoxDecoration(
                color: e.key.isEven ? Colors.white : const Color(0xFFF8FAFC),
              ),
              children: [
                _cell(e.value[0], bold: false),
                _cell(e.value[1], bold: false),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _cell(String text, {bool isHeader = false, bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 12,
          fontWeight: isHeader || bold ? FontWeight.w600 : FontWeight.normal,
          color: isHeader ? Colors.white : const Color(0xFF1E293B),
        ),
      ),
    );
  }
}

class _TableQuoteBreakdown extends StatelessWidget {
  const _TableQuoteBreakdown({required this.line, required this.currency});

  final SubscriptionQuoteLine line;
  final String currency;

  @override
  Widget build(BuildContext context) {
    const headerColor = AppColors.secondary;
    final taxRows = <List<String>>[];
    if (line.taxesTotal != null && line.taxesTotal! > 0) {
      for (final t in line.taxes ?? []) {
        final montant = (t['montant'] as num?)?.toDouble() ?? 0;
        if (montant > 0) {
          taxRows.add(['Taxe additionnelle (${t['nom'] ?? 'Taxe'})', '${montant.toStringAsFixed(0)} $currency']);
        }
      }
    }
    final surprime = line.montantSurprime;
    final surprimePct = line.pctSurprimeApplique;
    final rows = <List<String>>[
      ['Prime Nette', '${line.primeAssurance!.toStringAsFixed(0)} $currency'],
      // « Surprime » toujours affichée sous Prime Nette (revue : dépend
      // de l'âge de l'assuré — 0 F CFA quand aucune surprime).
      [
        'Surprime${surprimePct != null && surprimePct > 0 ? ' (${surprimePct.toStringAsFixed(surprimePct == surprimePct.roundToDouble() ? 0 : 1)} %)' : ''}',
        '${(surprime ?? 0).toStringAsFixed(0)} $currency',
      ],
      ['Coût de Police', '${(line.coutPolice ?? 0).toStringAsFixed(0)} $currency'],
      ['Taxe', '${line.fraisServices!.toStringAsFixed(0)} $currency'],
      ...taxRows,
      ['Prime Nette Totale', '${line.prixApplique.toStringAsFixed(0)} $currency'],
    ];
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      clipBehavior: Clip.antiAlias,
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
            final isTotal = e.value[0] == 'Prime Nette Totale';
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

class _OfficialGarantiesTable extends StatelessWidget {
  const _OfficialGarantiesTable();

  @override
  Widget build(BuildContext context) {
    const headerColor = AppColors.secondary;
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            color: headerColor,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            child: const Row(
              children: [
                Expanded(
                  flex: 3,
                  child: Text(
                    'PRESTATIONS',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                ),
                Expanded(
                  flex: 2,
                  child: Text(
                    'PLAFONDS',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ),
          for (final cat in kCategoriesGarantiesOfficielles) ...[
            Container(
              width: double.infinity,
              color: const Color(0xFFEDE7F6),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    cat.titre,
                    style: const TextStyle(
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                      color: AppColors.secondary,
                      letterSpacing: 0.3,
                    ),
                  ),
                  if (cat.sousTitre != null)
                    Text(
                      cat.sousTitre!,
                      style: const TextStyle(
                        fontSize: 10,
                        fontStyle: FontStyle.italic,
                        color: AppColors.secondary,
                      ),
                    ),
                ],
              ),
            ),
            for (final g in cat.lignes)
              Container(
                decoration: const BoxDecoration(
                  border: Border(
                    bottom: BorderSide(color: Color(0xFFF1F5F9)),
                  ),
                ),
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      flex: 3,
                      child: Text(
                        g.prestation,
                        style: const TextStyle(
                          fontSize: 11,
                          color: Color(0xFF1E293B),
                          height: 1.3,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      flex: 2,
                      child: Text(
                        g.plafond,
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: AppColors.secondary,
                          height: 1.3,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}

/// Exclusions officielles : intro + IMPORTANT + limites + 19 paragraphes
/// intégraux (source : TABLEAU DE GARANTIES & EXCLUSIONS).
class _OfficialExclusionsBlock extends StatelessWidget {
  const _OfficialExclusionsBlock();

  static const _bodyStyle = TextStyle(
    fontSize: 11.5,
    color: Color(0xFF1E293B),
    height: 1.4,
  );

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            color: AppColors.secondary,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: const Text(
              'Exclusions',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Colors.white,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final p in kIntroExclusionsOfficielles)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(p, style: _bodyStyle),
                  ),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF3EEF9),
                    borderRadius: BorderRadius.circular(6),
                    border: const Border(
                      left: BorderSide(color: AppColors.secondary, width: 3),
                    ),
                  ),
                  child: const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'IMPORTANT',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.secondary,
                          letterSpacing: 0.4,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        kImportantExclusionsOfficielles,
                        style: _bodyStyle,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Limites liées à la prise en charge par Mobility Health Care',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.secondary,
                  ),
                ),
                const SizedBox(height: 6),
                for (final p in kLimitesPriseEnChargeOfficielles)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(p, style: _bodyStyle),
                  ),
                const Divider(height: 24),
                for (final ex in kExclusionsOfficielles)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Exclusion – ${ex.numero}  ${ex.titre}',
                          style: const TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFF1E293B),
                            height: 1.35,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(ex.texte, style: _bodyStyle),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
