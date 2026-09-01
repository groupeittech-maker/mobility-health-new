class DestinationCityModel {
  final int id;
  final int paysId;
  final String nom;

  const DestinationCityModel({
    required this.id,
    required this.paysId,
    required this.nom,
  });

  factory DestinationCityModel.fromJson(Map<String, dynamic> json) {
    return DestinationCityModel(
      id: json['id'] as int,
      paysId: json['pays_id'] as int,
      nom: json['nom'] as String? ?? '',
    );
  }
}

class DestinationCountryModel {
  final int id;
  final String code;
  final String nom;
  final List<DestinationCityModel> villes;

  const DestinationCountryModel({
    required this.id,
    required this.code,
    required this.nom,
    required this.villes,
  });

  factory DestinationCountryModel.fromJson(Map<String, dynamic> json) {
    final rawCities = json['villes'] as List<dynamic>? ?? const [];
    return DestinationCountryModel(
      id: json['id'] as int,
      code: json['code'] as String? ?? '',
      nom: json['nom'] as String? ?? '',
      villes: rawCities
          .map((item) => DestinationCityModel.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class ReferenceCountryModel {
  final String code;
  final String nom;

  const ReferenceCountryModel({
    required this.code,
    required this.nom,
  });

  factory ReferenceCountryModel.fromJson(Map<String, dynamic> json) {
    return ReferenceCountryModel(
      code: (json['code'] as String? ?? '').trim().toUpperCase(),
      nom: json['nom'] as String? ?? '',
    );
  }
}
