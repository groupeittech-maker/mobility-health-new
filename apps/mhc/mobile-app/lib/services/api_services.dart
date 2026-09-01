import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../core/network/api_client.dart';
import '../models/destination.dart';
import '../models/product.dart';
import '../models/subscription.dart';
import '../models/subscription_quote.dart';

/// Produits (GET /products, GET /products/:id) - public.
class ProductsService {
  final ApiClient _api = ApiClient();

  Future<List<ProductModel>> getProducts({
    int skip = 0,
    int limit = 100,
    bool? estActif = true,
    bool filterByVoyageAssureur = false,
    int? residenceCountryId,
    int? destinationCountryId,
    String? residenceCountryName,
    String? destinationCountryName,
    String? zoneCode,
    String? canalDistribution,
    int? courtierId,
  }) async {
    final qp = <String, dynamic>{
      'skip': skip,
      'limit': limit,
    };
    if (estActif != null) qp['est_actif'] = estActif;
    if (filterByVoyageAssureur) qp['filter_by_voyage_assureur'] = true;
    if (residenceCountryId != null) qp['residence_country_id'] = residenceCountryId;
    if (destinationCountryId != null) qp['destination_country_id'] = destinationCountryId;
    if (residenceCountryName != null && residenceCountryName.trim().isNotEmpty) {
      qp['residence_country_name'] = residenceCountryName.trim();
    }
    if (destinationCountryName != null && destinationCountryName.trim().isNotEmpty) {
      qp['destination_country_name'] = destinationCountryName.trim();
    }
    if (zoneCode != null && zoneCode.trim().isNotEmpty) qp['zone_code'] = zoneCode.trim();
    if (canalDistribution != null && canalDistribution.trim().isNotEmpty) {
      qp['canal_distribution'] = canalDistribution.trim();
    }
    if (courtierId != null) qp['courtier_id'] = courtierId;

    final list = await _api.get<List<dynamic>>(
      '/products/',
      queryParameters: qp,
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => ProductModel.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<ProductModel> getProduct(int productId) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/products/$productId',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return ProductModel.fromJson(data);
  }
}

/// Souscriptions (GET /subscriptions/, POST /subscriptions/start) - authentifié.
class SubscriptionsService {
  final ApiClient _api = ApiClient();

  static List<SubscriptionModel>? _listCache;
  static DateTime? _listCacheTime;
  static const Duration _listCacheTtl = Duration(minutes: 2);

  static void clearSubscriptionsCache() {
    _listCache = null;
    _listCacheTime = null;
  }

  /// Affichage immédiat (onglet Historique) si le cache est encore valide.
  static List<SubscriptionModel>? peekSubscriptionsCache() {
    final now = DateTime.now();
    if (_listCache == null ||
        _listCacheTime == null ||
        now.difference(_listCacheTime!) >= _listCacheTtl) {
      return null;
    }
    return List<SubscriptionModel>.from(_listCache!);
  }

  static void warmSubscriptionsCache() {
    SubscriptionsService().getSubscriptions(limit: 1000).ignore();
  }

  Future<List<SubscriptionModel>> getSubscriptions({
    int limit = 1000,
    bool forceRefresh = false,
  }) async {
    final now = DateTime.now();
    if (!forceRefresh &&
        limit == 1000 &&
        _listCache != null &&
        _listCacheTime != null &&
        now.difference(_listCacheTime!) < _listCacheTtl) {
      return List<SubscriptionModel>.from(_listCache!);
    }

    final list = await _api.get<List<dynamic>>(
      '/subscriptions/',
      queryParameters: {'limit': limit},
      fromJson: (d) => d as List<dynamic>,
    );
    final parsed =
        list.map((e) => SubscriptionModel.fromJson(e as Map<String, dynamic>)).toList();
    if (limit == 1000) {
      _listCache = parsed;
      _listCacheTime = now;
    }
    return parsed;
  }

  /// Obtenir une souscription par ID (GET /subscriptions/:id).
  Future<SubscriptionModel> getSubscription(int subscriptionId) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/subscriptions/$subscriptionId',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return SubscriptionModel.fromJson(data);
  }

  /// Demander la résiliation d'une souscription (POST /subscriptions/:id/request-resiliation).
  Future<SubscriptionModel> requestResiliation(int subscriptionId, {String? notes}) async {
    final body = <String, dynamic>{};
    if (notes != null && notes.trim().isNotEmpty) body['notes'] = notes.trim();
    final data = await _api.post<Map<String, dynamic>>(
      '/subscriptions/$subscriptionId/request-resiliation',
      body: body,
      fromJson: (d) => d as Map<String, dynamic>,
    );
    clearSubscriptionsCache();
    return SubscriptionModel.fromJson(data);
  }

  /// Démarrer une souscription (POST /subscriptions/start).
  Future<SubscriptionModel> startSubscription({
    required int produitAssuranceId,
    int? projetVoyageId,
    DateTime? dateDebut,
    String? notes,
    int? destinationCountryId,
    String? canalDistribution,
    int? courtierId,
    String? zoneCode,
    int? dureeJours,
    int? age,
  }) async {
    final body = <String, dynamic>{
      'produit_assurance_id': produitAssuranceId,
      if (projetVoyageId != null) 'projet_voyage_id': projetVoyageId,
      if (dateDebut != null) 'date_debut': dateDebut.toIso8601String(),
      if (notes != null) 'notes': notes,
      if (destinationCountryId != null) 'destination_country_id': destinationCountryId,
      if (canalDistribution != null) 'canal_distribution': canalDistribution,
      if (courtierId != null) 'courtier_id': courtierId,
      if (zoneCode != null) 'zone_code': zoneCode,
      if (dureeJours != null) 'duree_jours': dureeJours,
      if (age != null) 'age': age,
    };
    final data = await _api.post<Map<String, dynamic>>(
      '/subscriptions/start',
      body: body,
      fromJson: (d) => d as Map<String, dynamic>,
    );
    clearSubscriptionsCache();
    return SubscriptionModel.fromJson(data);
  }

  /// Devis pour l’étape « choix produit » (même moteur que /start, sans souscription).
  Future<QuotePricesResult> quotePrices({
    required int projetVoyageId,
    required List<int> produitAssuranceIds,
    int? destinationCountryId,
    int? residenceCountryId,
    int? dureeJours,
    int? age,
  }) async {
    final body = <String, dynamic>{
      'projet_voyage_id': projetVoyageId,
      'produit_assurance_ids': produitAssuranceIds,
      if (destinationCountryId != null) 'destination_country_id': destinationCountryId,
      if (residenceCountryId != null) 'residence_country_id': residenceCountryId,
      if (dureeJours != null) 'duree_jours': dureeJours,
      if (age != null) 'age': age,
    };
    final data = await _api.post<Map<String, dynamic>>(
      '/subscriptions/quote-prices',
      body: body,
      fromJson: (d) => d as Map<String, dynamic>,
    );
    final list = data['quotes'];
    final out = <int, SubscriptionQuoteLine>{};
    if (list is List) {
      for (final q in list) {
        if (q is! Map) continue;
        final line = SubscriptionQuoteLine.fromJson(Map<String, dynamic>.from(q));
        if (line.produitAssuranceId > 0) {
          out[line.produitAssuranceId] = line;
        }
      }
    }
    final surprimes = <SurprimeAgeRow>[];
    final sa = data['surprimes_age_reference'];
    if (sa is List) {
      for (final row in sa) {
        if (row is Map) {
          surprimes.add(SurprimeAgeRow.fromJson(Map<String, dynamic>.from(row)));
        }
      }
    }
    final fp = data['frais_services_sur_prime_pct'];
    final fraisPct = fp is num ? fp.toDouble() : double.tryParse(fp?.toString() ?? '') ?? 15;
    return QuotePricesResult(
      byProductId: out,
      surprimesAge: surprimes,
      fraisSurPrimePct: fraisPct,
    );
  }
}

class CourtiersService {
  final ApiClient _api = ApiClient();

  Future<List<Map<String, dynamic>>> getCourtiers({int? assureurId}) async {
    try {
      final list = await _api.get<List<dynamic>>(
        '/courtiers/',
        queryParameters: {
          if (assureurId != null) 'assureur_id': assureurId,
        },
        fromJson: (d) => d as List<dynamic>,
      );
      return list.map((e) => e as Map<String, dynamic>).toList();
    } on DioException catch (e) {
      // Compatibilité serveur: si l'endpoint n'est pas encore déployé,
      // on n'interrompt pas le parcours de souscription.
      if (e.response?.statusCode == 404) {
        return const [];
      }
      rethrow;
    }
  }
}

/// Projets de voyage (GET/POST /voyages/) - authentifié.
class VoyagesService {
  final ApiClient _api = ApiClient();

  Future<List<ProjetVoyageModel>> getVoyages({int skip = 0, int limit = 100}) async {
    final list = await _api.get<List<dynamic>>(
      '/voyages/',
      queryParameters: {'skip': skip, 'limit': limit},
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => ProjetVoyageModel.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<ProjetVoyageModel> createVoyage({
    required String titre,
    required String destination,
    required DateTime dateDepart,
    String? description,
    DateTime? dateRetour,
    int nombreParticipants = 1,
    String? notes,
    int? destinationCountryId,
  }) async {
    final body = <String, dynamic>{
      'titre': titre,
      'destination': destination,
      'date_depart': dateDepart.toIso8601String(),
      'nombre_participants': nombreParticipants,
      if (description != null) 'description': description,
      if (dateRetour != null) 'date_retour': dateRetour.toIso8601String(),
      if (notes != null) 'notes': notes,
      if (destinationCountryId != null) 'destination_country_id': destinationCountryId,
    };
    final data = await _api.post<Map<String, dynamic>>(
      '/voyages/',
      body: body,
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return ProjetVoyageModel.fromJson(data);
  }
}

/// Destinations (GET /destinations/countries) - authentifié.
class DestinationsService {
  final ApiClient _api = ApiClient();

  /// Cache session : évite de recharger la liste complète à chaque ouverture d’écran.
  static List<DestinationCountryModel>? _countriesCacheNoCities;
  static DateTime? _countriesCacheTime;
  static const Duration _countriesCacheTtl = Duration(minutes: 45);

  /// Invalider le cache (ex. après déconnexion ou si les données pays ont changé côté serveur).
  static void clearDestinationCountriesCache() {
    _countriesCacheNoCities = null;
    _countriesCacheTime = null;
  }

  /// Lecture synchrone du cache pays (sans réseau) si encore valide — pour afficher l’UI tout de suite.
  static List<DestinationCountryModel>? peekDestinationCountriesCache() {
    final now = DateTime.now();
    if (_countriesCacheNoCities == null ||
        _countriesCacheTime == null ||
        now.difference(_countriesCacheTime!) >= _countriesCacheTtl) {
      return null;
    }
    return List<DestinationCountryModel>.from(_countriesCacheNoCities!);
  }

  /// Précharge la liste des pays dès que la session est prête (réduit la latence à l’étape voyage).
  static void warmDestinationCountriesCache() {
    DestinationsService().getDestinationCountries(includeCities: false).ignore();
  }

  Future<List<DestinationCountryModel>> getDestinationCountries({
    bool actifSeulement = true,
    bool includeCities = true,
    bool forceRefresh = false,
  }) async {
    final now = DateTime.now();
    if (!forceRefresh &&
        !includeCities &&
        actifSeulement &&
        _countriesCacheNoCities != null &&
        _countriesCacheTime != null &&
        now.difference(_countriesCacheTime!) < _countriesCacheTtl) {
      return List<DestinationCountryModel>.from(_countriesCacheNoCities!);
    }

    final list = await _api.get<List<dynamic>>(
      '/destinations/countries',
      queryParameters: {
        'actif_seulement': actifSeulement,
        'include_cities': includeCities,
      },
      fromJson: (d) => d as List<dynamic>,
    );
    final parsed = list
        .map(
          (item) => DestinationCountryModel.fromJson(
            item as Map<String, dynamic>,
          ),
        )
        .toList();
    if (!includeCities && actifSeulement) {
      _countriesCacheNoCities = parsed;
      _countriesCacheTime = now;
    }
    return parsed;
  }

  Future<List<DestinationCityModel>> getDestinationCities(
    int countryId, {
    bool actifSeulement = true,
  }) async {
    final list = await _api.get<List<dynamic>>(
      '/destinations/countries/$countryId/cities',
      queryParameters: {'actif_seulement': actifSeulement},
      fromJson: (d) => d as List<dynamic>,
    );
    return list
        .map(
          (item) => DestinationCityModel.fromJson(
            item as Map<String, dynamic>,
          ),
        )
        .toList();
  }

  Future<List<ReferenceCountryModel>> getReferenceCountries({
    bool forceRefresh = false,
  }) async {
    final list = await _api.get<List<dynamic>>(
      '/destinations/reference-countries',
      queryParameters: {'force_refresh': forceRefresh},
      fromJson: (d) => d as List<dynamic>,
    );
    return list
        .map(
          (item) => ReferenceCountryModel.fromJson(
            item as Map<String, dynamic>,
          ),
        )
        .toList();
  }
}

/// Health check (GET /health).
class HealthService {
  final ApiClient _api = ApiClient();

  Future<Map<String, dynamic>> health() async {
    return _api.get<Map<String, dynamic>>(
      '/health',
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }
}

/// Alerte SOS (POST /sos/trigger, GET /sos/) – déclencher et lister les alertes.
class SosService {
  final ApiClient _api = ApiClient();

  static List<Map<String, dynamic>>? _alertesCache;
  static DateTime? _alertesCacheTime;
  static const Duration _alertesCacheTtl = Duration(seconds: 45);

  static void clearSosAlertesCache() {
    _alertesCache = null;
    _alertesCacheTime = null;
  }

  static List<Map<String, dynamic>>? peekSosAlertesCache() {
    final now = DateTime.now();
    if (_alertesCache == null ||
        _alertesCacheTime == null ||
        now.difference(_alertesCacheTime!) >= _alertesCacheTtl) {
      return null;
    }
    return List<Map<String, dynamic>>.from(_alertesCache!);
  }

  static void warmSosAlertesCache() {
    SosService().getAlertes().ignore();
  }

  /// Déclencher une alerte SOS (comme sur l’application web).
  Future<Map<String, dynamic>> triggerSos({
    required double latitude,
    required double longitude,
    String? adresse,
    String? description,
    String priorite = 'normale',
    int? souscriptionId,
  }) async {
    final body = <String, dynamic>{
      'latitude': latitude,
      'longitude': longitude,
      'priorite': priorite,
      if (adresse != null && adresse.isNotEmpty) 'adresse': adresse,
      if (description != null && description.isNotEmpty) 'description': description,
      if (souscriptionId != null) 'souscription_id': souscriptionId,
    };
    final data = await _api.post<Map<String, dynamic>>(
      '/sos/trigger',
      body: body,
      fromJson: (d) => d as Map<String, dynamic>,
    );
    clearSosAlertesCache();
    return data;
  }

  /// Liste des alertes de l’utilisateur.
  Future<List<Map<String, dynamic>>> getAlertes({
    int skip = 0,
    int limit = 100,
    bool forceRefresh = false,
  }) async {
    final now = DateTime.now();
    if (!forceRefresh &&
        skip == 0 &&
        limit == 100 &&
        _alertesCache != null &&
        _alertesCacheTime != null &&
        now.difference(_alertesCacheTime!) < _alertesCacheTtl) {
      return List<Map<String, dynamic>>.from(_alertesCache!);
    }

    final list = await _api.get<List<dynamic>>(
      '/sos/',
      queryParameters: {'skip': skip, 'limit': limit},
      fromJson: (d) => d as List<dynamic>,
    );
    final parsed = list.map((e) => e as Map<String, dynamic>).toList();
    if (skip == 0 && limit == 100) {
      _alertesCache = parsed;
      _alertesCacheTime = now;
    }
    return parsed;
  }
}

/// Séjours hospitaliers (GET /hospital-sinistres/hospital-stays) – historique hospitalisations.
class HospitalStaysService {
  final ApiClient _api = ApiClient();

  static List<Map<String, dynamic>>? _staysCache;
  static DateTime? _staysCacheTime;
  static const Duration _staysCacheTtl = Duration(seconds: 45);

  static void clearHospitalStaysCache() {
    _staysCache = null;
    _staysCacheTime = null;
  }

  static List<Map<String, dynamic>>? peekHospitalStaysCache() {
    final now = DateTime.now();
    if (_staysCache == null ||
        _staysCacheTime == null ||
        now.difference(_staysCacheTime!) >= _staysCacheTtl) {
      return null;
    }
    return List<Map<String, dynamic>>.from(_staysCache!);
  }

  static void warmHospitalStaysCache() {
    HospitalStaysService().getHospitalStays().ignore();
  }

  Future<List<Map<String, dynamic>>> getHospitalStays({
    int skip = 0,
    int limit = 50,
    bool forceRefresh = false,
  }) async {
    final now = DateTime.now();
    if (!forceRefresh &&
        skip == 0 &&
        limit == 50 &&
        _staysCache != null &&
        _staysCacheTime != null &&
        now.difference(_staysCacheTime!) < _staysCacheTtl) {
      return List<Map<String, dynamic>>.from(_staysCache!);
    }

    final list = await _api.get<List<dynamic>>(
      '/hospital-sinistres/hospital-stays',
      queryParameters: {'skip': skip, 'limit': limit},
      fromJson: (d) => d as List<dynamic>,
    );
    final parsed = list.map((e) => e as Map<String, dynamic>).toList();
    if (skip == 0 && limit == 50) {
      _staysCache = parsed;
      _staysCacheTime = now;
    }
    return parsed;
  }
}

/// Questionnaires (POST /subscriptions/:id/questionnaire/medical, administratif, etc.)
class QuestionnaireService {
  final ApiClient _api = ApiClient();

  Future<Map<String, dynamic>> submitMedical(int subscriptionId, Map<String, dynamic> reponses) async {
    return _api.post<Map<String, dynamic>>(
      '/subscriptions/$subscriptionId/questionnaire/medical',
      body: reponses,
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> submitAdministratif(int subscriptionId, Map<String, dynamic> reponses) async {
    return _api.post<Map<String, dynamic>>(
      '/subscriptions/$subscriptionId/questionnaire/administratif',
      body: reponses,
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }
}

/// Paiements – une seule source de vérité : POST /payments/confirm génère l'attestation côté backend (comme le web).
class PaymentsService {
  final ApiClient _api = ApiClient();

  /// Confirmer le paiement et générer l'attestation provisoire (même flux que l'app web).
  /// À utiliser pour "Payer maintenant" : le backend crée le paiement + l'attestation.
  Future<Map<String, dynamic>> confirm({
    required int subscriptionId,
    required double montant,
    String methodePaiement = 'carte_bancaire',
  }) async {
    return _api.post<Map<String, dynamic>>(
      '/payments/confirm',
      body: {
        // Envoyer les noms de champs attendus par le backend.
        'souscription_id': subscriptionId,
        // Envoyer le montant en chaîne décimale évite les surprises de sérialisation JSON.
        'montant': montant.toStringAsFixed(2),
        'methode_paiement': methodePaiement,
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  /// Initier un paiement (URL checkout web) – à éviter pour le flux mobile, préférer [confirm].
  Future<Map<String, dynamic>> initiate({
    required int subscriptionId,
    required double amount,
    String paymentType = 'carte_bancaire',
  }) async {
    return _api.post<Map<String, dynamic>>(
      '/payments/initiate',
      body: {
        'subscription_id': subscriptionId,
        'amount': amount,
        'payment_type': paymentType,
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> getStatus(int paymentId) async {
    return _api.get<Map<String, dynamic>>(
      '/payments/$paymentId/status',
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }
}

/// Attestations (GET /subscriptions/:id/attestations, GET /users/me/attestations)
class AttestationsService {
  final ApiClient _api = ApiClient();

  static List<Map<String, dynamic>>? _userAttestationsCache;
  static DateTime? _userAttestationsCacheTime;
  static const Duration _userAttestationsCacheTtl = Duration(minutes: 2);

  static void clearUserAttestationsCache() {
    _userAttestationsCache = null;
    _userAttestationsCacheTime = null;
  }

  static void warmUserAttestationsCache() {
    AttestationsService().getUserAttestations().ignore();
  }

  /// Liste des attestations de l'utilisateur connecté.
  Future<List<Map<String, dynamic>>> getUserAttestations({
    bool forceRefresh = false,
  }) async {
    final now = DateTime.now();
    if (!forceRefresh &&
        _userAttestationsCache != null &&
        _userAttestationsCacheTime != null &&
        now.difference(_userAttestationsCacheTime!) < _userAttestationsCacheTtl) {
      return List<Map<String, dynamic>>.from(_userAttestationsCache!);
    }

    final list = await _api.get<List<dynamic>>(
      '/users/me/attestations',
      fromJson: (d) => d as List<dynamic>,
    );
    final parsed = list.map((e) => e as Map<String, dynamic>).toList();
    _userAttestationsCache = parsed;
    _userAttestationsCacheTime = now;
    return parsed;
  }

  Future<List<Map<String, dynamic>>> getSubscriptionAttestations(int subscriptionId) async {
    final list = await _api.get<List<dynamic>>(
      '/subscriptions/$subscriptionId/attestations',
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  /// Télécharge le PDF d'une attestation et retourne le chemin du fichier local.
  Future<String> downloadAttestationPdf(int attestationId, {String? numeroAttestation}) async {
    final response = await _api.dio.get<List<int>>(
      '/attestations/$attestationId/download',
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) throw Exception('PDF vide reçu');
    final dir = await getTemporaryDirectory();
    final name = 'attestation-${numeroAttestation ?? attestationId}.pdf'
        .replaceAll(RegExp(r'[^\w\-.]'), '_');
    final file = File('${dir.path}/$name');
    await file.writeAsBytes(bytes);
    return file.path;
  }

  /// Télécharge l'e-carte (PNG) d'une attestation et retourne le chemin du fichier local.
  Future<String> downloadEcard(int attestationId, {String? numeroAttestation}) async {
    final response = await _api.dio.get<List<int>>(
      '/attestations/$attestationId/ecard/download',
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) throw Exception('E-carte vide reçue');
    final dir = await getTemporaryDirectory();
    final name = 'ecarte-${numeroAttestation ?? attestationId}.png'
        .replaceAll(RegExp(r'[^\w\-.]'), '_');
    final file = File('${dir.path}/$name');
    await file.writeAsBytes(bytes);
    return file.path;
  }
}

/// Assureurs partenaires (GET /assureurs) – back office, pour afficher les logos.
class AssureursService {
  final ApiClient _api = ApiClient();

  Future<List<Map<String, dynamic>>> getAssureurs() async {
    final list = await _api.get<List<dynamic>>(
      '/assureurs',
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => e as Map<String, dynamic>).toList();
  }
}

/// Documents projet (POST /voyages/:projetId/documents – upload photo/document)
class VoyageDocumentsService {
  final ApiClient _api = ApiClient();

  Future<Map<String, dynamic>> uploadDocument({
    required int projetId,
    required String filePath,
    required String docType,
  }) async {
    return _api.postMultipart<Map<String, dynamic>>(
      '/voyages/$projetId/documents',
      fields: {'doc_type': docType},
      fileKey: 'file',
      filePath: filePath,
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }
}
