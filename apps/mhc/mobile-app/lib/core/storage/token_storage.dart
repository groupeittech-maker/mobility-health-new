import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Stockage sécurisé des tokens (équivalent localStorage + sanitize du frontend).
class TokenStorage {
  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const _userIdKey = 'user_id';
  static const _userRoleKey = 'user_role';
  static const _userNameKey = 'user_name';

  /// [resetOnError] : efface le stockage si le Keystore Android ne peut plus déchiffrer
  /// (réinstall, changement de signature debug, restauration backup incompatible).
  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
      resetOnError: true,
    ),
  );

  bool _storageResetDone = false;

  Future<String?> getAccessToken() async {
    final raw = await _safeRead(_accessKey);
    return _sanitizeToken(raw);
  }

  Future<void> setAccessToken(String? token) async {
    if (token == null || token.isEmpty) {
      await _safeDelete(_accessKey);
      return;
    }
    final sanitized = _sanitizeToken(token);
    if (sanitized == null) {
      await _safeDelete(_accessKey);
      return;
    }
    await _safeWrite(_accessKey, sanitized);
  }

  Future<String?> getRefreshToken() async {
    return _sanitizeToken(await _safeRead(_refreshKey));
  }

  Future<void> setRefreshToken(String? token) async {
    if (token == null || token.isEmpty) {
      await _safeDelete(_refreshKey);
      return;
    }
    final sanitized = _sanitizeToken(token);
    if (sanitized == null) {
      await _safeDelete(_refreshKey);
      return;
    }
    await _safeWrite(_refreshKey, sanitized);
  }

  Future<void> saveUserMeta({required int userId, required String role, required String name}) async {
    await _safeWrite(_userIdKey, userId.toString());
    await _safeWrite(_userRoleKey, role);
    await _safeWrite(_userNameKey, name);
  }

  Future<int?> getUserId() async {
    final s = await _safeRead(_userIdKey);
    return int.tryParse(s ?? '');
  }

  Future<String?> getUserRole() async => _safeRead(_userRoleKey);
  Future<String?> getUserName() async => _safeRead(_userNameKey);

  Future<void> clearAll() async {
    await _safeDeleteAll();
  }

  Future<String?> _safeRead(String key) async {
    try {
      return await _storage.read(key: key);
    } on PlatformException catch (e, st) {
      if (_isKeystoreCorruption(e)) {
        await _recoverFromKeystoreFailure(e, st);
        return null;
      }
      rethrow;
    }
  }

  Future<void> _safeWrite(String key, String value) async {
    try {
      await _storage.write(key: key, value: value);
    } on PlatformException catch (e, st) {
      if (_isKeystoreCorruption(e)) {
        await _recoverFromKeystoreFailure(e, st);
        await _storage.write(key: key, value: value);
        return;
      }
      rethrow;
    }
  }

  Future<void> _safeDelete(String key) async {
    try {
      await _storage.delete(key: key);
    } on PlatformException catch (e, st) {
      if (_isKeystoreCorruption(e)) {
        await _recoverFromKeystoreFailure(e, st);
        return;
      }
      rethrow;
    }
  }

  Future<void> _safeDeleteAll() async {
    try {
      await _storage.deleteAll();
    } on PlatformException catch (e, st) {
      if (_isKeystoreCorruption(e)) {
        await _recoverFromKeystoreFailure(e, st);
        return;
      }
      rethrow;
    }
  }

  bool _isKeystoreCorruption(PlatformException e) {
    final message = '${e.message ?? ''} ${e.details ?? ''}'.toLowerCase();
    return message.contains('verification failed') ||
        message.contains('verif') ||
        message.contains('keystore') ||
        message.contains('decrypt') ||
        message.contains('mac') ||
        message.contains('signature');
  }

  Future<void> _recoverFromKeystoreFailure(PlatformException e, StackTrace st) async {
    if (_storageResetDone) return;
    _storageResetDone = true;
    debugPrint(
      'TokenStorage: stockage sécurisé illisible (Keystore Android). '
      'Réinitialisation — reconnexion requise. ${e.message}',
    );
    try {
      await _storage.deleteAll();
    } catch (_) {
      // resetOnError ou données déjà effacées
    }
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
