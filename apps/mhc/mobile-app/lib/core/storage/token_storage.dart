import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Stockage sécurisé des tokens (équivalent localStorage + sanitize du frontend).
class TokenStorage {
  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const _userIdKey = 'user_id';
  static const _userRoleKey = 'user_role';
  static const _userNameKey = 'user_name';

  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  Future<String?> getAccessToken() async {
    final raw = await _storage.read(key: _accessKey);
    return _sanitizeToken(raw);
  }

  Future<void> setAccessToken(String? token) async {
    if (token == null || token.isEmpty) {
      await _storage.delete(key: _accessKey);
      return;
    }
    await _storage.write(key: _accessKey, value: _sanitizeToken(token));
  }

  Future<String?> getRefreshToken() async {
    return _sanitizeToken(await _storage.read(key: _refreshKey));
  }

  Future<void> setRefreshToken(String? token) async {
    if (token == null || token.isEmpty) {
      await _storage.delete(key: _refreshKey);
      return;
    }
    await _storage.write(key: _refreshKey, value: _sanitizeToken(token));
  }

  Future<void> saveUserMeta({required int userId, required String role, required String name}) async {
    await _storage.write(key: _userIdKey, value: userId.toString());
    await _storage.write(key: _userRoleKey, value: role);
    await _storage.write(key: _userNameKey, value: name);
  }

  Future<int?> getUserId() async {
    final s = await _storage.read(key: _userIdKey);
    return int.tryParse(s ?? '');
  }

  Future<String?> getUserRole() async => _storage.read(key: _userRoleKey);
  Future<String?> getUserName() async => _storage.read(key: _userNameKey);

  Future<void> clearAll() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
    await _storage.delete(key: _userIdKey);
    await _storage.delete(key: _userRoleKey);
    await _storage.delete(key: _userNameKey);
  }

  static String? _sanitizeToken(String? raw) {
    if (raw == null || raw.isEmpty) return null;
    String t = raw.trim();
    if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
      t = t.substring(1, t.length - 1).trim();
    }
    if (t.toLowerCase().startsWith('bearer ')) {
      t = t.substring(7).trim();
    }
    if (t.isEmpty || t.toLowerCase() == 'null' || t.toLowerCase() == 'undefined') return null;
    return t;
  }
}
