import '../core/network/api_client.dart';

/// API des avenants de police (suspension) côté assuré.
class AvenantService {
  AvenantService._();
  static final AvenantService instance = AvenantService._();

  final ApiClient _api = ApiClient();

  /// Catalogue des motifs et pièces (clé → libellé).
  Future<Map<String, dynamic>> fetchCatalog() async {
    final data = await _api.get<Map<String, dynamic>>(
      '/avenants/catalogue',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  /// Demande de suspension par le souscripteur.
  Future<Map<String, dynamic>> requestSuspension(
    int subscriptionId, {
    required List<String> motifs,
    String? motifAutre,
    List<String> pieces = const [],
  }) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/subscriptions/$subscriptionId/avenant-suspension',
      body: {
        'motifs': motifs,
        if (motifAutre != null && motifAutre.trim().isNotEmpty) 'motif_autre': motifAutre.trim(),
        'pieces': pieces,
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  /// Liste des avenants d'une souscription.
  Future<List<Map<String, dynamic>>> listAvenants(int subscriptionId) async {
    final list = await _api.get<List<dynamic>>(
      '/subscriptions/$subscriptionId/avenants',
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  /// Téléverse une pièce justificative sur une demande de suspension.
  Future<void> uploadPiece(int avenantId, String filePath) async {
    await _api.postMultipart<dynamic>(
      '/avenants/$avenantId/pieces',
      fields: const {},
      fileKey: 'file',
      filePath: filePath,
      fromJson: (d) => d,
    );
  }
}
