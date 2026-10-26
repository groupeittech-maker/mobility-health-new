import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../core/network/api_client.dart';

/// Actions sur une police (workflow MyMHC V3) : annulation, modification,
/// prorogation, paiement du complément, avenants et quittances de ristourne.
class AvenantService {
  AvenantService._();
  static final AvenantService instance = AvenantService._();

  final ApiClient _api = ApiClient();

  /// Actions disponibles (règle exclusive), demande en cours, avenants, ristournes.
  Future<Map<String, dynamic>> fetchActions(int subscriptionId) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/subscriptions/$subscriptionId/actions',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  /// `confirm = false` : simulation (montants) sans modifier la police.
  Future<Map<String, dynamic>> submitAction(
    int subscriptionId,
    String action, {
    required bool confirm,
    DateTime? nouvelleDateDebut,
    DateTime? nouvelleDateFin,
    String? motif,
  }) async {
    String day(DateTime d) =>
        '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
    final data = await _api.post<Map<String, dynamic>>(
      '/subscriptions/$subscriptionId/actions/$action',
      body: {
        'confirmer': confirm,
        if (nouvelleDateDebut != null) 'nouvelle_date_debut': day(nouvelleDateDebut),
        if (nouvelleDateFin != null) 'nouvelle_date_fin': day(nouvelleDateFin),
        if (motif != null && motif.trim().isNotEmpty) 'motif': motif.trim(),
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  /// Paiement du complément de prime d'une modification / prorogation.
  Future<Map<String, dynamic>> payAvenant(int avenantId, {required String paymentType}) async {
    final data = await _api.post<Map<String, dynamic>>(
      '/avenants/$avenantId/payer',
      body: {'payment_type': paymentType, 'flow': 'checkout'},
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  /// Renoncer à une demande en attente de paiement.
  Future<void> abandonAvenant(int avenantId) async {
    await _api.post<dynamic>('/avenants/$avenantId/abandon', fromJson: (d) => d);
  }

  Future<String> downloadAvenantPdf(int avenantId, {String? numero}) =>
      _downloadPdf('/avenants/$avenantId/download', 'avenant-${numero ?? avenantId}.pdf');

  Future<String> downloadRistournePdf(int ristourneId, {String? numero}) =>
      _downloadPdf('/ristournes/$ristourneId/download', 'quittance-ristourne-${numero ?? ristourneId}.pdf');

  Future<String> _downloadPdf(String path, String fileName) async {
    final response = await _api.dio.get<List<int>>(
      path,
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) throw Exception('PDF vide reçu');
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/${fileName.replaceAll(RegExp(r'[^\w\-.]'), '_')}');
    await file.writeAsBytes(bytes);
    return file.path;
  }
}
