/// Produit d'assurance (ProduitAssuranceResponse).
class ProductModel {
  final int id;
  final String code;
  final String nom;
  final String? description;
  final bool estActif;
  final String? assureur;
  final int? assureurId;
  final String? imageUrl;
  final double cout;
  final String? currency;
  final int? dureeMinJours;
  final int? dureeMaxJours;
  final int? dureeValiditeJours;
  final bool reconductionPossible;
  final bool couvertureMultiEntrees;
  final int? ageMinimum;
  final int? ageMaximum;
  final String? conditions;
  final String? conditionsGeneralesPdfUrl;
  final List<Map<String, dynamic>>? garanties;
  final Map<String, dynamic>? primesGenerees;
  final List<Map<String, dynamic>>? exclusionsGenerales;
  final Map<String, dynamic>? zonesGeographiques;

  ProductModel({
    required this.id,
    required this.code,
    required this.nom,
    this.description,
    this.estActif = true,
    this.assureur,
    this.assureurId,
    this.imageUrl,
    required this.cout,
    this.currency,
    this.dureeMinJours,
    this.dureeMaxJours,
    this.dureeValiditeJours,
    this.reconductionPossible = false,
    this.couvertureMultiEntrees = false,
    this.ageMinimum,
    this.ageMaximum,
    this.conditions,
    this.conditionsGeneralesPdfUrl,
    this.garanties,
    this.primesGenerees,
    this.exclusionsGenerales,
    this.zonesGeographiques,
  });

  /// Nombre indicatif de zones / pays éligibles (données fiche produit).
  int get geographicalZonesCount {
    final z = zonesGeographiques;
    if (z == null) return 0;
    for (final key in ['zones', 'pays_eligibles', 'paysEligibles']) {
      final v = z[key];
      if (v is List && v.isNotEmpty) return v.length;
    }
    return 0;
  }

  factory ProductModel.fromJson(Map<String, dynamic> json) {
    List<Map<String, dynamic>>? parseList(dynamic v) {
      if (v == null) return null;
      if (v is List) return v.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      return null;
    }
    Map<String, dynamic>? parseMap(dynamic v) {
      if (v == null) return null;
      if (v is Map) return Map<String, dynamic>.from(v);
      return null;
    }
    return ProductModel(
      id: json['id'] as int,
      code: json['code'] as String,
      nom: json['nom'] as String,
      description: json['description'] as String?,
      estActif: json['est_actif'] as bool? ?? true,
      assureur: json['assureur'] as String?,
      assureurId: json['assureur_id'] as int?,
      imageUrl: json['image_url'] as String?,
      cout: (json['cout'] is num) ? (json['cout'] as num).toDouble() : double.tryParse(json['cout']?.toString() ?? '0') ?? 0,
      currency: json['currency'] as String?,
      dureeMinJours: json['duree_min_jours'] as int?,
      dureeMaxJours: json['duree_max_jours'] as int?,
      dureeValiditeJours: json['duree_validite_jours'] as int?,
      reconductionPossible: json['reconduction_possible'] as bool? ?? false,
      couvertureMultiEntrees: json['couverture_multi_entrees'] as bool? ?? false,
      ageMinimum: json['age_minimum'] as int?,
      ageMaximum: json['age_maximum'] as int?,
      conditions: json['conditions'] as String?,
      conditionsGeneralesPdfUrl: json['conditions_generales_pdf_url'] as String?,
      garanties: parseList(json['garanties']),
      primesGenerees: parseMap(json['primes_generees']),
      exclusionsGenerales: parseList(json['exclusions_generales']),
      zonesGeographiques: parseMap(json['zones_geographiques']),
    );
  }
}
