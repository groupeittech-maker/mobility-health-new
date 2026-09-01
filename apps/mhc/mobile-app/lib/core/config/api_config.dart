/// Configuration de l'API - chargée depuis .env (flutter_dotenv).
/// S'inspire de frontend-simple/js/api.js
import 'package:flutter_dotenv/flutter_dotenv.dart';

class ApiConfig {
  static String _env(String key, [String fallback = '']) {
    return dotenv.env[key]?.trim() ?? fallback;
  }

  /// URL de base de l'API (ex: https://api.srv1324425.hstgr.cloud/api/v1 ou http://10.0.2.2:8000/api/v1 pour émulateur Android)
  static String get baseUrl {
    final url = _env('API_BASE_URL').isNotEmpty
        ? _env('API_BASE_URL')
        : _env('API_CONNEXION_BACKEND').isNotEmpty
            ? _env('API_CONNEXION_BACKEND')
            : 'https://api.srv1324425.hstgr.cloud/api/v1';
    return url.endsWith('/api/v1') ? url : '$url/api/v1';
  }

  static int get timeoutMs => int.tryParse(_env('API_TIMEOUT', '30000')) ?? 30000;
  static String get environment => _env('ENVIRONMENT', 'production');
  static String get appName => _env('APP_NAME', 'Mobility Health');
  static String get appVersion => _env('APP_VERSION', '1.0.0');

  static bool get isProduction => environment.toLowerCase() == 'production';
}
