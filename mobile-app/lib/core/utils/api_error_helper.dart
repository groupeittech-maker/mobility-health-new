import 'package:dio/dio.dart';

/// Convertit une exception API en message utilisateur en français.
String apiErrorToUserMessage(Object e) {
  if (e is DioException) {
    final statusCode = e.response?.statusCode;
    switch (statusCode) {
      case 500:
        return 'Erreur serveur. Veuillez vous reconnecter plus tard.';
      case 502:
      case 503:
        return 'Serveur temporairement indisponible. Réessayez dans quelques instants.';
      case 404:
        return 'Ressource non trouvée.';
      case 401:
        return 'Session expirée. Veuillez vous reconnecter.';
      case 403:
        return 'Accès non autorisé.';
      case 422:
        return 'Données invalides.';
    }
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'Délai dépassé. Vérifiez votre connexion.';
      case DioExceptionType.connectionError:
        return 'Connexion impossible. Vérifiez votre connexion internet.';
      case DioExceptionType.badCertificate:
        return 'Certificat invalide. Vérifiez la configuration.';
      default:
        break;
    }
    final detail = e.response?.data;
    if (detail is Map && detail['detail'] != null) {
      final d = detail['detail'];
      if (d is String) return d;
      if (d is List && d.isNotEmpty && d.first is String) return d.first as String;
    }
  }
  final str = e.toString().replaceFirst('Exception: ', '').replaceFirst('DioException: ', '');
  if (str.contains('500')) return 'Erreur serveur. Veuillez vous reconnecter plus tard.';
  if (str.contains('connection') || str.contains('Connection')) return 'Connexion impossible. Vérifiez votre connexion internet.';
  return str.length > 120 ? 'Une erreur est survenue. Veuillez réessayer.' : str;
}
