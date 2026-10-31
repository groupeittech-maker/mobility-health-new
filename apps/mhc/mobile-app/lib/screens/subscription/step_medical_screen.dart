import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../core/widgets/mh_text_highlight.dart';

/// Réponses du questionnaire médical (kit) — transmises au parent puis
/// soumises à l'API après la création de la souscription (étape Assurance).
class MedicalFormData {
  const MedicalFormData({required this.reponses});

  /// Map prête pour `QuestionnaireService.submitMedical` (clés snake/camel).
  final Map<String, dynamic> reponses;
}

/// Étape « Questionnaire » (kit) : Oui/Non + « veuillez préciser » uniquement
/// pour une réponse positive pertinente, attestation d'exactitude.
/// [mineurs] : prénom/nom de chaque enfant déclaré au voyage — chacun répond
/// à son propre questionnaire (workflow V3 §4.3), transmis dans
/// `reponses['enfants']` et analysé par le moteur de décision.
class StepMedicalScreen extends StatefulWidget {
  const StepMedicalScreen({
    super.key,
    required this.onContinue,
    this.mineurs = const [],
  });

  final void Function(MedicalFormData data) onContinue;
  final List<String> mineurs;

  @override
  State<StepMedicalScreen> createState() => _StepMedicalScreenState();
}

class _StepMedicalScreenState extends State<StepMedicalScreen> {
  final _formKey = GlobalKey<FormState>();

  String? _maladeSouscription;
  final _maladeSouscriptionPrec = TextEditingController();
  String? _malade12Mois;
  final _malade12MoisPrec = TextEditingController();
  String? _maladieChronique;
  final _maladieChroniquePrec = TextEditingController();
  String? _enceinte;
  final _moisGrossesseController = TextEditingController();
  String? _voyageMedical;
  String? _activite;
  final _activitePrec = TextEditingController();

  bool _declarationSante = false;
  String? _error;

  /// Réponses médicales par enfant : clé = index dans [widget.mineurs].
  final List<Map<String, String?>> _childAnswers = [];
  final List<Map<String, TextEditingController>> _childPrecisions = [];

  static const _childQuestions = [
    ('malade_12_mois', 'A-t-il(elle) été malade au cours des 12 derniers mois ?'),
    ('maladie_chronique', 'Souffre-t-il(elle) d\'une maladie chronique ?'),
    ('voyage_medical', 'Le voyage est-il prévu pour des raisons médicales ?'),
    ('enceinte_5mois', 'Est-elle enceinte de plus de 5 mois ?'),
  ];

  @override
  void initState() {
    super.initState();
    for (var i = 0; i < widget.mineurs.length; i++) {
      _childAnswers.add({for (final (key, _) in _childQuestions) key: null});
      _childPrecisions.add({for (final (key, _) in _childQuestions) key: TextEditingController()});
    }
  }

  bool get _pregnancyIneligible {
    if (_enceinte != 'oui') return false;
    final months = int.tryParse(_moisGrossesseController.text.trim());
    return months != null && months > 5;
  }

  @override
  void dispose() {
    _maladeSouscriptionPrec.dispose();
    _malade12MoisPrec.dispose();
    _maladieChroniquePrec.dispose();
    _moisGrossesseController.dispose();
    _activitePrec.dispose();
    for (final m in _childPrecisions) {
      for (final c in m.values) {
        c.dispose();
      }
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_pregnancyIneligible) {
      setState(() {
        _error =
            'Vous n\'êtes pas éligible pour être assuré par nos services (grossesse de plus de 5 mois).';
      });
      return;
    }
    if (!_formKey.currentState!.validate()) return;
    if (!_declarationSante) {
      setState(() => _error = 'Veuillez certifier l’exactitude des informations.');
      return;
    }
    if (_maladeSouscription == null ||
        _malade12Mois == null ||
        _maladieChronique == null ||
        _enceinte == null ||
        _voyageMedical == null ||
        _activite == null) {
      setState(() => _error = 'Veuillez répondre à toutes les questions médicales.');
      return;
    }
    for (var i = 0; i < widget.mineurs.length; i++) {
      final answered = _childAnswers[i];
      if (_childQuestions.any((q) => answered[q.$1] == null)) {
        setState(() => _error =
            'Répondez à toutes les questions pour ${widget.mineurs[i]}.');
        return;
      }
    }
    if (_enceinte == 'oui') {
      final months = int.tryParse(_moisGrossesseController.text.trim());
      if (months == null || months < 1) {
        setState(() => _error = 'Veuillez indiquer le nombre de mois de grossesse.');
        return;
      }
      if (months > 5) {
        setState(() {
          _error =
              'Vous n\'êtes pas éligible pour être assuré par nos services (grossesse de plus de 5 mois).';
        });
        return;
      }
    }

    // Une grossesse de plus de 5 mois chez n'importe quelle personne du groupe
    // (enfant comprise) entraîne le refus de tout le dossier (§4.3).
    if (_childAnswers.any(
        (a) => a['enceinte_5mois'] == 'oui')) {
      setState(() {
        _error =
            'Vous n\'êtes pas éligible pour être assuré par nos services (grossesse de plus de 5 mois).';
      });
      return;
    }

    // Toute réponse « Oui » (hors question grossesse), chez l'adulte comme chez
    // un enfant, envoie tout le dossier au pôle santé de MHC (§4.3).
    final childOui = _childAnswers.any((a) =>
        a.entries.any((e) => e.key != 'enceinte_5mois' && e.value == 'oui'));
    final requiresTechnicalReview = _maladeSouscription == 'oui' ||
        _malade12Mois == 'oui' ||
        _maladieChronique == 'oui' ||
        _voyageMedical == 'oui' ||
        _activite == 'oui' ||
        childOui;
    if (requiresTechnicalReview && mounted) {
      final proceed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16)),
          title: const Row(
            children: [
              Icon(Icons.medical_information_outlined,
                  color: AppColors.secondary),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Analyse médicale',
                  style: TextStyle(fontSize: 18),
                ),
              ),
            ],
          ),
          content: const Text(
            'Votre dossier sera redirigé vers le service technique de MHC '
            'qui prendra contact avec vous dans les plus brefs délais.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Revenir'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.secondary,
              ),
              child: const Text('Continuer'),
            ),
          ],
        ),
      );
      if (proceed != true || !mounted) return;
    }

    String? prec(TextEditingController c) {
      final t = c.text.trim();
      return t.isEmpty ? null : t;
    }

    final moisGrossesse = _enceinte == 'oui'
        ? int.tryParse(_moisGrossesseController.text.trim())
        : null;

    final reponses = <String, dynamic>{
      'version': 'simplified_v1',
      'declaration_sante': true,
      'date_soumission': DateTime.now().toIso8601String(),
      'malade_souscription': _maladeSouscription,
      'maladeSouscription': _maladeSouscription,
      'malade_12_mois': _malade12Mois,
      'malade12Mois': _malade12Mois,
      'maladie_chronique': _maladieChronique,
      'maladieChronique': _maladieChronique,
      'enceinte': _enceinte,
      'pregnancy': _enceinte,
      if (moisGrossesse != null) 'mois_grossesse': moisGrossesse,
      if (moisGrossesse != null) 'moisGrossesse': moisGrossesse,
      'voyage_medical': _voyageMedical,
      'voyageMedical': _voyageMedical,
      'activite_sportive_pro': _activite,
      'activiteSportivePro': _activite,
      if (widget.mineurs.isNotEmpty)
        'enfants': [
          for (var i = 0; i < widget.mineurs.length; i++)
            {
              'nom': widget.mineurs[i],
              'reponses': {
                for (final (key, _) in _childQuestions)
                  if (_childAnswers[i][key] != null) key: _childAnswers[i][key],
                for (final (key, _) in _childQuestions)
                  if (_childPrecisions[i][key]!.text.trim().isNotEmpty)
                    '${key}_precision': _childPrecisions[i][key]!.text.trim(),
              },
            },
        ],
      if (prec(_maladeSouscriptionPrec) != null)
        'malade_souscription_precision': prec(_maladeSouscriptionPrec),
      if (prec(_malade12MoisPrec) != null)
        'malade_12_mois_precision': prec(_malade12MoisPrec),
      if (prec(_maladieChroniquePrec) != null)
        'maladie_chronique_precision': prec(_maladieChroniquePrec),
      if (prec(_activitePrec) != null)
        'activite_precision': prec(_activitePrec),
    };

    widget.onContinue(MedicalFormData(reponses: reponses));
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
    return Container(
      color: kMhContentBackground,
      child: SingleChildScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: EdgeInsets.fromLTRB(
            20, 20, 20, mq.padding.bottom + mq.viewInsets.bottom + 24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const MHSectionTitle(title: 'Questionnaire médical'),
              const SizedBox(height: 8),
              const Text(
                'Répondez pour chaque voyageur assuré.',
                style: TextStyle(fontSize: 13, color: AppColors.mutedText),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.danger.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    _error!,
                    style:
                        const TextStyle(color: AppColors.danger, fontSize: 13),
                  ),
                ),
              ],
              if (_pregnancyIneligible) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.danger.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                        color: AppColors.danger.withValues(alpha: 0.35)),
                  ),
                  child: const Text(
                    'Vous n\'êtes pas éligible pour être assuré par nos services (grossesse de plus de 5 mois).',
                    style: TextStyle(color: AppColors.danger, fontSize: 13),
                  ),
                ),
              ],
              const SizedBox(height: 20),
              MHSurfaceCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _yesNoRow(
                      '1. Êtes-vous malade au moment de la souscription ?',
                      _maladeSouscription,
                      (v) => setState(() {
                        _maladeSouscription = v;
                        if (v != 'oui') _maladeSouscriptionPrec.clear();
                      }),
                    ),
                    if (_maladeSouscription == 'oui')
                      _preciserField(_maladeSouscriptionPrec),
                    const SizedBox(height: 12),
                    _yesNoRow(
                      '2. Avez-vous été malade au cours des 12 derniers mois ?',
                      _malade12Mois,
                      (v) => setState(() {
                        _malade12Mois = v;
                        if (v != 'oui') _malade12MoisPrec.clear();
                      }),
                    ),
                    if (_malade12Mois == 'oui')
                      _preciserField(_malade12MoisPrec),
                    const SizedBox(height: 12),
                    _yesNoRow(
                      '3. Souffrez-vous d\'une maladie chronique ?',
                      _maladieChronique,
                      (v) => setState(() {
                        _maladieChronique = v;
                        if (v != 'oui') _maladieChroniquePrec.clear();
                      }),
                    ),
                    if (_maladieChronique == 'oui')
                      _preciserField(_maladieChroniquePrec),
                    const SizedBox(height: 12),
                    _yesNoRow(
                      '4. Êtes-vous enceinte au moment de la souscription ?',
                      _enceinte,
                      (v) => setState(() {
                        _enceinte = v;
                        if (v != 'oui') _moisGrossesseController.clear();
                      }),
                    ),
                    if (_enceinte == 'oui') ...[
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: _moisGrossesseController,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly
                        ],
                        decoration: MHSurfaceCard.input(
                          labelText: 'De combien de mois ?',
                          isDense: true,
                        ),
                        onChanged: (_) => setState(() {}),
                        validator: (value) {
                          if (_enceinte != 'oui') return null;
                          final months =
                              int.tryParse((value ?? '').trim());
                          if (months == null || months < 1) {
                            return 'Indiquez le nombre de mois';
                          }
                          if (months > 5) {
                            return 'Non éligible au-delà de 5 mois';
                          }
                          return null;
                        },
                      ),
                    ],
                    const SizedBox(height: 12),
                    _yesNoRow(
                      '5. Voyagez-vous pour des raisons médicales ?',
                      _voyageMedical,
                      (v) => setState(() => _voyageMedical = v),
                    ),
                    const SizedBox(height: 12),
                    _yesNoRow(
                      '6. Prévoyez-vous une activité sportive, d\'aventure ou professionnelle ?',
                      _activite,
                      (v) => setState(() {
                        _activite = v;
                        if (v != 'oui') _activitePrec.clear();
                      }),
                    ),
                    if (_activite == 'oui') _preciserField(_activitePrec),
                  ],
                ),
              ),
              for (var i = 0; i < widget.mineurs.length; i++) ...[
                const SizedBox(height: 16),
                MHSurfaceCard(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.child_care_outlined,
                              color: AppColors.secondary, size: 20),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Questionnaire de ${widget.mineurs[i]}',
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: AppColors.secondary,
                                fontSize: 14,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      for (var q = 0; q < _childQuestions.length; q++) ...[
                        _yesNoRow(
                          '${q + 1}. ${_childQuestions[q].$2}',
                          _childAnswers[i][_childQuestions[q].$1],
                          (v) => setState(() {
                            _childAnswers[i][_childQuestions[q].$1] = v;
                            if (v != 'oui') {
                              _childPrecisions[i][_childQuestions[q].$1]!.clear();
                            }
                          }),
                        ),
                        if (_childAnswers[i][_childQuestions[q].$1] == 'oui')
                          _preciserField(
                              _childPrecisions[i][_childQuestions[q].$1]!),
                        const SizedBox(height: 12),
                      ],
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 16),
              MHSurfaceCard(
                padding: const EdgeInsets.all(16),
                child: CheckboxListTile(
                  value: _declarationSante,
                  onChanged: (v) =>
                      setState(() => _declarationSante = v ?? false),
                  title: const Text(
                    'Je certifie que les informations fournies sont exactes et complètes.',
                    style: TextStyle(fontSize: 14, color: Color(0xFF1E293B)),
                  ),
                  controlAffinity: ListTileControlAffinity.leading,
                  contentPadding: EdgeInsets.zero,
                  activeColor: AppColors.primary,
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _pregnancyIneligible ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.secondary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text('Continuer vers les assurances'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _preciserField(TextEditingController controller) {
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: TextFormField(
        controller: controller,
        maxLines: 2,
        decoration: MHSurfaceCard.input(
          labelText: 'Veuillez préciser *',
          hintText: 'Décrivez votre situation',
          isDense: true,
        ),
        validator: (v) =>
            (v == null || v.trim().isEmpty) ? 'Précisez votre réponse' : null,
      ),
    );
  }

  Widget _yesNoRow(
    String label,
    String? value,
    ValueChanged<String?> onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: AppColors.secondary,
              ),
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            ChoiceChip(
              label: const Text('Oui'),
              selected: value == 'oui',
              onSelected: (_) => onChanged('oui'),
              selectedColor: AppColors.brandTeal.withValues(alpha: 0.18),
              labelStyle: TextStyle(
                color: value == 'oui'
                    ? const Color(0xFF087F72)
                    : AppColors.secondary,
              ),
            ),
            const SizedBox(width: 8),
            ChoiceChip(
              label: const Text('Non'),
              selected: value == 'non',
              onSelected: (_) => onChanged('non'),
              selectedColor: AppColors.brandTeal.withValues(alpha: 0.18),
              labelStyle: TextStyle(
                color: value == 'non'
                    ? const Color(0xFF087F72)
                    : AppColors.secondary,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
