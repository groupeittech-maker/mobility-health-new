import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('register_screen.dart aligné sur le web (sans passeport ni médical)', () {
    final source = File('lib/screens/register_screen.dart').readAsStringSync();

    expect(source.contains('numero_passeport'), isFalse);
    expect(source.contains('validite_passeport'), isFalse);
    expect(source.contains('maladies_chroniques'), isFalse);
    expect(source.contains('Informations médicales'), isFalse);
    expect(source.contains('Numéro de passeport'), isFalse);
    expect(source.contains('full_name'), isTrue);
    expect(source.contains('consentCgu'), isTrue);
    expect(source.contains('verify-email'), isTrue);
  });
}
