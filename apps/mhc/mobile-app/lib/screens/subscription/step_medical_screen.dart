import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../services/api_services.dart';

/// Étape 3 : Questionnaire médical. La photo e-carte est prise à l’étape « Choix du produit »
/// puis envoyée ici dans le JSON (persist MinIO / génération e-carte, identique au web).
class StepMedicalScreen extends StatefulWidget {
  const StepMedicalScreen({
    super.key,
    required this.subscriptionId,
    this.medicalPhotoPath,
    required this.onContinue,
  });

  final int subscriptionId;
  /// Chemin local de la photo e-carte (obligatoire), fourni par l’étape « Choix du produit ».
  final String? medicalPhotoPath;
  final VoidCallback onContinue;

  @override
  State<StepMedicalScreen> createState() => _StepMedicalScreenState();
}

class _StepMedicalScreenState extends State<StepMedicalScreen> {
  static const int _maxPhotoBytes = 5 * 1024 * 1024;

  final QuestionnaireService _questionnaireService = QuestionnaireService();
  final _formKey = GlobalKey<FormState>();
  bool _loading = false;
  String? _error;
  bool _declarationSante = false;
  // Formulaire détaillé (ex-inscription)
  final List<String> _maladiesChecked = [];
  bool _aucuneMaladieChronique = false;
  final _maladiesAutreController = TextEditingController();
  String? _traitementRegulier;
  final _traitementPrecisionController = TextEditingController();
  String? _hospitalise12;
  final _hospitaliseRaisonController = TextEditingController();
  /// `oui` | `non` | `non_concerne` — réponse obligatoire avant envoi.
  String? _enceinte;
  String? _fumeur;
  final _fumeurCigarettesController = TextEditingController();
  String? _alcool;
  String? _alcoolFrequence;
  String? _activitePhysique;
  String? _allergies;
  final _allergiesPrecisionController = TextEditingController();
  String? _santeMentale;
  final _santeMentalePrecisionController = TextEditingController();

  static const _maladiesOptions = ['Diabète', 'HTA', 'Asthme', 'Épilepsie', 'Drépanocytose', 'Cardiopathie'];

  @override
  void initState() {
    super.initState();
    _traitementRegulier = 'oui';
    _hospitalise12 = 'oui';
    _fumeur = 'oui';
    _alcool = 'oui';
    _alcoolFrequence = 'occasionnellement';
    _activitePhysique = 'oui';
    _allergies = 'oui';
    _santeMentale = 'oui';
  }

  @override
  void dispose() {
    _maladiesAutreController.dispose();
    _traitementPrecisionController.dispose();
    _hospitaliseRaisonController.dispose();
    _fumeurCigarettesController.dispose();
    _allergiesPrecisionController.dispose();
    _santeMentalePrecisionController.dispose();
    super.dispose();
  }

  static String _dataUrlFromBytes(Uint8List bytes) {
    if (bytes.length >= 2 && bytes[0] == 0xFF && bytes[1] == 0xD8) {
      return 'data:image/jpeg;base64,${base64Encode(bytes)}';
    }
    if (bytes.length >= 8 &&
        bytes[0] == 0x89 &&
        bytes[1] == 0x50 &&
        bytes[2] == 0x4E &&
        bytes[3] == 0x47 &&
        bytes[4] == 0x0D &&
        bytes[5] == 0x0A &&
        bytes[6] == 0x1A &&
        bytes[7] == 0x0A) {
      return 'data:image/png;base64,${base64Encode(bytes)}';
    }
    return 'data:image/jpeg;base64,${base64Encode(bytes)}';
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate() || !_declarationSante) {
      setState(() {
        _error = _declarationSante ? null : 'Veuillez accepter la déclaration santé.';
      });
      return;
    }
    if (_enceinte == null) {
      setState(() {
        _error = 'Veuillez répondre : êtes-vous enceinte ? (Oui, Non ou Non concerné).';
      });
      return;
    }
    final photoPath = widget.medicalPhotoPath?.trim();
    if (photoPath == null || photoPath.isEmpty) {
      setState(() {
        _error =
            'Photo e-carte manquante. Revenez à l’étape « Choix du produit » pour ajouter une photo portrait (visage visible), puis repassez par ici.';
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final maladiesList = <String>[];
      if (_aucuneMaladieChronique) {
        maladiesList.add('Aucune');
      } else {
        maladiesList.addAll(_maladiesChecked);
        final autre = _maladiesAutreController.text.trim();
        if (autre.isNotEmpty) {
          maladiesList.add('Autre: $autre');
        }
      }
      final maladiesChroniques = maladiesList.isEmpty ? null : maladiesList.join(', ');
      String? traitementsEnCours;
      if (_traitementRegulier == 'oui') {
        final p = _traitementPrecisionController.text.trim();
        traitementsEnCours = 'Traitement médical régulier: Oui. ${p.isNotEmpty ? 'Type: $p' : ''}';
      } else if (_traitementRegulier == 'non') {
        traitementsEnCours = 'Traitement médical régulier: Non';
      }
      final parts = <String>[];
      if (_hospitalise12 == 'oui') {
        parts.add('Hospitalisation (12 derniers mois): Oui. Raison: ${_hospitaliseRaisonController.text.trim().isEmpty ? '—' : _hospitaliseRaisonController.text.trim()}');
      } else if (_hospitalise12 == 'non') {
        parts.add('Hospitalisation (12 derniers mois): Non');
      }
      if (_fumeur == 'oui') {
        parts.add('Fumeur: Oui${_fumeurCigarettesController.text.trim().isEmpty ? '' : ' (${_fumeurCigarettesController.text.trim()} cigarettes/jour)'}');
      } else if (_fumeur == 'non') {
        parts.add('Fumeur: Non');
      }
      if (_alcool == 'oui') {
        const freqLabels = {'occasionnellement': 'Occasionnellement', 'regulierement': 'Régulièrement (1 à 2 fois/semaine)', 'quotidiennement': 'Quotidiennement'};
        final f = _alcoolFrequence != null ? (freqLabels[_alcoolFrequence] ?? _alcoolFrequence) : '—';
        parts.add('Alcool: Oui. Fréquence: $f');
      } else if (_alcool == 'non') {
        parts.add('Alcool: Non');
      }
      if (_activitePhysique == 'oui') {
        parts.add('Activité physique régulière: Oui');
      } else if (_activitePhysique == 'non') {
        parts.add('Activité physique régulière: Non');
      }
      if (_allergies == 'oui') {
        parts.add('Allergies: Oui. ${_allergiesPrecisionController.text.trim().isEmpty ? '—' : _allergiesPrecisionController.text.trim()}');
      } else if (_allergies == 'non') {
        parts.add('Allergies: Non');
      }
      if (_santeMentale == 'oui') {
        parts.add('Santé mentale (trouble diagnostiqué): Oui. ${_santeMentalePrecisionController.text.trim().isEmpty ? '—' : _santeMentalePrecisionController.text.trim()}');
      } else if (_santeMentale == 'non') {
        parts.add('Santé mentale (trouble diagnostiqué): Non');
      }
      final antecedentsRecents = parts.isEmpty ? null : parts.join('\n');

      final reponses = <String, dynamic>{
        'declaration_sante': true,
        'date_soumission': DateTime.now().toIso8601String(),
        'enceinte': _enceinte,
        if (maladiesChroniques != null && maladiesChroniques.isNotEmpty) 'maladies_chroniques': maladiesChroniques,
        if (traitementsEnCours != null && traitementsEnCours.isNotEmpty) 'traitements_en_cours': traitementsEnCours,
        if (antecedentsRecents != null && antecedentsRecents.isNotEmpty) 'antecedents_recents': antecedentsRecents,
      };
      final file = File(photoPath);
      if (!await file.exists()) {
        throw Exception(
          'Fichier photo introuvable sur l’appareil. Reprenez la photo à l’étape « Choix du produit ».',
        );
      }
      final bytes = await file.readAsBytes();
      if (bytes.isEmpty) {
        throw Exception('La photo est vide. Veuillez en choisir une autre.');
      }
      if (bytes.length > _maxPhotoBytes) {
        throw Exception(
          'Photo trop volumineuse (max. 5 Mo). Reprenez-la ou choisissez une image plus légère.',
        );
      }
      final dataUrl = _dataUrlFromBytes(bytes);
      reponses['photo_medicale'] = dataUrl;
      reponses['photoMedicale'] = dataUrl;
      reponses['photo_identity'] = dataUrl;
      await _questionnaireService.submitMedical(widget.subscriptionId, reponses);
      if (mounted) widget.onContinue();
    } catch (e) {
      if (mounted) {
        String msg = e.toString().replaceFirst('Exception: ', '');
        if (e is DioException && e.response?.statusCode == 413) {
          msg = 'Données trop volumineuses. Choisissez une image plus légère à l’étape « Choix du produit ».';
        }
        setState(() {
          _error = msg;
          _loading = false;
        });
      }
      return;
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);
    return Container(
      color: const Color(0xFFE8F0F4),
      child: SingleChildScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: EdgeInsets.fromLTRB(20, 20, 20, mq.padding.bottom + mq.viewInsets.bottom + 24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Questionnaire médical',
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFF1E293B),
                ),
              ),
              const SizedBox(height: 12),
              _buildEcartePhotoSummary(theme),
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
                    style: const TextStyle(color: AppColors.danger, fontSize: 13),
                  ),
                ),
              ],
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.06),
                      blurRadius: 10,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'DONNÉES MÉDICALES',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: AppColors.primary,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text('Maladies chroniques', style: theme.textTheme.labelLarge),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        FilterChip(
                          label: const Text('Aucune'),
                          selected: _aucuneMaladieChronique,
                          onSelected: (v) {
                            setState(() {
                              if (v) {
                                _aucuneMaladieChronique = true;
                                _maladiesChecked.clear();
                              } else {
                                _aucuneMaladieChronique = false;
                              }
                            });
                          },
                          selectedColor: AppColors.primary.withValues(alpha: 0.2),
                        ),
                        ..._maladiesOptions.map((m) {
                          final checked = _maladiesChecked.contains(m);
                          return FilterChip(
                            label: Text(m),
                            selected: checked,
                            onSelected: (v) {
                              setState(() {
                                if (v) {
                                  _aucuneMaladieChronique = false;
                                  _maladiesChecked.add(m);
                                } else {
                                  _maladiesChecked.remove(m);
                                }
                              });
                            },
                            selectedColor: AppColors.primary.withValues(alpha: 0.2),
                          );
                        }),
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: _maladiesAutreController,
                      decoration: const InputDecoration(
                        labelText: 'Autre (précisez)',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text('Traitement médical régulier ?', style: theme.textTheme.labelLarge),
                    Row(
                      children: [
                        ChoiceChip(label: const Text('Oui'), selected: _traitementRegulier == 'oui', onSelected: (_) => setState(() => _traitementRegulier = 'oui'), selectedColor: AppColors.primary.withValues(alpha: 0.2)),
                        const SizedBox(width: 8),
                        ChoiceChip(label: const Text('Non'), selected: _traitementRegulier == 'non', onSelected: (_) => setState(() => _traitementRegulier = 'non'), selectedColor: AppColors.primary.withValues(alpha: 0.2)),
                      ],
                    ),
                    if (_traitementRegulier == 'oui') ...[
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: _traitementPrecisionController,
                        decoration: const InputDecoration(labelText: 'Précisez le type de traitement', border: OutlineInputBorder(), isDense: true),
                        maxLines: 2,
                      ),
                    ],
                    const SizedBox(height: 12),
                    Text('Hospitalisé au cours des 12 derniers mois ?', style: theme.textTheme.labelLarge),
                    Row(
                      children: [
                        ChoiceChip(label: const Text('Oui'), selected: _hospitalise12 == 'oui', onSelected: (_) => setState(() => _hospitalise12 = 'oui'), selectedColor: AppColors.primary.withValues(alpha: 0.2)),
                        const SizedBox(width: 8),
                        ChoiceChip(label: const Text('Non'), selected: _hospitalise12 == 'non', onSelected: (_) => setState(() => _hospitalise12 = 'non'), selectedColor: AppColors.primary.withValues(alpha: 0.2)),
                      ],
                    ),
                    if (_hospitalise12 == 'oui') ...[
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: _hospitaliseRaisonController,
                        decoration: const InputDecoration(labelText: 'Raison', border: OutlineInputBorder(), isDense: true),
                        maxLines: 2,
                      ),
                    ],
                    const SizedBox(height: 12),
                    Text('Êtes-vous enceinte ?', style: theme.textTheme.labelLarge),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        ChoiceChip(
                          label: const Text('Oui'),
                          selected: _enceinte == 'oui',
                          onSelected: (_) => setState(() => _enceinte = 'oui'),
                          selectedColor: AppColors.primary.withValues(alpha: 0.2),
                        ),
                        ChoiceChip(
                          label: const Text('Non'),
                          selected: _enceinte == 'non',
                          onSelected: (_) => setState(() => _enceinte = 'non'),
                          selectedColor: AppColors.primary.withValues(alpha: 0.2),
                        ),
                        ChoiceChip(
                          label: const Text('Non concerné'),
                          selected: _enceinte == 'non_concerne',
                          onSelected: (_) => setState(() => _enceinte = 'non_concerne'),
                          selectedColor: AppColors.primary.withValues(alpha: 0.2),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    _yesNoRow('Fumez-vous ?', _fumeur, (v) => setState(() => _fumeur = v), _fumeurCigarettesController, 'Cigarettes par jour'),
                    const SizedBox(height: 10),
                    _yesNoRow('Consommation d\'alcool ?', _alcool, (v) => setState(() => _alcool = v), null, null, true),
                    const SizedBox(height: 10),
                    _yesNoRow('Activité physique régulière ?', _activitePhysique, (v) => setState(() => _activitePhysique = v)),
                    const SizedBox(height: 10),
                    _yesNoRow('Allergies (médicaments, aliments) ?', _allergies, (v) => setState(() => _allergies = v), _allergiesPrecisionController, 'Précisez'),
                    const SizedBox(height: 10),
                    _yesNoRow('Trouble mental ou émotionnel diagnostiqué ?', _santeMentale, (v) => setState(() => _santeMentale = v), _santeMentalePrecisionController, 'Précisez'),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.06),
                      blurRadius: 10,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    CheckboxListTile(
                      value: _declarationSante,
                      onChanged: (v) => setState(() => _declarationSante = v ?? false),
                      title: const Text(
                        'Je déclare que les informations fournies sont exactes et complètes.',
                        style: TextStyle(fontSize: 14, color: Color(0xFF1E293B)),
                      ),
                      controlAffinity: ListTileControlAffinity.leading,
                      contentPadding: EdgeInsets.zero,
                      activeColor: AppColors.primary,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: _loading ? null : _submit,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: _loading
                      ? const SizedBox(
                          height: 24,
                          width: 24,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Text('Continuer vers le paiement'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _yesNoRow(
    String label,
    String? value,
    ValueChanged<String?> onChanged, [
    TextEditingController? detailController,
    String? detailLabel,
    bool isAlcool = false,
  ]) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 6),
        Row(
          children: [
            ChoiceChip(
              label: const Text('Oui'),
              selected: value == 'oui',
              onSelected: (_) => onChanged('oui'),
              selectedColor: AppColors.primary.withValues(alpha: 0.2),
            ),
            const SizedBox(width: 8),
            ChoiceChip(
              label: const Text('Non'),
              selected: value == 'non',
              onSelected: (_) => onChanged('non'),
              selectedColor: AppColors.primary.withValues(alpha: 0.2),
            ),
          ],
        ),
        if (value == 'oui') ...[
          const SizedBox(height: 8),
          if (isAlcool)
            DropdownButtonFormField<String>(
              value: _alcoolFrequence,
              decoration: const InputDecoration(labelText: 'Fréquence', border: OutlineInputBorder(), isDense: true),
              items: const [
                DropdownMenuItem(value: 'occasionnellement', child: Text('Occasionnellement')),
                DropdownMenuItem(value: 'regulierement', child: Text('Régulièrement (1-2/sem)')),
                DropdownMenuItem(value: 'quotidiennement', child: Text('Quotidiennement')),
              ],
              onChanged: (v) => setState(() => _alcoolFrequence = v),
            )
          else if (detailController != null && detailLabel != null)
            TextFormField(
              controller: detailController,
              decoration: InputDecoration(labelText: detailLabel, border: const OutlineInputBorder(), isDense: true),
              maxLines: detailLabel.contains('Précisez') ? 2 : 1,
            ),
        ],
      ],
    );
  }

  /// Aperçu de la photo e-carte (choisie à l’étape produit), sans texte explicatif sur l’e-carte.
  Widget _buildEcartePhotoSummary(ThemeData theme) {
    final path = widget.medicalPhotoPath;
    final ok = path != null && path.trim().isNotEmpty;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: ok ? const Color(0xFFE2E8F0) : AppColors.danger.withValues(alpha: 0.35),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (ok) ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.file(
                File(path!.trim()),
                height: 120,
                width: double.infinity,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text(
                    'Impossible d’afficher l’aperçu ; le fichier sera tout de même renvoyé si présent.',
                    style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Veuillez renseigner vos informations médicales et veuillez à ce qu’elles soient exactes.',
              style: TextStyle(fontSize: 14, color: Color(0xFF64748B), height: 1.35),
            ),
          ] else
            Text(
              'Aucune photo : vous devez d’abord l’ajouter à l’étape « Choix du produit » (caméra ou galerie), puis revenir ici.',
              style: const TextStyle(fontSize: 13, color: Color(0xFF64748B), height: 1.35),
            ),
        ],
      ),
    );
  }
}
