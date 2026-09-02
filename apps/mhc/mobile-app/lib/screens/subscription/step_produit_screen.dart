import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../core/config/api_config.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../models/product.dart';
import '../../models/subscription_quote.dart';
import 'product_detail_screen.dart';

String _voyageDureeSubtitle(ProductModel p, int? voyageDureeJours) {
  if (voyageDureeJours != null && voyageDureeJours > 0) {
    return '$voyageDureeJours jours de voyage';
  }
  final v = p.dureeValiditeJours;
  if (v != null && v > 0) return 'Validité produit : $v j';
  return 'Durée à définir';
}

SubscriptionQuoteLine? _devisLineFor(
  ProductModel p,
  Map<int, SubscriptionQuoteLine>? devisParProduit,
) {
  return devisParProduit?[p.id];
}

int? _optInt(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value.toString().trim());
}

String? _resolveCourtierLogoUrl(Map<String, dynamic>? courtier) {
  if (courtier == null) return null;
  final rawLogo = courtier['logo_url']?.toString().trim();
  if (rawLogo != null && rawLogo.isNotEmpty && rawLogo.startsWith('http')) {
    return rawLogo;
  }
  final courtierId = _optInt(courtier['id']);
  if (courtierId != null) {
    return '${ApiConfig.baseUrl}/courtiers/$courtierId/logo';
  }
  return null;
}

String _zoneBadgeText(ProductModel p, SubscriptionQuoteLine? line) {
  final z = line?.zoneLibelleFr?.trim();
  if (z != null && z.isNotEmpty) return z;
  final code = line?.zoneGeographiqueCode?.trim();
  if (code != null && code.isNotEmpty) return 'Zone : $code';
  final n = p.geographicalZonesCount;
  if (n > 0) return '$n zones (fiche produit)';
  return 'Couverture voyage';
}

/// Ex. 71875 → « 71 875 » (lisible, une ligne courte sur la carte).
String _formatMontantCarte(double value) {
  final n = value.round();
  final neg = n < 0;
  final digits = (neg ? -n : n).toString();
  final buf = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) buf.write(' ');
    buf.write(digits[i]);
  }
  return neg ? '-$buf' : buf.toString();
}

Widget _priceBlock(
  BuildContext context,
  ProductModel pm, {
  Map<int, SubscriptionQuoteLine>? devisParProduit,
  required bool loadingDevis,
}) {
  final primaryStyle = const TextStyle(
    fontSize: 14,
    fontWeight: FontWeight.bold,
    color: AppColors.primary,
    height: 1.25,
  );
  final cur = pm.currency ?? 'XAF';
  if (loadingDevis) {
    return Text('Calcul…', style: primaryStyle, textAlign: TextAlign.end);
  }
  final line = devisParProduit?[pm.id];
  if (line != null) {
    return Text(
      '${_formatMontantCarte(line.prixApplique)} $cur',
      style: primaryStyle,
      textAlign: TextAlign.end,
      maxLines: 1,
      overflow: TextOverflow.fade,
      softWrap: false,
    );
  }
  final c = pm.cout;
  final s = c % 1 == 0 ? _formatMontantCarte(c) : c.toString();
  return Text(
    '$s $cur',
    style: primaryStyle,
    textAlign: TextAlign.end,
    maxLines: 1,
    overflow: TextOverflow.fade,
    softWrap: false,
  );
}

/// Étape 2 : Sélection du produit – liste de cartes, "Voir les détails", photo (optionnelle), déclarations, bouton Continuer.
class StepProduitScreen extends StatefulWidget {
  const StepProduitScreen({
    super.key,
    required this.onContinue,
    required this.canalDistribution,
    required this.selectedCourtierId,
    required this.courtiers,
    required this.onCanalChanged,
    required this.onCourtierChanged,
    this.onBackToVoyage,
    this.initialMedicalPhotoPath,
    this.products,
    this.devisParProduit,
    this.loadingDevis = false,
    this.residenceCountryName,
    this.destinationCountryName,
    this.voyageDureeJours,
    this.subscriberAge,
    this.surprimesAge = const [],
    this.fraisSurPrimePct = 15,
  });

  /// Appelé avec (productId, medicalPhotoPath). productId vient de la carte sélectionnée.
  final void Function(int productId, String? medicalPhotoPath) onContinue;
  final String canalDistribution;
  final int? selectedCourtierId;
  final List<Map<String, dynamic>> courtiers;
  final Future<void> Function(String value) onCanalChanged;
  final Future<void> Function(int? courtierId) onCourtierChanged;
  /// Retour à l’étape voyage si aucune offre ne correspond au parcours.
  final VoidCallback? onBackToVoyage;
  final String? initialMedicalPhotoPath;
  /// Produits renvoyés par l’API (liste vide = aucune offre pour ce voyage, pas de fallback).
  final List<ProductModel>? products;
  /// Devis par produit (POST /subscriptions/quote-prices).
  final Map<int, SubscriptionQuoteLine>? devisParProduit;
  final bool loadingDevis;
  final String? residenceCountryName;
  final String? destinationCountryName;
  final int? voyageDureeJours;
  final int? subscriberAge;
  final List<SurprimeAgeRow> surprimesAge;
  final double fraisSurPrimePct;

  @override
  State<StepProduitScreen> createState() => _StepProduitScreenState();
}

class _StepProduitScreenState extends State<StepProduitScreen> {
  int? _selectedProductIndex;
  bool _acceptCgu = false;
  bool _acceptExclusions = false;
  String? _medicalPhotoPath;

  List<ProductModel> get _productList => widget.products ?? const [];

  @override
  void didUpdateWidget(covariant StepProduitScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selectedProductIndex != null && _selectedProductIndex! >= _productList.length) {
      _selectedProductIndex = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);
    final bottomPadding = mq.padding.bottom + mq.viewInsets.bottom + 24;
    return Container(
      color: kMhContentBackground,
      child: SingleChildScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: EdgeInsets.fromLTRB(20, 20, 20, bottomPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Sélection du produit',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: const Color(0xFF1E293B),
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Canal de souscription',
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: const Color(0xFF1E293B),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: RadioListTile<String>(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          value: 'assureur',
                          groupValue: widget.canalDistribution,
                          title: const Text('Compagnie directe', style: TextStyle(fontSize: 13)),
                          onChanged: (v) {
                            if (v != null) widget.onCanalChanged(v);
                          },
                        ),
                      ),
                      Expanded(
                        child: RadioListTile<String>(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          value: 'courtier',
                          groupValue: widget.canalDistribution,
                          title: const Text('Via courtier', style: TextStyle(fontSize: 13)),
                          onChanged: (v) {
                            if (v != null) widget.onCanalChanged(v);
                          },
                        ),
                      ),
                    ],
                  ),
                  if (widget.canalDistribution == 'courtier') ...[
                    const SizedBox(height: 6),
                    if (widget.courtiers.isEmpty)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text(
                          'Aucun courtier disponible pour ce contexte. Vous pouvez choisir "Compagnie directe".',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: const Color(0xFF64748B),
                          ),
                        ),
                      ),
                    if (widget.courtiers.isNotEmpty)
                      Text(
                        'Courtiers éligibles : ${widget.courtiers.map((c) => c['nom']?.toString() ?? '').where((s) => s.trim().isNotEmpty).join(', ')}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: const Color(0xFF64748B),
                        ),
                      ),
                  ],
                ],
              ),
            ),
            if (widget.loadingDevis) ...[
              const SizedBox(height: 10),
              const LinearProgressIndicator(minHeight: 3, color: AppColors.primary),
              const SizedBox(height: 8),
              Text(
                'Calcul des tarifs selon votre voyage…',
                style: theme.textTheme.bodySmall?.copyWith(color: const Color(0xFF64748B)),
              ),
            ] else if (widget.devisParProduit != null && widget.devisParProduit!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                'Tarif = prime d’assurance + frais de services selon votre pays de résidence, la destination et la durée (identique au paiement).',
                style: theme.textTheme.bodySmall?.copyWith(color: const Color(0xFF64748B)),
              ),
            ],
            const SizedBox(height: 16),
            if (_productList.isEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Icon(
                      Icons.travel_explore_outlined,
                      size: 48,
                      color: AppColors.mutedText,
                    ),
                    const SizedBox(height: 14),
                    Text(
                      'Aucune offre pour ce voyage',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: const Color(0xFF1E293B),
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Aucun produit n’est disponible pour votre combinaison pays de résidence / '
                      'destination : il n’y a pas d’assureur partenaire configuré pour ce parcours '
                      '(par ex. inter-Afrique vers ce pays). Modifiez la destination ou contactez '
                      'Mobility Healthcare.',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: const Color(0xFF64748B),
                        height: 1.45,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    if (widget.onBackToVoyage != null) ...[
                      const SizedBox(height: 20),
                      FilledButton(
                        onPressed: widget.onBackToVoyage,
                        style: FilledButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                        child: const Text('Modifier le voyage'),
                      ),
                    ],
                  ],
                ),
              )
            else
              ...List.generate(_productList.length, (i) {
                final p = _productList[i];
                final name = p.nom;
                final assureur = p.assureur ?? '';
                final assureurId = p.assureurId;
                Map<String, dynamic>? linkedCourtier;
                if (widget.canalDistribution == 'courtier' && assureurId != null) {
                  for (final c in widget.courtiers) {
                    if (c['assureur_id'] == assureurId) {
                      linkedCourtier = c;
                      break;
                    }
                  }
                }
                final isCourtierMode = linkedCourtier != null;
                final partnerName =
                    isCourtierMode ? (linkedCourtier['nom']?.toString() ?? assureur) : assureur;
                final courtierId = _optInt(linkedCourtier?['id']);
                final duree = _voyageDureeSubtitle(p, widget.voyageDureeJours);
                final priceBlock = _priceBlock(
                  context,
                  p,
                  devisParProduit: widget.devisParProduit,
                  loadingDevis: widget.loadingDevis,
                );
                final line = _devisLineFor(p, widget.devisParProduit);
                final zoneLabel = _zoneBadgeText(p, line);
                final logoUrl = isCourtierMode
                    ? _resolveCourtierLogoUrl(linkedCourtier)
                    : (assureurId != null
                          ? '${ApiConfig.baseUrl}/assureurs/$assureurId/logo'
                          : null);
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _ProductCard(
                    name: name,
                    assureur: partnerName,
                    logoUrl: logoUrl,
                    duree: duree,
                    priceBlock: priceBlock,
                    zoneLabel: zoneLabel,
                    isSelected: _selectedProductIndex == i,
                    onTap: () => setState(() => _selectedProductIndex = i),
                    onViewDetails: () {
                      final q = _devisLineFor(p, widget.devisParProduit);
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => ProductDetailScreen(
                            productId: p.id,
                            productName: name,
                            assureur: partnerName,
                            quoteLine: q,
                            currency: p.currency ?? 'XAF',
                            subscriberAge: widget.subscriberAge,
                            residenceCountryName: widget.residenceCountryName,
                            destinationCountryName: widget.destinationCountryName,
                            voyageDureeJours: widget.voyageDureeJours,
                            surprimesAge: widget.surprimesAge,
                            fraisSurPrimePct: widget.fraisSurPrimePct,
                          ),
                        ),
                      );
                    },
                  ),
                );
              }),
            if (_selectedProductIndex != null) ...[
              const SizedBox(height: 20),
              _PhotoMedicaleCard(
                imagePath: _medicalPhotoPath ?? widget.initialMedicalPhotoPath,
                onPhotoPicked: (path) => setState(() => _medicalPhotoPath = path),
              ),
              const SizedBox(height: 16),
              _DeclarationsCard(
                acceptCgu: _acceptCgu,
                acceptExclusions: _acceptExclusions,
                onCguChanged: (v) => setState(() => _acceptCgu = v ?? false),
                onExclusionsChanged: (v) => setState(() => _acceptExclusions = v ?? false),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: (_selectedProductIndex != null && _acceptCgu && _acceptExclusions)
                      ? () {
                          final photo = _medicalPhotoPath ?? widget.initialMedicalPhotoPath;
                          if (photo == null || photo.trim().isEmpty) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Ajoutez une photo portrait pour l’e-carte (caméra ou galerie) avant de continuer.',
                                ),
                                backgroundColor: AppColors.danger,
                              ),
                            );
                            return;
                          }
                          final p = _productList[_selectedProductIndex!];
                          widget.onContinue(p.id, photo.trim());
                        }
                      : null,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: (_acceptCgu && _acceptExclusions)
                        ? AppColors.primary
                        : const Color(0xFF94A3B8),
                    foregroundColor: Colors.white,
                    disabledBackgroundColor: const Color(0xFF94A3B8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text('Continuer vers les formulaires'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ProductCard extends StatelessWidget {
  const _ProductCard({
    required this.name,
    required this.assureur,
    this.logoUrl,
    required this.duree,
    required this.priceBlock,
    required this.zoneLabel,
    required this.isSelected,
    required this.onTap,
    required this.onViewDetails,
  });

  final String name, assureur, duree;
  final Widget priceBlock;
  final String zoneLabel;
  final String? logoUrl;
  final bool isSelected;
  final VoidCallback onTap;
  final VoidCallback onViewDetails;

  @override
  Widget build(BuildContext context) {
    return Container(
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
          Row(
            children: [
              if (logoUrl != null && logoUrl!.isNotEmpty)
                ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: Image.network(
                    logoUrl!,
                    width: 48,
                    height: 48,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => _avatarFallback(),
                  ),
                )
              else
                _avatarFallback(),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      assureur,
                      style: const TextStyle(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      duree,
                      style: const TextStyle(
                        color: Color(0xFF64748B),
                        fontSize: 12,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  name,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1E293B),
                  ),
                  overflow: TextOverflow.visible,
                  maxLines: 3,
                ),
              ),
              const SizedBox(width: 8),
              Flexible(
                child: priceBlock,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              zoneLabel,
              style: const TextStyle(
                fontSize: 12,
                color: AppColors.primary,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Couverture complète pour vos déplacements internationaux.',
            style: TextStyle(
              fontSize: 13,
              color: Color(0xFF64748B),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.success.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Text(
                  'Actif',
                  style: TextStyle(
                    fontSize: 12,
                    color: AppColors.success,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              GestureDetector(
                onTap: onViewDetails,
                child: const Text(
                  'Voir les détails',
                  style: TextStyle(
                    fontSize: 14,
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600,
                    decoration: TextDecoration.underline,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: onTap,
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.primary,
                side: BorderSide(
                  color: isSelected ? AppColors.primary : const Color(0xFFE2E8F0),
                  width: isSelected ? 2 : 1,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: Text(isSelected ? 'Sélectionné' : 'Sélectionner'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _avatarFallback() {
    return CircleAvatar(
      radius: 24,
      backgroundColor: const Color(0xFFE2E8F0),
      child: Text(
        assureur.isNotEmpty ? assureur.substring(0, 1).toUpperCase() : '?',
        style: const TextStyle(
          fontWeight: FontWeight.bold,
          color: Color(0xFF64748B),
        ),
      ),
    );
  }
}

class _PhotoMedicaleCard extends StatelessWidget {
  const _PhotoMedicaleCard({
    this.imagePath,
    required this.onPhotoPicked,
  });

  final String? imagePath;
  final ValueChanged<String?> onPhotoPicked;

  Future<void> _pickImage(BuildContext context, ImageSource source) async {
    final isCamera = source == ImageSource.camera;
    if (isCamera) {
      final status = await Permission.camera.request();
      if (!status.isGranted) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Autorisation caméra requise pour prendre une photo.')),
          );
        }
        return;
      }
    } else {
      final status = await Permission.photos.request();
      if (!status.isGranted) {
        final storage = await Permission.storage.request();
        if (!storage.isGranted && !(await Permission.photos.isGranted)) {
          if (context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Autorisation galerie requise pour choisir une photo.')),
            );
          }
          return;
        }
      }
    }
    try {
      final picker = ImagePicker();
      final XFile? file = await picker.pickImage(
        source: source,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 82,
      );
      if (file != null) onPhotoPicked(file.path);
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erreur: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
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
          const Text(
            'Photo pour l’e-carte ( obligatoire )',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1E293B),
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Prenez une photo. Cette image sera utilisée pour votre carte numérique sur le web et dans l’application.',
            style: TextStyle(
              fontSize: 13,
              color: Color(0xFF64748B),
            ),
          ),
          if (imagePath != null && imagePath!.isNotEmpty) ...[
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Image.file(
                File(imagePath!),
                height: 120,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: () => onPhotoPicked(null),
              icon: const Icon(Icons.delete_outline, size: 18),
              label: const Text('Supprimer la photo'),
              style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            ),
            const SizedBox(height: 8),
          ],
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _pickImage(context, ImageSource.camera),
                  icon: const Icon(Icons.camera_alt, size: 20),
                  label: const Text('Caméra'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF1E293B),
                    side: const BorderSide(color: Color(0xFFE2E8F0)),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _pickImage(context, ImageSource.gallery),
                  icon: const Icon(Icons.photo_library, size: 20),
                  label: const Text('Galerie'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF1E293B),
                    side: const BorderSide(color: Color(0xFFE2E8F0)),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DeclarationsCard extends StatelessWidget {
  const _DeclarationsCard({
    required this.acceptCgu,
    required this.acceptExclusions,
    required this.onCguChanged,
    required this.onExclusionsChanged,
  });

  final bool acceptCgu;
  final bool acceptExclusions;
  final ValueChanged<bool?> onCguChanged;
  final ValueChanged<bool?> onExclusionsChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
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
          const Text(
            'Déclarations et consentements',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1E293B),
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Veuillez lire et accepter les conditions suivantes pour continuer',
            style: TextStyle(
              fontSize: 13,
              color: Color(0xFF64748B),
            ),
          ),
          const SizedBox(height: 12),
          CheckboxListTile(
            value: acceptCgu,
            onChanged: onCguChanged,
            title: const Text(
              'J\'ai lu et j\'accepte les conditions générales.',
              style: TextStyle(fontSize: 14, color: Color(0xFF1E293B)),
            ),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
            activeColor: AppColors.primary,
          ),
          CheckboxListTile(
            value: acceptExclusions,
            onChanged: onExclusionsChanged,
            title: const Text(
              'J\'ai lu et j\'accepte les exclusions.',
              style: TextStyle(fontSize: 14, color: Color(0xFF1E293B)),
            ),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
            activeColor: AppColors.primary,
          ),
        ],
      ),
    );
  }
}
