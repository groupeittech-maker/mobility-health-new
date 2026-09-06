import 'package:dio/dio.dart';

import '../config/env_config.dart';
import '../core/config/api_hosts.dart';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;

  late final Dio _dio;

  ApiClient._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: canonicalizeApiBaseUrl(EnvConfig.apiBaseUrl),
      connectTimeout: Duration(milliseconds: EnvConfig.apiTimeout),
      receiveTimeout: Duration(milliseconds: EnvConfig.apiTimeout),
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
    ));
  }

  Dio get dio => _dio;

  void setAuthToken(String token) {
    _dio.options.headers['Authorization'] = 'Bearer $token';
  }

  void clearAuthToken() {
    _dio.options.headers.remove('Authorization');
  }
}
