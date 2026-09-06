import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../core/widgets/mh_text_highlight.dart';
import '../../services/api_services.dart';

/// Étape 3 : Questionnaire médical simplifié (5 questions oui/non).
class StepMedicalScreen extends StatefulWidget {
  const StepMedicalScreen({
    super.key,
    required this.subscriptionId,
    this.medicalPhotoPath,
    required this.onContinue,
  });

  final int subscriptionId;
  final String? medicalPhotoPath;
  final VoidCallback onContinue;

  @override
  State<StepMedicalScreen> createState() => _StepMedicalScreenState();
}

class _StepMedicalScreenState extends State<StepMedicalScreen> {
  static const int _maxPhotoBytes = 5 * 1024 * 1024;

  final QuestionnaireService _questionnaireService = QuestionnaireService();
  final _formKey = GlobalKey<FormState>();
  final _moisGrossesseController = TextEditingController();

  bool _loading = false;
  String? _error;
  bool _declarationSante = false;
  String? _maladeSouscription;
  String? _malade12Mois;
  String? _maladieChronique;
  String? _enceinte;
  String? _voyageMedical;

  bool get _pregnancyIneligible {
    if (_enceinte != 'oui') return false;
    final months = int.tryParse(_moisGrossesseController.text.trim());
    return months != null && months > 5;
  }

  @override
  void dispose() {
    _moisGrossesseController.dispose();
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
    if (_pregnancyIneligible) {
      setState(() {
        _error = 'Vous n\'êtes pas éligible pour être assuré par nos services (grossesse de plus de 5 mois).';
      });
      return;
    }
    if (!_formKey.currentState!.validate() || !_declarationSante) {
      setState(() {
        _error = _declarationSante ? null : 'Veuillez accepter la déclaration santé.';
      });
      return;
    }
    if (_maladeSouscription == null ||
        _malade12Mois == null ||
        _maladieChronique == null ||
        _enceinte == null ||
        _voyageMedical == null) {
      setState(() => _error = 'Veuillez répondre à toutes les questions médicales.');
      return;
    }
    if (_enceinte == 'oui') {
      final months = int.tryParse(_moisGrossesseController.text.trim());
      if (months == null || months < 1) {
        setState(() => _error = 'Veuillez indiquer le nombre de mois de grossesse.');
        return;
      }
      if (months > 5) {
        setState(() {
          _error = 'Vous n\'êtes pas éligible pour être assuré par nos services (grossesse de plus de 5 mois).';
        });
        return;
      }
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
      color: kMhContentBackground,
      child: SingleChildScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: EdgeInsets.fromLTRB(20, 20, 20, mq.padding.bottom + mq.viewInsets.bottom + 24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const MHSectionTitle(title: 'Questionnaire médical'),
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
              if (_pregnancyIneligible) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.danger.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.danger.withValues(alpha: 0.35)),
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
                    Text(
                      'QUESTIONS MÉDICALES',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: AppColors.secondary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Répondez par Oui ou Non à chaque question.',
                      style: TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                    ),
                    const SizedBox(height: 16),
                    _yesNoRow(
                      '1. Êtes-vous malade au moment de la souscription ?',
                      _maladeSouscription,
                      (v) => setState(() => _maladeSouscription = v),
                    ),
                    const SizedBox(height: 12),
                    _yesNoRow(
                      '2. Avez-vous été malade au cours des 12 derniers mois ?',
                      _malade12Mois,
                      (v) => setState(() => _malade12Mois = v),
                    ),
                    const SizedBox(height: 12),
                    _yesNoRow(
                      '3. Souffrez-vous d\'une maladie chronique ?',
                      _maladieChronique,
                      (v) => setState(() => _maladieChronique = v),
                    ),
                    const SizedBox(height: 12),
                    _yesNoRow(
                      '4. Êtes-vous enceinte au moment de la souscription ?',
                      _enceinte,
                      (v) => setState(() {
                        _enceinte = v;
                        if (v != 'oui') {
                          _moisGrossesseController.clear();
                        }
                      }),
                    ),
                    if (_enceinte == 'oui') ...[
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: _moisGrossesseController,
                        keyboardType: TextInputType.number,
                        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                        decoration: MHSurfaceCard.input(
                          labelText: 'De combien de mois ?',
                          isDense: true,
                        ),
                        onChanged: (_) => setState(() {}),
                        validator: (value) {
                          if (_enceinte != 'oui') return null;
                          final months = int.tryParse((value ?? '').trim());
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
                      '5. Faites-vous un voyage à but médical ?',
                      _voyageMedical,
                      (v) => setState(() => _voyageMedical = v),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              MHSurfaceCard(
                padding: const EdgeInsets.all(16),
                child: CheckboxListTile(
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
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: (_loading || _pregnancyIneligible) ? null : _submit,
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
      ],
    );
  }

  Widget _buildEcartePhotoSummary(ThemeData theme) {
    final path = widget.medicalPhotoPath;
    final ok = path != null && path.trim().isNotEmpty;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceCard,
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
            const Text(
              'Aucune photo : vous devez d’abord l’ajouter à l’étape « Choix du produit » (caméra ou galerie), puis revenir ici.',
              style: TextStyle(fontSize: 13, color: Color(0xFF64748B), height: 1.35),
            ),
        ],
      ),
    );
  }
}
