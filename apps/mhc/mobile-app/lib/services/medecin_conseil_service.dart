import '../core/network/api_client.dart';
import '../models/medecin_conseil.dart';
import 'medecin_conseil_offline_store.dart';

/// Charge les coordonnées du médecin-conseil et les conserve hors ligne.
class MedecinConseilService {
  MedecinConseilService({
    ApiClient? api,
    MedecinConseilOfflineStore? store,
  })  : _api = api ?? ApiClient(),
        _store = store ?? MedecinConseilOfflineStore();

  final ApiClient _api;
  final MedecinConseilOfflineStore _store;

  Future<List<MedecinConseilAssignment>> loadCached() => _store.load();

  Future<List<MedecinConseilAssignment>> refresh({int? souscriptionId}) async {
    final list = await _api.get<List<dynamic>>(
      '/sos/medecin-conseil',
      queryParameters: {
        if (souscriptionId != null) 'souscription_id': souscriptionId,
      },
      fromJson: (data) => data as List<dynamic>,
    );
    final parsed = list
        .whereType<Map>()
        .map((item) => MedecinConseilAssignment.fromJson(Map<String, dynamic>.from(item)))
        .toList();
    if (souscriptionId == null) {
      await _store.save(parsed);
    } else {
      final existing = await _store.load();
      final merged = [
        ...existing.where((item) => item.souscriptionId != souscriptionId),
        ...parsed,
      ];
      await _store.save(merged);
    }
    return parsed;
  }

  Future<void> clearCache() => _store.clear();
}
