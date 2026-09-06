import 'package:flutter_dotenv/flutter_dotenv.dart';

import '../core/config/api_hosts.dart';

class EnvConfig {
  static String get apiBaseUrl {
    final raw = dotenv.env['API_BASE_URL'] ??
        dotenv.env['API_CONNEXION_BACKEND'] ??
        kProductionApiBaseUrl;
    final url = canonicalizeApiBaseUrl(raw);
    return url.endsWith('/api/v1') ? url : '$url/api/v1';
  }

  static int get apiTimeout =>
      int.tryParse(dotenv.env['API_TIMEOUT'] ?? '30000') ?? 30000;
}
