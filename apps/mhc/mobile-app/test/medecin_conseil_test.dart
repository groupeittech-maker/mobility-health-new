import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mobility_health_mobile/models/medecin_conseil.dart';
import 'package:mobility_health_mobile/services/medecin_conseil_offline_store.dart';
import 'package:mobility_health_mobile/widgets/medecin_conseil_card.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('parse les coordonnées du médecin-conseil depuis l’API', () {
    final assignment = MedecinConseilAssignment.fromJson({
      'souscription_id': 12,
      'numero_souscription': 'SUB-FR-12',
      'destination': 'Paris, France',
      'destination_country_id': 3,
      'destination_country_name': 'France',
      'medecin_conseil': {
        'id': 7,
        'nom': 'Dr Dupont',
        'telephone': '+33123456789',
        'email': 'dupont@example.com',
      },
    });

    expect(assignment.souscriptionId, 12);
    expect(assignment.destinationLabel, 'Paris, France');
    expect(assignment.hasContact, isTrue);
    expect(assignment.medecinConseil?.nom, 'Dr Dupont');
    expect(assignment.medecinConseil?.telephone, '+33123456789');
  });

  test('le cache local conserve les coordonnées hors ligne', () async {
    final store = MedecinConseilOfflineStore();
    final assignment = MedecinConseilAssignment.fromJson({
      'souscription_id': 4,
      'destination': 'Lisbonne, Portugal',
      'destination_country_name': 'Portugal',
      'medecin_conseil': {
        'id': 9,
        'nom': 'Dr Silva',
        'telephone': '+351210000000',
        'email': 'silva@example.com',
      },
    });

    await store.save([assignment]);
    final cached = await store.load();

    expect(cached, hasLength(1));
    expect(cached.first.medecinConseil?.nom, 'Dr Silva');
    expect(cached.first.medecinConseil?.telephone, '+351210000000');
    expect(cached.first.destination, 'Lisbonne, Portugal');
  });

  testWidgets('affiche le médecin-conseil et permet l’appel', (tester) async {
    String? called;
    final assignment = MedecinConseilAssignment.fromJson({
      'souscription_id': 1,
      'destination': 'Rome, Italie',
      'medecin_conseil': {
        'id': 2,
        'nom': 'Dr Rossi',
        'telephone': '+390612345678',
        'email': 'rossi@example.com',
      },
    });

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MedecinConseilCard(
            assignments: [assignment],
            fromCache: true,
            onCall: (phone) async => called = phone,
            onEmail: (_) async {},
          ),
        ),
      ),
    );

    expect(find.text('Dr Rossi'), findsOneWidget);
    expect(find.text('Rome, Italie'), findsOneWidget);
    expect(find.text('+390612345678'), findsOneWidget);
    expect(find.textContaining('hors ligne'), findsOneWidget);

    await tester.tap(find.text('+390612345678'));
    await tester.pump();
    expect(called, '+390612345678');
  });
}
