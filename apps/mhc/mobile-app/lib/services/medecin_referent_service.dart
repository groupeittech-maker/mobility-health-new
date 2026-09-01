import '../core/network/api_client.dart';
import '../models/referent_pipeline.dart';

/// API médecin référent MH : dossiers SOS, validation urgences, rapports séjour, factures médicales, notifications.
class MedecinReferentService {
  MedecinReferentService._();
  static final MedecinReferentService instance = MedecinReferentService._();

  final ApiClient _api = ApiClient();

  /// Page d’alertes (défaut 20 — éviter les réponses trop lourdes / coupures réseau).
  Future<List<Map<String, dynamic>>> fetchAlertes({
    bool realtime = true,
    int limit = 20,
    int skip = 0,
  }) async {
    final list = await _api.get<List<dynamic>>(
      '/sos/',
      queryParameters: {
        'realtime': realtime,
        'limit': limit,
        'skip': skip,
      },
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  /// Une page de dossiers référent : une seule requête `GET /sos/` (workflow_steps, is_oriented sur chaque alerte).
  /// Le détail sinistre n’est chargé que sur l’écran dossier, pas N× par liste.
  Future<List<ReferentDossierItem>> loadEnrichedDossiersPage({
    bool realtime = false,
    int skip = 0,
    int limit = 20,
  }) async {
    final alertes = await fetchAlertes(
      realtime: realtime,
      limit: limit,
      skip: skip,
    );
    return alertes
        .map((a) => ReferentDossierItem(Map<String, dynamic>.from(a), null))
        .toList();
  }

  Future<Map<String, dynamic>> fetchAlerte(int alerteId) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/sos/$alerteId',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  Future<Map<String, dynamic>> fetchSinistreByAlerte(int alerteId) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/sos/$alerteId/sinistre',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  /// Validation / refus de la véracité de l'urgence (réservé au rôle médecin référent MH).
  Future<Map<String, dynamic>> verifyUrgence(
    int sinistreId, {
    required bool approve,
    String? notes,
  }) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/sos/sinistres/$sinistreId/verification',
      body: {
        'approve': approve,
        if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  /// Approuver ou refuser le rapport médical du séjour hospitalier.
  Future<Map<String, dynamic>> validateHospitalStayReport(
    int stayId, {
    required bool approve,
    String? notes,
  }) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/hospital-sinistres/hospital-stays/$stayId/validation',
      body: {
        'approve': approve,
        if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  /// Factures visibles pour le référent (central). [stage] : medical | sinistre | compta.
  Future<List<Map<String, dynamic>>> fetchInvoices({
    String? stage,
    int limit = 100,
    int skip = 0,
  }) async {
    final list = await _api.get<List<dynamic>>(
      '/invoices/',
      queryParameters: {
        if (stage != null) 'stage': stage,
        'limit': limit,
        'skip': skip,
      },
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> fetchInvoice(int invoiceId) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/invoices/$invoiceId',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  Future<Map<String, dynamic>> validateInvoiceMedical(
    int invoiceId, {
    required bool approve,
    String? notes,
  }) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/invoices/$invoiceId/validate_medical',
      body: {
        'approve': approve,
        if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  Future<List<Map<String, dynamic>>> fetchNotifications({
    int limit = 80,
    int skip = 0,
    bool? isRead,
  }) async {
    final list = await _api.get<List<dynamic>>(
      '/notifications/',
      queryParameters: {
        'limit': limit,
        'skip': skip,
        if (isRead != null) 'is_read': isRead,
      },
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<void> markNotificationRead(int notificationId) async {
    await _api.patch<Map<String, dynamic>>(
      '/notifications/$notificationId/read',
      body: <String, dynamic>{},
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }
}
