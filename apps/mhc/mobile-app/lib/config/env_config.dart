import 'package:flutter_dotenv/flutter_dotenv.dart';

class EnvConfig {
  static String get apiBaseUrl {
    final url = dotenv.env['API_BASE_URL'] ??
        dotenv.env['API_CONNEXION_BACKEND'] ??
        'https://api.srv1324425.hstgr.cloud/api/v1';
    return url.endsWith('/api/v1') ? url : '$url/api/v1';
  }

  static int get apiTimeout =>
      int.tryParse(dotenv.env['API_TIMEOUT'] ?? '30000') ?? 30000;
}
