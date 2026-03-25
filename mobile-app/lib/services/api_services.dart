import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../core/network/api_client.dart';
import '../models/destination.dart';
import '../models/product.dart';
import '../models/subscription.dart';

/// Produits (GET /products, GET /products/:id) - public.
class ProductsService {
  final ApiClient _api = ApiClient();

  Future<List<ProductModel>> getProducts({int skip = 0, int limit = 100, bool? estActif = true}) async {
    final list = await _api.get<List<dynamic>>(
      '/products/',
      queryParameters: {'skip': skip, 'limit': limit, 'est_actif': estActif},
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

  Future<List<SubscriptionModel>> getSubscriptions({int limit = 1000}) async {
    final list = await _api.get<List<dynamic>>(
      '/subscriptions/',
      queryParameters: {'limit': limit},
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => SubscriptionModel.fromJson(e as Map<String, dynamic>)).toList();
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
    return SubscriptionModel.fromJson(data);
  }

  /// Démarrer une souscription (POST /subscriptions/start).
  Future<SubscriptionModel> startSubscription({
    required int produitAssuranceId,
    int? projetVoyageId,
    DateTime? dateDebut,
    String? notes,
    int? destinationCountryId,
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
      if (zoneCode != null) 'zone_code': zoneCode,
      if (dureeJours != null) 'duree_jours': dureeJours,
      if (age != null) 'age': age,
    };
    final data = await _api.post<Map<String, dynamic>>(
      '/subscriptions/start',
      body: body,
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return SubscriptionModel.fromJson(data);
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
    return data;
  }

  /// Liste des alertes de l’utilisateur.
  Future<List<Map<String, dynamic>>> getAlertes({int skip = 0, int limit = 100}) async {
    final list = await _api.get<List<dynamic>>(
      '/sos/',
      queryParameters: {'skip': skip, 'limit': limit},
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => e as Map<String, dynamic>).toList();
  }
}

/// Séjours hospitaliers (GET /hospital-sinistres/hospital-stays) – historique hospitalisations.
class HospitalStaysService {
  final ApiClient _api = ApiClient();

  Future<List<Map<String, dynamic>>> getHospitalStays({int skip = 0, int limit = 50}) async {
    final list = await _api.get<List<dynamic>>(
      '/hospital-sinistres/hospital-stays',
      queryParameters: {'skip': skip, 'limit': limit},
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => e as Map<String, dynamic>).toList();
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

  /// Liste des attestations de l'utilisateur connecté.
  Future<List<Map<String, dynamic>>> getUserAttestations() async {
    final list = await _api.get<List<dynamic>>(
      '/users/me/attestations',
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => e as Map<String, dynamic>).toList();
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
