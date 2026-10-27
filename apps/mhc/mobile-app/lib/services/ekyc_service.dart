import 'dart:convert';

import 'package:http/http.dart' as http;

/// Référence à une session eKYC Trusdy, reconstruite depuis le
/// `verification_url` renvoyé par `POST /v1/kyc/sessions`.
///
/// Le jeton de session est dans le fragment `?token=` de l'URL : il sert de
/// Bearer pour les endpoints `/v1/verification/{id}/*` et ne quitte jamais
/// ce téléphone.
class EkycSessionRef {
  final String baseUrl;
  final String sessionId;
  final String token;

  const EkycSessionRef({
    required this.baseUrl,
    required this.sessionId,
    required this.token,
  });

  /// Parse `https://ekyc.tld/verify/<session_id>?token=...`
  /// (ou `?transfer=<code>` pour un transfert QR — non implémenté ici).
  static EkycSessionRef? parse(String verificationUrl) {
    final uri = Uri.tryParse(verificationUrl.trim());
    if (uri == null) return null;
    final segments = uri.pathSegments;
    if (segments.length < 2 || segments.first != 'verify') return null;
    final token = uri.queryParameters['token'];
    if (token == null || token.isEmpty) return null;
    final base = Uri(
      scheme: uri.scheme,
      host: uri.host,
      port: uri.hasPort ? uri.port : null,
    ).toString();
    return EkycSessionRef(
      baseUrl: base,
      sessionId: segments[1],
      token: token,
    );
  }

  Uri _endpoint(String path) =>
      Uri.parse('$baseUrl/v1/verification/$sessionId$path');
}

class EkycApiException implements Exception {
  final int statusCode;
  final String detail;
  const EkycApiException(this.statusCode, this.detail);
  @override
  String toString() => 'eKYC $statusCode: $detail';
}

/// Minimal client for the end-user eKYC session API — only what the NFC
/// journey needs. Passive authentication is recomputed server-side; the app
/// only ships raw chip data.
class EkycService {
  final http.Client _client;
  EkycService({http.Client? client}) : _client = client ?? http.Client();

  Map<String, String> _headers(EkycSessionRef session) => {
        'Authorization': 'Bearer ${session.token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };

  Future<Map<String, dynamic>> context(EkycSessionRef session) async {
    final response = await _client.get(
      session._endpoint('/context'),
      headers: _headers(session),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> status(EkycSessionRef session) async {
    final response = await _client.get(
      session._endpoint('/status'),
      headers: _headers(session),
    );
    return _decode(response);
  }

  /// Submits raw eMRTD chip data for server-side passive authentication.
  /// Returns `{status, checks, nfc_status: VALID|INVALID|INDETERMINATE,
  /// reason}`.
  Future<NfcSubmissionResult> submitNfc(
    EkycSessionRef session, {
    required List<int> efCom,
    required List<int> efSod,
    List<int>? dg1,
    List<int>? dg2,
  }) async {
    String b64(List<int> bytes) => base64.encode(bytes);
    final response = await _client.post(
      session._endpoint('/nfc'),
      headers: _headers(session),
      body: jsonEncode({
        'ef_com': b64(efCom),
        'ef_sod': b64(efSod),
        if (dg1 != null) 'dg1': b64(dg1),
        if (dg2 != null) 'dg2': b64(dg2),
      }),
    );
    final body = _decode(response);
    return NfcSubmissionResult(
      nfcStatus: body['nfc_status'] as String? ?? 'INDETERMINATE',
      reason: body['reason'] as String? ?? '',
      sessionStatus: body['status'] as String? ?? '',
      checks: (body['checks'] as Map?)?.cast<String, dynamic>() ?? const {},
    );
  }

  Map<String, dynamic> _decode(http.Response response) {
    final body = response.body.isNotEmpty ? jsonDecode(response.body) : {};
    if (response.statusCode >= 400) {
      throw EkycApiException(
        response.statusCode,
        body is Map ? (body['detail']?.toString() ?? 'erreur') : 'erreur',
      );
    }
    return body is Map ? Map<String, dynamic>.from(body) : {};
  }

  void close() => _client.close();
}

class NfcSubmissionResult {
  /// VALID | INVALID | INDETERMINATE — le verdict cryptographique du serveur.
  final String nfcStatus;
  final String reason;
  final String sessionStatus;
  final Map<String, dynamic> checks;

  const NfcSubmissionResult({
    required this.nfcStatus,
    required this.reason,
    required this.sessionStatus,
    required this.checks,
  });
}
