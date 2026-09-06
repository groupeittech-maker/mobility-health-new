import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/services.dart';

import '../models/destination.dart';

const _countriesDevUrl = 'https://countries.dev/countries?limit=300';

Future<List<ReferenceCountryModel>> fetchReferenceCountriesFromAsset() async {
  final raw = await rootBundle.loadString('assets/data/reference_countries.json');
  return _parseReferenceCountriesJson(raw);
}

List<ReferenceCountryModel> parseReferenceCountriesJson(String raw) =>
    _parseReferenceCountriesJson(raw);

List<ReferenceCountryModel> _parseReferenceCountriesJson(String raw) {
  final decoded = (const JsonDecoder().convert(raw) as List<dynamic>?) ?? const [];
  return decoded
      .map((item) => ReferenceCountryModel.fromJson(item as Map<String, dynamic>))
      .where((country) => country.code.isNotEmpty && country.nom.isNotEmpty)
      .toList()
    ..sort((a, b) => a.nom.toLowerCase().compareTo(b.nom.toLowerCase()));
}

Future<List<ReferenceCountryModel>> fetchReferenceCountriesFromCountriesDev() async {
  final dio = Dio(
    BaseOptions(
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 20),
    ),
  );
  final response = await dio.get<List<dynamic>>(_countriesDevUrl);
  final items = response.data ?? const [];
  final countries = <ReferenceCountryModel>[];

  for (final raw in items) {
    if (raw is! Map<String, dynamic>) continue;
    final code = (raw['alpha2Code'] as String? ?? '').trim().toUpperCase();
    final nom = (raw['name'] as String? ?? '').trim();
    if (code.isEmpty || nom.isEmpty) continue;
    countries.add(ReferenceCountryModel(code: code, nom: nom));
  }

  countries.sort((a, b) => a.nom.toLowerCase().compareTo(b.nom.toLowerCase()));
  return countries;
}

/// Ordre : JSON embarqué (FR) → countries.dev → liste minimale.
Future<List<ReferenceCountryModel>> fetchReferenceCountriesFallback() async {
  try {
    final assetCountries = await fetchReferenceCountriesFromAsset();
    if (assetCountries.isNotEmpty) {
      return assetCountries;
    }
  } catch (_) {
    // Ignorer : tenter countries.dev.
  }

  try {
    final remoteCountries = await fetchReferenceCountriesFromCountriesDev();
    if (remoteCountries.isNotEmpty) {
      return remoteCountries;
    }
  } catch (_) {
    // Ignorer : tenter la liste minimale.
  }

  return List<ReferenceCountryModel>.from(kLocalReferenceCountriesFallback);
}

/// Liste locale minimale si toutes les autres sources échouent.
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
