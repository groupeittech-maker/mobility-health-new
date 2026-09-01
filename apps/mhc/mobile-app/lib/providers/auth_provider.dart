import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/user.dart';
import '../services/api_services.dart';
import '../services/auth_service.dart';
import '../services/referent_push_service.dart';

class AuthProvider extends ChangeNotifier {
  final AuthService _auth = AuthService.instance;

  UserModel? _currentUser;
  bool _loading = false;
  bool _checked = false;

  UserModel? get currentUser => _currentUser;
  bool get loading => _loading;
  bool get isAuthenticated => _currentUser != null;
  bool get checked => _checked;

  /// Délai max pour ne pas bloquer l'app si l'API ne répond pas (réseau coupé, serveur down).
  static const Duration _authCheckTimeout = Duration(seconds: 8);

  Future<void> checkAuth() async {
    if (_checked) return;
    _loading = true;
    notifyListeners();
    try {
      final valid = await _auth.validateAuth().timeout(
        _authCheckTimeout,
        onTimeout: () => false,
      );
      if (valid) {
        _currentUser = await _auth.getMe().timeout(
          _authCheckTimeout,
          onTimeout: () => throw TimeoutException('getMe'),
        );
        await ReferentPushService.instance.syncBackendTokenIfSessionOpen();
        DestinationsService.warmDestinationCountriesCache();
        SubscriptionsService.warmSubscriptionsCache();
        AttestationsService.warmUserAttestationsCache();
        SosService.warmSosAlertesCache();
        HospitalStaysService.warmHospitalStaysCache();
      } else {
        _currentUser = null;
      }
    } on TimeoutException {
      _currentUser = null;
    } catch (_) {
      _currentUser = null;
    }
    _loading = false;
    _checked = true;
    notifyListeners();
  }

  Future<UserModel> login(String username, String password) async {
    _loading = true;
    notifyListeners();
    try {
      _currentUser = await _auth.login(username, password);
      DestinationsService.warmDestinationCountriesCache();
      SubscriptionsService.warmSubscriptionsCache();
      AttestationsService.warmUserAttestationsCache();
      SosService.warmSosAlertesCache();
      HospitalStaysService.warmHospitalStaysCache();
      return _currentUser!;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await _auth.logout();
    _currentUser = null;
    _checked = true;
    notifyListeners();
  }

  Future<void> refreshUser() async {
    if (!isAuthenticated) return;
    try {
      _currentUser = await _auth.getMe();
      notifyListeners();
    } catch (_) {}
  }
}
