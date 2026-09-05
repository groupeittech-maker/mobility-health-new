import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/medecin_conseil.dart';

/// Cache persistant des coordonnées médecin-conseil (consultation hors ligne).
class MedecinConseilOfflineStore {
  static const key = 'medecin_conseil_assignments_v1';

  Future<void> save(List<MedecinConseilAssignment> items) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      key,
      jsonEncode(items.map((item) => item.toJson()).toList()),
    );
  }

  Future<List<MedecinConseilAssignment>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(key);
    if (raw == null || raw.isEmpty) return const [];
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return const [];
      return decoded
          .whereType<Map>()
          .map((item) => MedecinConseilAssignment.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    } catch (_) {
      return const [];
    }
  }

  Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(key);
  }
}
