import 'package:dio/dio.dart';
import 'package:logger/logger.dart';

import '../config/api_config.dart';
import '../storage/token_storage.dart';

/// Client HTTP pour l'API Mobility Health (équivalent api.js + refresh token).
class ApiClient {
  ApiClient._() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: Duration(milliseconds: ApiConfig.timeoutMs),
      receiveTimeout: Duration(milliseconds: ApiConfig.timeoutMs),
      headers: {'Accept': 'application/json', 'Content-Type': 'application/json'},
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: _onRequest,
      onError: _onError,
    ));
  }

  static final ApiClient _instance = ApiClient._();
  factory ApiClient() => _instance;

  late final Dio _dio;
  final TokenStorage _storage = TokenStorage();
  final Logger _log = Logger();
  bool _refreshing = false;

  Dio get dio => _dio;

  Future<void> _onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _storage.getAccessToken();
    if (token != null && token.isNotEmpty && options.headers['Authorization'] == null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  Future<void> _onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode != 401) {
      handler.next(err);
      return;
    }
    final detail = err.response?.data is Map
        ? (err.response!.data['detail'] ?? '').toString()
        : '';
    final isAuthError = detail.toLowerCase().contains('could not validate credentials') ||
        detail.toLowerCase().contains('invalid') ||
        detail.toLowerCase().contains('expired') ||
        detail.toLowerCase().contains('not authenticated');
    if (!isAuthError) {
      handler.next(err);
      return;
    }
    try {
      final newToken = await _refreshAccessToken();
      if (newToken != null) {
        final opts = err.requestOptions;
        opts.headers['Authorization'] = 'Bearer $newToken';
        final response = await _dio.fetch(opts);
        return handler.resolve(response);
      }
    } catch (_) {}
    handler.next(err);
  }

  Future<String?> _refreshAccessToken() async {
    if (_refreshing) {
      await Future.delayed(const Duration(milliseconds: 500));
      return _storage.getAccessToken();
    }
    _refreshing = true;
    try {
      final refreshToken = await _storage.getRefreshToken();
      if (refreshToken == null || refreshToken.isEmpty) return null;
      final response = await _dio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final access = response.data?['access_token'] as String?;
      final refresh = response.data?['refresh_token'] as String?;
      if (access != null) await _storage.setAccessToken(access);
      if (refresh != null) await _storage.setRefreshToken(refresh);
      return access;
    } catch (e) {
      _log.w('Refresh token failed: $e');
      await _storage.clearAll();
      return null;
    } finally {
      _refreshing = false;
    }
  }

  /// GET
  Future<T> get<T>(String path, {Map<String, dynamic>? queryParameters, T Function(dynamic)? fromJson}) async {
    final response = await _dio.get<dynamic>(path, queryParameters: queryParameters);
    return _decode<T>(response.data, fromJson);
  }

  /// POST (body JSON)
  Future<T> post<T>(String path, {dynamic body, T Function(dynamic)? fromJson}) async {
    final response = await _dio.post<dynamic>(path, data: body);
    return _decode<T>(response.data, fromJson);
  }

  /// POST form-urlencoded (pour login OAuth2)
  Future<T> postForm<T>(String path, {required Map<String, dynamic> formData, T Function(dynamic)? fromJson}) async {
    final response = await _dio.post<dynamic>(
      path,
      data: formData,
      options: Options(contentType: Headers.formUrlEncodedContentType),
    );
    return _decode<T>(response.data, fromJson);
  }

  /// PUT
  Future<T> put<T>(String path, {dynamic body, T Function(dynamic)? fromJson}) async {
    final response = await _dio.put<dynamic>(path, data: body);
    return _decode<T>(response.data, fromJson);
  }

  /// PATCH
  Future<T> patch<T>(String path, {dynamic body, T Function(dynamic)? fromJson}) async {
    final response = await _dio.patch<dynamic>(path, data: body);
    return _decode<T>(response.data, fromJson);
  }

  /// DELETE
  Future<void> delete(String path) async {
    await _dio.delete(path);
  }

  /// POST multipart (upload fichier)
  Future<T> postMultipart<T>(
    String path, {
    required Map<String, dynamic> fields,
    required String fileKey,
    required String filePath,
    T Function(dynamic)? fromJson,
  }) async {
    final name = filePath.split(RegExp(r'[/\\]')).last;
    final formData = FormData.fromMap({
      ...fields,
      fileKey: await MultipartFile.fromFile(filePath, filename: name),
    });
    final response = await _dio.post<dynamic>(
      path,
      data: formData,
      options: Options(
        contentType: Headers.multipartFormDataContentType,
        sendTimeout: const Duration(seconds: 60),
        receiveTimeout: const Duration(seconds: 60),
      ),
    );
    return _decode<T>(response.data, fromJson);
  }

  static T _decode<T>(dynamic data, T Function(dynamic)? fromJson) {
    if (data == null) throw Exception('Empty response');
    if (fromJson != null) return fromJson(data);
    return data as T;
  }
}
