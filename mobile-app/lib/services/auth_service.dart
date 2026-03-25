import 'package:dio/dio.dart';

import '../core/network/api_client.dart';
import '../core/storage/token_storage.dart';
import '../models/user.dart';

/// Authentification et compte (singleton — utilisé par [AuthProvider] et écrans associés).
class AuthService {
  AuthService._();
  static final AuthService instance = AuthService._();

  final ApiClient _api = ApiClient();
  final TokenStorage _storage = TokenStorage();

  /// Jeton présent (sans appel réseau). La validité est vérifiée par [validateAuth] / [AuthProvider.checkAuth].
  Future<bool> get isLoggedIn async {
    final t = await _storage.getAccessToken();
    return t != null && t.isNotEmpty;
  }

  /// Prénom / nom ou nom d’utilisateur (cache après login, sinon [getMe] si session active).
  Future<String> getDisplayName() async {
    final cached = await _storage.getUserName();
    if (cached != null && cached.trim().isNotEmpty) return cached.trim();
    final t = await _storage.getAccessToken();
    if (t == null || t.isEmpty) return '';
    try {
      return (await getMe()).displayName;
    } catch (_) {
      return '';
    }
  }

  Future<bool> validateAuth() async {
    final t = await _storage.getAccessToken();
    if (t == null || t.isEmpty) return false;
    try {
      await _api.get<Map<String, dynamic>>(
        '/auth/me',
        fromJson: (d) => d as Map<String, dynamic>,
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<UserModel> getMe() async {
    final data = await _api.get<Map<String, dynamic>>(
      '/auth/me',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return UserModel.fromJson(data);
  }

  /// Connexion OAuth2 (formulaire). Retourne l’utilisateur courant.
  Future<UserModel> login(String username, String password) async {
    try {
      final data = await _api.postForm<Map<String, dynamic>>(
        '/auth/login',
        formData: {
          'username': username.trim(),
          'password': password,
        },
        fromJson: (d) => d as Map<String, dynamic>,
      );
      final access = data['access_token'] as String?;
      final refresh = data['refresh_token'] as String?;
      if (access == null || refresh == null) {
        throw Exception('Réponse de connexion invalide');
      }
      await _storage.setAccessToken(access);
      await _storage.setRefreshToken(refresh);
      final user = await getMe();
      await _storage.saveUserMeta(
        userId: user.id,
        role: user.role,
        name: user.displayName,
      );
      return user;
    } on DioException catch (e) {
      throw Exception(_dioDetail(e) ?? 'Connexion impossible');
    }
  }

  Future<void> logout() async {
    await _storage.clearAll();
  }

  Future<Map<String, dynamic>> getMaskedEmail(String usernameOrEmail) async {
    try {
      return await _api.post<Map<String, dynamic>>(
        '/auth/get-masked-email',
        body: {'username_or_email': usernameOrEmail.trim()},
        fromJson: (d) => d as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      throw Exception(_dioDetail(e) ?? 'Erreur lors de la recherche du compte');
    }
  }

  Future<Map<String, dynamic>> requestPasswordReset(String email) async {
    try {
      return await _api.post<Map<String, dynamic>>(
        '/auth/forgot-password',
        body: {'email': email.trim()},
        fromJson: (d) => d as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      throw Exception(_dioDetail(e) ?? 'Impossible d’envoyer le code');
    }
  }

  Future<String> verifyResetCode({
    required String email,
    required String code,
  }) async {
    try {
      final data = await _api.post<Map<String, dynamic>>(
        '/auth/verify-reset-code',
        body: {'email': email.trim(), 'code': code.trim()},
        fromJson: (d) => d as Map<String, dynamic>,
      );
      final token = data['token'] as String?;
      if (token == null || token.isEmpty) {
        throw Exception('Réponse serveur invalide');
      }
      return token;
    } on DioException catch (e) {
      throw Exception(_dioDetail(e) ?? 'Code invalide');
    }
  }

  Future<void> resetPassword({
    required String email,
    required String token,
    required String newPassword,
  }) async {
    try {
      await _api.post<Map<String, dynamic>>(
        '/auth/reset-password',
        body: {
          'email': email.trim(),
          'token': token,
          'new_password': newPassword,
        },
        fromJson: (d) => d as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      throw Exception(_dioDetail(e) ?? 'Impossible de réinitialiser le mot de passe');
    }
  }

  static String? _dioDetail(DioException e) {
    final d = e.response?.data;
    if (d is Map && d['detail'] != null) {
      final detail = d['detail'];
      if (detail is String) return detail;
      if (detail is List && detail.isNotEmpty) return detail.first.toString();
    }
    return e.message;
  }
}
