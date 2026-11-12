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

/// Étape « Questionnaire » (kit) : les 6 questions sont posées **une fois pour
/// le groupe de voyageurs**. Sur une réponse « Oui », l'utilisateur désigne la
/// ou les personnes concernées (liste des voyageurs) puis précise la situation
/// — la précision est associée aux personnes sélectionnées (workflow §4.3).
///
/// - [adultIncluded] = false : souscription « enfants mineurs uniquement » —
///   le parent ne voyage pas, aucun questionnaire adulte n'est affiché.
/// - Un seul voyageur : formulation individuelle, pas de sélecteur de personne.
/// - Plusieurs voyageurs : formulation groupe + sélecteur de personnes.
class StepMedicalScreen extends StatefulWidget {
  const StepMedicalScreen({
    super.key,
    required this.onContinue,
    this.mineurs = const [],
    this.adultIncluded = true,
    this.adultName,
  });

  final void Function(MedicalFormData data) onContinue;

  /// Prénom/nom de chaque enfant déclaré au voyage.
  final List<String> mineurs;

  /// L'adulte (souscripteur) fait partie des voyageurs assurés.
  final bool adultIncluded;

  /// Libellé affiché pour l'adulte dans le sélecteur de personnes.
  final String? adultName;

  @override
  State<StepMedicalScreen> createState() => _StepMedicalScreenState();
}

class _StepMedicalScreenState extends State<StepMedicalScreen> {
  final _formKey = GlobalKey<FormState>();

  /// Réponse Oui/Non par question (clé interne).
  final Map<String, String?> _answers = {
    for (final q in _questions) q.key: null,
  };

  /// Personnes concernées par question (index dans [_travelers]) — utilisé
  /// uniquement quand la réponse est « oui » et qu'il y a plusieurs voyageurs.
  final Map<String, Set<int>> _persons = {
    for (final q in _questions) q.key: <int>{},
  };

  /// « Veuillez préciser » par question (obligatoire si « oui »).
  final Map<String, TextEditingController> _precs = {
    for (final q in _questions) q.key: TextEditingController(),
  };

  final _moisGrossesseController = TextEditingController();

  bool _declarationSante = false;
  String? _error;

  /// Voyageurs assurés : adulte (s'il voyage) puis chaque enfant.
  List<String> get _travelers => [
        if (widget.adultIncluded) widget.adultName ?? 'Vous (adulte)',
        ...widget.mineurs,
      ];

  bool get _isGroup => _travelers.length > 1;

  /// Souscription « un seul enfant voyageur » : formulation individuelle pour
  /// l'enfant (le parent répond à sa place).
  bool get _soloChild => !widget.adultIncluded && widget.mineurs.length == 1;

  bool get _pregnancyIneligible {
    if (_answers['enceinte'] != 'oui') return false;
    final months = int.tryParse(_moisGrossesseController.text.trim());
    return months != null && months > 5;
  }

  @override
  void dispose() {
    for (final c in _precs.values) {
      c.dispose();
    }
    _moisGrossesseController.dispose();
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
      setState(
          () => _error = 'Veuillez certifier l’exactitude des informations.');
      return;
    }
    for (final q in _questions) {
      if (_answers[q.key] == null) {
        setState(
            () => _error = 'Veuillez répondre à toutes les questions médicales.');
        return;
      }
      if (_answers[q.key] == 'oui' &&
          _isGroup &&
          (_persons[q.key]?.isEmpty ?? true)) {
        setState(() => _error =
            'Sélectionnez la ou les personnes concernées par la question ${q.index + 1}.');
        return;
      }
    }
    if (_answers['enceinte'] == 'oui') {
      final months = int.tryParse(_moisGrossesseController.text.trim());
      if (months == null || months < 1) {
        setState(() =>
            _error = 'Veuillez indiquer le nombre de mois de grossesse.');
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

    // Toute réponse « Oui » envoie le dossier au pôle santé de MHC (§4.3).
    final requiresMedicalReview =
        _answers.values.any((v) => v == 'oui');
    if (requiresMedicalReview && mounted) {
      final proceed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
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
            'Votre dossier sera redirigé vers le service médical de MHC '
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

    String? prec(String key) {
      final t = _precs[key]!.text.trim();
      return t.isEmpty ? null : t;
    }

    final moisGrossesse = _answers['enceinte'] == 'oui'
        ? int.tryParse(_moisGrossesseController.text.trim())
        : null;

    String a(String key) => _answers[key] ?? 'non';

    /// Noms des personnes concernées par la question (pour la revue MHC).
    List<String> personsOf(String key) {
      final sel = _persons[key] ?? const <int>{};
      final t = _travelers;
      if (sel.isEmpty) {
        // Voyageur unique : la réponse « oui » le concerne.
        return t;
      }
      return [for (final i in sel.toList()..sort()) t[i]];
    }

    final reponses = <String, dynamic>{
      'version': 'group_v2',
      'declaration_sante': true,
      'date_soumission': DateTime.now().toIso8601String(),
      'adulte_voyage': widget.adultIncluded,
      'voyageurs': _travelers,
      // Clés historiques conservées : le moteur de décision lit « oui ».
      'malade_souscription': a('malade_souscription'),
      'maladeSouscription': a('malade_souscription'),
      'malade_12_mois': a('malade_12_mois'),
      'malade12Mois': a('malade_12_mois'),
      'maladie_chronique': a('maladie_chronique'),
      'maladieChronique': a('maladie_chronique'),
      'enceinte': a('enceinte'),
      'pregnancy': a('enceinte'),
      if (moisGrossesse != null) 'mois_grossesse': moisGrossesse,
      if (moisGrossesse != null) 'moisGrossesse': moisGrossesse,
      'voyage_medical': a('voyage_medical'),
      'voyageMedical': a('voyage_medical'),
      'activite_sportive_pro': a('activite'),
      'activiteSportivePro': a('activite'),
      // Personnes concernées par chaque réponse « oui » (revue médicale).
      for (final q in _questions)
        if (a(q.key) == 'oui') '${q.key}_personnes': personsOf(q.key),
      // Réponses détaillées par personne (compatibilité moteur + revue).
      if (widget.adultIncluded)
        'adult': {
          'nom': widget.adultName ?? 'Adulte',
          'reponses': {
            for (final q in _questions) q.key: _adultAnswer(q.key),
            for (final q in _questions)
              if (_adultAnswer(q.key) == 'oui' && prec(q.key) != null)
                '${q.key}_precision': prec(q.key),
          },
        },
      if (widget.mineurs.isNotEmpty)
        'enfants': [
          for (var j = 0; j < widget.mineurs.length; j++)
            {
              'nom': widget.mineurs[j],
              'reponses': {
                for (final q in _questions)
                  q.key: _childAnswer(j, q.key),
                for (final q in _questions)
                  if (_childAnswer(j, q.key) == 'oui' && prec(q.key) != null)
                    '${q.key}_precision': prec(q.key),
              },
            },
        ],
      for (final q in _questions)
        if (prec(q.key) != null) '${q.key}_precision': prec(q.key),
    };

    widget.onContinue(MedicalFormData(reponses: reponses));
  }

  /// Réponse d'un enfant à une question : « oui » si l'enfant est désigné,
  /// « non » sinon. Enfant seul : la réponse du formulaire s'applique à lui.
  String _childAnswer(int childIndex, String key) {
    if (_answers[key] != 'oui') return _answers[key] ?? 'non';
    final travelerIndex = childIndex + (widget.adultIncluded ? 1 : 0);
    final sel = _persons[key];
    if (sel == null || sel.isEmpty) return 'oui'; // voyageur unique
    return sel.contains(travelerIndex) ? 'oui' : 'non';
  }

  /// Réponse de l'adulte à une question (sélecteur de personnes en groupe).
  String _adultAnswer(String key) {
    if (_answers[key] != 'oui') return _answers[key] ?? 'non';
    final sel = _persons[key];
    if (sel == null || sel.isEmpty) return 'oui';
    return sel.contains(0) ? 'oui' : 'non';
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
              Text(
                _isGroup
                    ? 'Répondez pour l\'ensemble des voyageurs assurés : ${_travelers.join(', ')}.'
                    : _soloChild
                        ? 'Répondez pour l\'enfant voyageur : ${_travelers.first}.'
                        : 'Répondez pour le voyageur assuré.',
                style:
                    const TextStyle(fontSize: 13, color: AppColors.mutedText),
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
                    for (final q in _questions) ...[
                      _yesNoRow(
                        '${q.index + 1}. ${_questionLabel(q)}',
                        _answers[q.key],
                        (v) => setState(() {
                          _answers[q.key] = v;
                          if (v != 'oui') {
                            _precs[q.key]!.clear();
                            _persons[q.key]!.clear();
                            if (q.key == 'enceinte') {
                              _moisGrossesseController.clear();
                            }
                          }
                        }),
                      ),
                      if (_answers[q.key] == 'oui') ...[
                        if (_isGroup) _personSelector(q.key),
                        if (q.key == 'enceinte') ...[
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
                              if (_answers['enceinte'] != 'oui') return null;
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
                        _preciserField(_precs[q.key]!),
                      ],
                      const SizedBox(height: 12),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
              MHSurfaceCard(
                padding: const EdgeInsets.all(16),
                child: Material(
                  type: MaterialType.transparency,
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

  String _questionLabel(_MedicalQuestion q) {
    if (_isGroup) return q.groupLabel;
    if (_soloChild) return q.childLabel;
    return q.adultLabel;
  }

  /// Liste des voyageurs à cocher quand une question de groupe reçoit « Oui ».
  Widget _personSelector(String key) {
    final t = _travelers;
    final sel = _persons[key]!;
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Personne(s) concernée(s) *',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: AppColors.secondary,
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              for (var i = 0; i < t.length; i++)
                FilterChip(
                  label: Text(t[i]),
                  selected: sel.contains(i),
                  onSelected: (v) => setState(() {
                    if (v) {
                      sel.add(i);
                    } else {
                      sel.remove(i);
                    }
                  }),
                  selectedColor:
                      AppColors.brandTeal.withValues(alpha: 0.18),
                  labelStyle: TextStyle(
                    color: sel.contains(i)
                        ? const Color(0xFF087F72)
                        : AppColors.secondary,
                  ),
                ),
            ],
          ),
        ],
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
          hintText: 'Décrivez la situation',
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

/// Une question médicale du kit, déclinée en formulation adulte / enfant seul /
/// groupe de voyageurs.
class _MedicalQuestion {
  const _MedicalQuestion(
    this.index,
    this.key, {
    required this.adultLabel,
    required this.childLabel,
    required this.groupLabel,
  });

  final int index;
  final String key;
  final String adultLabel;
  final String childLabel;
  final String groupLabel;
}

const _questions = [
  _MedicalQuestion(
    0,
    'malade_souscription',
    adultLabel: 'Êtes-vous malade au moment de la souscription ?',
    childLabel: 'L\'enfant est-il malade au moment de la souscription ?',
    groupLabel:
        'L\'un des voyageurs est-il malade au moment de la souscription ?',
  ),
  _MedicalQuestion(
    1,
    'malade_12_mois',
    adultLabel: 'Avez-vous été malade au cours des 12 derniers mois ?',
    childLabel:
        'L\'enfant a-t-il été malade au cours des 12 derniers mois ?',
    groupLabel:
        'L\'un des voyageurs a-t-il été malade au cours des 12 derniers mois ?',
  ),
  _MedicalQuestion(
    2,
    'maladie_chronique',
    adultLabel: 'Souffrez-vous d\'une maladie chronique ?',
    childLabel: 'L\'enfant souffre-t-il d\'une maladie chronique ?',
    groupLabel:
        'L\'un des voyageurs souffre-t-il d\'une maladie chronique ?',
  ),
  _MedicalQuestion(
    3,
    'enceinte',
    adultLabel: 'Êtes-vous enceinte au moment de la souscription ?',
    childLabel: 'L\'enfant est-elle enceinte au moment de la souscription ?',
    groupLabel:
        'L\'une des voyageuses est-elle enceinte au moment de la souscription ?',
  ),
  _MedicalQuestion(
    4,
    'voyage_medical',
    adultLabel: 'Voyagez-vous pour des raisons médicales ?',
    childLabel:
        'Le voyage de l\'enfant est-il prévu pour des raisons médicales ?',
    groupLabel: 'Le voyage est-il prévu pour des raisons médicales ?',
  ),
  _MedicalQuestion(
    5,
    'activite',
    adultLabel:
        'Prévoyez-vous une activité sportive, d\'aventure ou professionnelle ?',
    childLabel:
        'L\'enfant prévoit-il une activité sportive, d\'aventure ou professionnelle ?',
    groupLabel:
        'L\'un des voyageurs prévoit-il une activité sportive, d\'aventure ou professionnelle ?',
  ),
];
