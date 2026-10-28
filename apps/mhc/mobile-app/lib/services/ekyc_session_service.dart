import 'package:dio/dio.dart';

import '../core/network/api_client.dart';

/// Session eKYC côté MHC : création (par le backend, tenant Trusdy) et
/// polling du résultat. L'utilisateur authentifié ne voit jamais les clés
/// tenant — l'app reçoit seulement la `verification_url` jetable.
class EkycSession {
  final String sessionId;
  final String status;
  final String verificationUrl;
  final DateTime? expiresAt;
  final bool isVerified;

  const EkycSession({
    required this.sessionId,
    required this.status,
    required this.verificationUrl,
    this.expiresAt,
    this.isVerified = false,
  });
}

class EkycSessionStatus {
  final String sessionId;
  final String status;
  final Map<String, dynamic> checks;
  final List<dynamic> reasons;
  final bool isTerminal;
  final bool isVerified;

  const EkycSessionStatus({
    required this.sessionId,
    required this.status,
    required this.checks,
    required this.reasons,
    required this.isTerminal,
    required this.isVerified,
  });
}

class EkycSessionService {
  EkycSessionService._();
  static final EkycSessionService instance = EkycSessionService._();

  final ApiClient _api = ApiClient();

  /// Démarre une vérification d'identité côté backend MHC.
  Future<EkycSession> createSession({int? souscriptionId}) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/ekyc/sessions',
      body: {if (souscriptionId != null) 'souscription_id': souscriptionId},
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return EkycSession(
      sessionId: data['session_id'] as String,
      status: data['status'] as String? ?? 'CREATED',
      verificationUrl: data['verification_url'] as String,
      expiresAt: data['expires_at'] != null
          ? DateTime.tryParse(data['expires_at'].toString())
          : null,
    );
  }

  /// Dernière session liée à une souscription — 404 → null (aucune).
  Future<EkycSession?> getLatestForSouscription(int souscriptionId) async {
    try {
      final data = await _api.get<Map<String, dynamic>>(
        '/ekyc/sessions/by-souscription/$souscriptionId',
        fromJson: (d) => d as Map<String, dynamic>,
      );
      return EkycSession(
        sessionId: data['session_id'] as String,
        status: data['status'] as String? ?? 'CREATED',
        verificationUrl: (data['verification_url'] as String?) ?? '',
        expiresAt: data['expires_at'] != null
            ? DateTime.tryParse(data['expires_at'].toString())
            : null,
        isVerified: data['is_verified'] == true,
      );
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  /// État courant — le backend rapatrie le résultat Trusdy au passage.
  Future<EkycSessionStatus> getStatus(String sessionId) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/ekyc/sessions/$sessionId',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return EkycSessionStatus(
      sessionId: sessionId,
      status: data['status'] as String? ?? '',
      checks: (data['checks'] as Map?)?.cast<String, dynamic>() ?? const {},
      reasons: (data['reasons'] as List?) ?? const [],
      isTerminal: data['is_terminal'] == true,
      isVerified: data['is_verified'] == true,
    );
  }
}
