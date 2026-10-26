import 'package:dio/dio.dart';

/// Convertit une exception API en message utilisateur en français.
String apiErrorToUserMessage(Object e) {
  if (e is DioException) {
    final statusCode = e.response?.statusCode;
    final detailMessage = _extractDetailMessage(e);
    switch (statusCode) {
      case 500:
        return detailMessage ??
            'Erreur serveur. Veuillez vous reconnecter plus tard.';
      case 502:
      case 503:
        return detailMessage ??
            'Serveur temporairement indisponible. Réessayez dans quelques instants.';
      case 404:
        return 'Ressource non trouvée.';
      case 401:
        return 'Session expirée. Veuillez vous reconnecter.';
      case 403:
        return 'Accès non autorisé.';
      case 422:
        return detailMessage ?? 'Données invalides.';
    }
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'Délai dépassé. Vérifiez votre connexion.';
      case DioExceptionType.connectionError:
        return 'Connexion impossible. Vérifiez votre connexion internet.';
      case DioExceptionType.badCertificate:
        return _certificateMessage;
      default:
        break;
    }
    if (isTlsCertificateFailure(e)) {
      return _certificateMessage;
    }
    final detail = detailMessage ?? _extractDetailMessage(e);
    if (detail != null) return detail;
  }
  final str = e.toString().replaceFirst('Exception: ', '').replaceFirst('DioException: ', '');
  if (_looksLikeCertificateFailure(str)) return _certificateMessage;
  if (str.contains('500')) return 'Erreur serveur. Veuillez vous reconnecter plus tard.';
  if (str.contains('connection') || str.contains('Connection')) return 'Connexion impossible. Vérifiez votre connexion internet.';
  return str.length > 120 ? 'Une erreur est survenue. Veuillez réessayer.' : str;
}

String? _extractDetailMessage(DioException e) {
  final detail = e.response?.data;
  if (detail is Map && detail['detail'] != null) {
    final d = detail['detail'];
    if (d is String && d.trim().isNotEmpty) return d;
    if (d is List && d.isNotEmpty) {
      final msg = pydanticDetailToMessage(d);
      if (msg != null) return msg;
      if (d.first is String) return d.first as String;
    }
  }
  return null;
}

/// Convertit une liste d'erreurs FastAPI/Pydantic
/// (`[{type, loc, msg, ...}]`) en message lisible en français.
String? pydanticDetailToMessage(List detail) {
  final msgs = detail
      .whereType<Map>()
      .map(_pydanticMsg)
      .where((m) => m.isNotEmpty)
      .toSet()
      .toList();
  return msgs.isEmpty ? null : msgs.join(' ; ');
}

const _fieldLabels = {
  'username': 'Adresse e-mail',
  'email': 'Adresse e-mail',
  'password': 'Mot de passe',
  'telephone': 'Téléphone',
  'date_naissance': 'Date de naissance',
};

String _pydanticMsg(Map m) {
  final loc = m['loc'];
  final field = (loc is List && loc.isNotEmpty) ? loc.last.toString() : null;
  final label = _fieldLabels[field] ?? field;
  final msg = m['msg']?.toString() ?? '';
  if (msg.contains('Field required') || m['type'] == 'missing') {
    return label != null ? '$label : champ requis' : 'Champ requis';
  }
  if (msg.contains('valid email')) return 'Adresse e-mail invalide';
  // Les validateurs métier renvoient déjà des messages en français
  // (« Le mot de passe doit contenir… ») : on les affiche tels quels.
  if (msg.startsWith('Value error, ')) {
    final inner = msg.substring('Value error, '.length);
    return inner.isNotEmpty ? inner : '';
  }
  if (msg.isEmpty) return '';
  return label != null ? '$label : $msg' : msg;
}

const _certificateMessage =
    'Connexion sécurisée impossible (certificat serveur expiré ou invalide). Réessayez dans un instant.';

bool isTlsCertificateFailure(Object e) {
  if (e is DioException) {
    if (e.type == DioExceptionType.badCertificate) return true;
    return _looksLikeCertificateFailure('${e.error ?? ''} ${e.message ?? ''} $e');
  }
  return _looksLikeCertificateFailure(e.toString());
}

bool _looksLikeCertificateFailure(String text) {
  final lower = text.toLowerCase();
  return lower.contains('certificate') ||
      lower.contains('handshakeexception') ||
      lower.contains('certificat');
}
