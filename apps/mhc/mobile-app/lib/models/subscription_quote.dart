/// Ligne de référence surprime âge (réponse globale quote-prices).
class SurprimeAgeRow {
  final String tranche;
  final double pct;

  SurprimeAgeRow({required this.tranche, required this.pct});

  factory SurprimeAgeRow.fromJson(Map<String, dynamic> json) {
    final p = json['pct'];
    return SurprimeAgeRow(
      tranche: json['tranche']?.toString() ?? '',
      pct: p is num ? p.toDouble() : double.tryParse(p?.toString() ?? '0') ?? 0,
    );
  }
}

/// Résultat complet de POST /subscriptions/quote-prices.
class QuotePricesResult {
  QuotePricesResult({
    required this.byProductId,
    required this.surprimesAge,
    required this.fraisSurPrimePct,
  });

  final Map<int, SubscriptionQuoteLine> byProductId;
  final List<SurprimeAgeRow> surprimesAge;
  final double fraisSurPrimePct;

  factory QuotePricesResult.empty() {
    return QuotePricesResult(
      byProductId: {},
      surprimesAge: [],
      fraisSurPrimePct: 15,
    );
  }
}

/// Ligne de devis (POST /subscriptions/quote-prices).
class SubscriptionQuoteLine {
  final int produitAssuranceId;
  final double prixApplique;
  final double? primeAssurance;
  final double? fraisServices;
  final String? zoneGeographiqueCode;
  final String? zoneLibelleFr;
  final String? trancheDureeCode;
  final int? dureeMinJours;
  final int? dureeMaxJours;

  SubscriptionQuoteLine({
    required this.produitAssuranceId,
    required this.prixApplique,
    this.primeAssurance,
    this.fraisServices,
    this.zoneGeographiqueCode,
    this.zoneLibelleFr,
    this.trancheDureeCode,
    this.dureeMinJours,
    this.dureeMaxJours,
  });

  factory SubscriptionQuoteLine.fromJson(Map<String, dynamic> json) {
    double? optNum(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      return double.tryParse(v.toString());
    }

    int? optInt(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toInt();
      return int.tryParse(v.toString());
    }

    final id = json['produit_assurance_id'];
    final px = json['prix_applique'];
    return SubscriptionQuoteLine(
      produitAssuranceId: id is num ? id.toInt() : 0,
      prixApplique: px is num ? px.toDouble() : double.tryParse(px?.toString() ?? '0') ?? 0,
      primeAssurance: optNum(json['prime_assurance']),
      fraisServices: optNum(json['frais_services']),
      zoneGeographiqueCode: json['zone_geographique_code'] as String?,
      zoneLibelleFr: json['zone_libelle_fr'] as String?,
      trancheDureeCode: json['tranche_duree_code'] as String?,
      dureeMinJours: optInt(json['duree_min_jours']),
      dureeMaxJours: optInt(json['duree_max_jours']),
    );
  }

  bool get hasBreakdown =>
      primeAssurance != null && fraisServices != null;

  /// Libellé tranche durée (grille voyage).
  String? get trancheDureeLabelFr {
    final c = trancheDureeCode;
    if (c == null || c.isEmpty) return null;
    const m = {
      '1_7': '1 à 7 jours',
      '8_15': '8 à 15 jours',
      '16_30': '16 à 30 jours',
      '31_60': '31 à 60 jours',
      '61_90': '61 à 90 jours',
    };
    if (m.containsKey(c)) return m[c];
    if (dureeMinJours != null && dureeMaxJours != null) {
      return '$dureeMinJours–$dureeMaxJours jours';
    }
    return c;
  }
}
