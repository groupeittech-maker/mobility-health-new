import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Langue de l'application (workflow V3 : fr, en, es, pt, ar — arabe en RTL).
/// Persistée localement ; synchronisée avec le compte via PUT /users/me/settings.
class LocaleProvider extends ChangeNotifier {
  static const _prefKey = 'app_locale';
  static const supported = ['fr', 'en', 'es', 'pt', 'ar'];

  Locale _locale = const Locale('fr');
  Locale get locale => _locale;

  bool get isRtl => _locale.languageCode == 'ar';

  Future<void> load() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final code = prefs.getString(_prefKey);
      if (code != null && supported.contains(code)) {
        _locale = Locale(code);
        notifyListeners();
      }
    } catch (_) {}
  }

  Future<void> setLocale(Locale locale) async {
    if (!supported.contains(locale.languageCode)) return;
    _locale = Locale(locale.languageCode);
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefKey, locale.languageCode);
    } catch (_) {}
  }
}
