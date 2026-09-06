import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobility_health_mobile/core/config/api_config.dart';
import 'package:mobility_health_mobile/core/config/api_hosts.dart';
import 'package:mobility_health_mobile/core/utils/api_error_helper.dart';

void main() {
  test('canonicalizeApiBaseUrl remplace le sous-domaine au certificat expiré', () {
    expect(
      canonicalizeApiBaseUrl('https://api.srv1324425.hstgr.cloud/api/v1'),
      'https://srv1324425.hstgr.cloud/api/v1',
    );
    expect(
      canonicalizeApiBaseUrl('https://srv1324425.hstgr.cloud/api/v1'),
      'https://srv1324425.hstgr.cloud/api/v1',
    );
  });

  test('ApiConfig réécrit un .env encore pointé vers api.', () {
    dotenv.testLoad(
      fileInput: 'API_BASE_URL=https://api.srv1324425.hstgr.cloud/api/v1\n',
    );
    expect(ApiConfig.baseUrl, 'https://srv1324425.hstgr.cloud/api/v1');
  });

  test('apiErrorToUserMessage masque HandshakeException certificat expiré', () {
    final error = DioException(
      requestOptions: RequestOptions(path: '/auth/register'),
      type: DioExceptionType.unknown,
      error: const HandshakeException(
        'CERTIFICATE_VERIFY_FAILED: certificate has expired',
      ),
    );
    final message = apiErrorToUserMessage(error);
    expect(message.toLowerCase(), contains('certificat'));
    expect(message.contains('HandshakeException'), isFalse);
    expect(message.contains('DioException'), isFalse);
  });
}
