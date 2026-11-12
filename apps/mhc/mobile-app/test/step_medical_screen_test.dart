import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:mobility_health_mobile/screens/subscription/step_medical_screen.dart';

Widget _wrap(Widget child) => MaterialApp(
      home: Scaffold(body: child),
    );

void main() {
  group('StepMedicalScreen — questionnaire groupe', () {
    testWidgets('adulte seul : formulation individuelle, pas de sélecteur',
        (tester) async {
      await tester.pumpWidget(_wrap(StepMedicalScreen(
        onContinue: (_) {},
        mineurs: const [],
      )));
      await tester.pumpAndSettle();

      expect(find.textContaining('Êtes-vous malade'), findsOneWidget);
      expect(find.text('Personne(s) concernée(s) *'), findsNothing);
    });

    testWidgets('enfants uniquement : aucun questionnaire adulte',
        (tester) async {
      // Le parent ne voyage pas : pas de « vous », seules les questions de
      // l'enfant (formulation individuelle si un seul enfant).
      await tester.pumpWidget(_wrap(StepMedicalScreen(
        onContinue: (_) {},
        adultIncluded: false,
        mineurs: const ['Fatou NDIAYE'],
      )));
      await tester.pumpAndSettle();

      expect(find.textContaining('Êtes-vous'), findsNothing);
      expect(
          find.textContaining("L'enfant est-il malade"), findsOneWidget);
      expect(find.textContaining('Fatou NDIAYE'), findsWidgets);
    });

    testWidgets('groupe : « Oui » affiche sélecteur de personnes + précision',
        (tester) async {
      await tester.pumpWidget(_wrap(StepMedicalScreen(
        onContinue: (_) {},
        mineurs: const ['Fatou NDIAYE', 'Moussa NDIAYE'],
      )));
      await tester.pumpAndSettle();

      // Formulation groupe.
      expect(
          find.textContaining("L'un des voyageurs est-il malade"),
          findsOneWidget);

      // Répondre « Oui » à la première question.
      await tester.tap(find.text('Oui').first);
      await tester.pumpAndSettle();

      // Liste des personnes + champ « Veuillez préciser ».
      expect(find.text('Personne(s) concernée(s) *'), findsOneWidget);
      expect(find.text('Vous (adulte)'), findsOneWidget);
      expect(find.text('Fatou NDIAYE'), findsOneWidget);
      expect(find.text('Moussa NDIAYE'), findsOneWidget);
      expect(find.text('Veuillez préciser *'), findsOneWidget);
    });

    testWidgets('soumission groupe : réponses associées aux personnes',
        (tester) async {
      Map<String, dynamic>? submitted;
      await tester.pumpWidget(_wrap(StepMedicalScreen(
        onContinue: (data) => submitted = data.reponses,
        mineurs: const ['Fatou NDIAYE'],
      )));
      await tester.pumpAndSettle();

      Future<void> answer(String question, {bool oui = false}) async {
        final q = find.textContaining(question);
        await tester.ensureVisible(q);
        await tester.pumpAndSettle();
        // Les puces « Oui »/« Non » de CETTE question (colonne _yesNoRow
        // englobante — le premier Column ancêtre du libellé).
        final column =
            find.ancestor(of: q.first, matching: find.byType(Column)).first;
        await tester.tap(find.descendant(
            of: column, matching: find.text(oui ? 'Oui' : 'Non')));
        await tester.pumpAndSettle();
      }

      // Q1 : Oui → sélectionne l'enfant + précision.
      await answer("L'un des voyageurs est-il malade", oui: true);
      await tester.tap(find.text('Fatou NDIAYE'));
      await tester.pumpAndSettle();
      await tester.enterText(
          find.widgetWithText(TextFormField, 'Veuillez préciser *'),
          'rhume');
      // Q2-Q6 : Non.
      for (final q in [
        "12 derniers mois",
        'maladie chronique',
        'enceinte',
        'raisons médicales',
        'activité sportive',
      ]) {
        await answer(q);
      }

      // Attestation d'exactitude + continuer.
      await tester.ensureVisible(
          find.textContaining('Je certifie'));
      await tester.tap(find.textContaining('Je certifie'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Continuer vers les assurances'));
      await tester.pumpAndSettle();
      // Dialogue « analyse médicale » → Continuer.
      await tester.tap(find.text('Continuer').last);
      await tester.pumpAndSettle();

      expect(submitted, isNotNull);
      final enfants = submitted!['enfants'] as List;
      final fatou = enfants.firstWhere(
          (e) => (e['nom'] as String).contains('Fatou'))['reponses']
          as Map;
      expect(fatou['malade_souscription'], 'oui');
      expect(fatou['malade_12_mois'], 'non');
    });
  });
}
