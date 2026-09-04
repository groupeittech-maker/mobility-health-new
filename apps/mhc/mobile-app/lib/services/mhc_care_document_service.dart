import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';

import '../core/network/api_client.dart';

/// API bons / attestations MHC pour le médecin référent (aligné web).
class MhcCareDocumentService {
  MhcCareDocumentService._();
  static final MhcCareDocumentService instance = MhcCareDocumentService._();

  final ApiClient _api = ApiClient();

  Future<Map<String, dynamic>> fetchCareDocuments(int sinistreId) async {
    final data = await _api.get<Map<String, dynamic>>(
      '/mhc/sinistres/$sinistreId/care-documents',
      fromJson: (d) => d as Map<String, dynamic>,
    );
    return Map<String, dynamic>.from(data);
  }

  Future<List<Map<String, dynamic>>> issueCareDocument(
    int sinistreId, {
    required String documentType,
    Map<String, dynamic>? payload,
    String? notes,
  }) async {
    final list = await _api.post<List<dynamic>>(
      '/mhc/sinistres/$sinistreId/care-documents',
      body: {
        'document_type': documentType,
        if (payload != null && payload.isNotEmpty) 'payload': payload,
        if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
      },
      fromJson: (d) => d as List<dynamic>,
    );
    return list.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<String> downloadCareDocumentPdf(int documentId, {String? numero}) async {
    final response = await _api.dio.get<List<int>>(
      '/mhc/care-documents/$documentId/pdf',
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) throw Exception('PDF vide reçu');
    final dir = await getTemporaryDirectory();
    final name = 'mhc-${numero ?? documentId}.pdf'.replaceAll(RegExp(r'[^\w\-.]'), '_');
    final file = File('${dir.path}/$name');
    await file.writeAsBytes(bytes);
    return file.path;
  }
}
