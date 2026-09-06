import 'package:dio/dio.dart';

import '../models/destination.dart';

const _restCountriesUrl =
    'https://restcountries.com/v3.1/all?fields=cca2,translations';

/// Liste locale minimale si l'API MHC et RestCountries sont indisponibles.
const List<ReferenceCountryModel> kLocalReferenceCountriesFallback = [
  ReferenceCountryModel(code: 'FR', nom: 'France'),
  ReferenceCountryModel(code: 'BE', nom: 'Belgique'),
  ReferenceCountryModel(code: 'CH', nom: 'Suisse'),
  ReferenceCountryModel(code: 'SN', nom: 'Sénégal'),
  ReferenceCountryModel(code: 'CI', nom: 'Côte d\'Ivoire'),
  ReferenceCountryModel(code: 'CM', nom: 'Cameroun'),
  ReferenceCountryModel(code: 'MA', nom: 'Maroc'),
  ReferenceCountryModel(code: 'TN', nom: 'Tunisie'),
  ReferenceCountryModel(code: 'DZ', nom: 'Algérie'),
  ReferenceCountryModel(code: 'DE', nom: 'Allemagne'),
  ReferenceCountryModel(code: 'GB', nom: 'Royaume-Uni'),
  ReferenceCountryModel(code: 'US', nom: 'États-Unis'),
  ReferenceCountryModel(code: 'CA', nom: 'Canada'),
];

Future<List<ReferenceCountryModel>> fetchReferenceCountriesFallback() async {
  try {
    final dio = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 20),
      ),
    );
    final response = await dio.get<List<dynamic>>(_restCountriesUrl);
    final items = response.data ?? const [];
    final countries = <ReferenceCountryModel>[];

    for (final raw in items) {
      if (raw is! Map<String, dynamic>) continue;
      final code = (raw['cca2'] as String? ?? '').trim().toUpperCase();
      final translations = raw['translations'] as Map<String, dynamic>? ?? {};
      final french = translations['fra'] as Map<String, dynamic>? ?? {};
      final nom = (french['common'] as String? ?? '').trim();
      if (code.isEmpty || nom.isEmpty) continue;
      countries.add(ReferenceCountryModel(code: code, nom: nom));
    }

    countries.sort((a, b) => a.nom.toLowerCase().compareTo(b.nom.toLowerCase()));
    if (countries.isNotEmpty) {
      return countries;
    }
  } catch (_) {
    // Ignorer : on retombe sur la liste locale.
  }

  return List<ReferenceCountryModel>.from(kLocalReferenceCountriesFallback);
}
