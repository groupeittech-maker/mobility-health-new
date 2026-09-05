import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../core/network/api_client.dart';

/// Pièces jointes sinistre (certificat de décès hospitalier).
class SinistreAttachmentService {
  SinistreAttachmentService._();
  static final SinistreAttachmentService instance = SinistreAttachmentService._();

  final ApiClient _api = ApiClient();

  Future<Map<String, dynamic>> uploadCertificatDeces(int sinistreId, String filePath) async {
    final data = await _api.postMultipart<Map<String, dynamic>>(
      '/hospital-sinistres/sinistres/$sinistreId/attachments/certificat-deces',
      fields: const {},
      fileKey: 'file',
      filePath: filePath,
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  Future<String> downloadCertificatDeces(int sinistreId, {String? fileName}) async {
    final response = await _api.dio.get<List<int>>(
      '/hospital-sinistres/sinistres/$sinistreId/attachments/certificat-deces',
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) throw Exception('Fichier vide reçu');
    final dir = await getTemporaryDirectory();
    final safeName = (fileName ?? 'certificat-deces.pdf').replaceAll(RegExp(r'[^\w.\-]'), '_');
    final file = File('${dir.path}/$safeName');
    await file.writeAsBytes(bytes);
    return file.path;
  }
}
