import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../core/config/api_config.dart';
import '../../core/constants/app_colors.dart';
import 'product_detail_screen.dart';

/// Étape 2 : Sélection du produit – liste de cartes, "Voir les détails", photo (optionnelle), déclarations, bouton Continuer.
class StepProduitScreen extends StatefulWidget {
  const StepProduitScreen({
    super.key,
    required this.onContinue,
    this.initialMedicalPhotoPath,
    this.products,
  });

  /// Appelé avec (productId, medicalPhotoPath). productId vient de la carte sélectionnée.
  final void Function(int productId, String? medicalPhotoPath) onContinue;
  final String? initialMedicalPhotoPath;
  /// Si fourni, afficher ces produits (API). Sinon utiliser la liste statique.
  final List<dynamic>? products;

  @override
  State<StepProduitScreen> createState() => _StepProduitScreenState();
}

class _StepProduitScreenState extends State<StepProduitScreen> {
  int? _selectedProductIndex;
  bool _acceptCgu = false;
  bool _acceptExclusions = false;
  String? _medicalPhotoPath;

  static const _productsFallback = [
    _ProductData(1, 'NSC voyage', 'NSIA Congo', '90 jours', '175 000 XAF', 3),
    _ProductData(2, 'voyageur+++', 'ARC', 'Durée flexible', '250 000 XAF', 4),
  ];

  List<dynamic> get _productList {
    if (widget.products != null && widget.products!.isNotEmpty) return widget.products!;
    return _productsFallback;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);
    final bottomPadding = mq.padding.bottom + mq.viewInsets.bottom + 24;
    return Container(
      color: const Color(0xFFE8F0F4),
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
            const SizedBox(height: 16),
            ...List.generate(_productList.length, (i) {
              final p = _productList[i];
              final name = p is _ProductData ? p.name : (p as dynamic).nom as String? ?? '';
              final assureur = (p is _ProductData ? p.assureur : (p as dynamic).assureur) as String? ?? '';
              final assureurId = p is _ProductData ? null : (p as dynamic).assureurId as int?;
              final duree = p is _ProductData ? p.duree : '${(p as dynamic).dureeValiditeJours ?? 0} jours';
              final price = p is _ProductData ? p.price : '${(p as dynamic).cout} ${(p as dynamic).currency ?? 'XAF'}';
              final zonesCount = p is _ProductData ? p.zonesCount : 0;
              final logoUrl = assureurId != null ? '${ApiConfig.baseUrl}/assureurs/$assureurId/logo' : null;
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _ProductCard(
                  name: name,
                  assureur: assureur,
                  logoUrl: logoUrl,
                  duree: duree,
                  price: price,
                  zonesCount: zonesCount,
                  isSelected: _selectedProductIndex == i,
                  onTap: () => setState(() => _selectedProductIndex = i),
                  onViewDetails: () {
                    final p = _productList[i];
                    final id = p is _ProductData ? p.id : (p as dynamic).id as int;
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ProductDetailScreen(
                          productId: id,
                          productName: name,
                          assureur: assureur,
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
                          final p = _productList[_selectedProductIndex!];
                          final id = p is _ProductData ? p.id : (p as dynamic).id as int;
                          widget.onContinue(id, _medicalPhotoPath ?? widget.initialMedicalPhotoPath);
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

class _ProductData {
  const _ProductData(this.id, this.name, this.assureur, this.duree, this.price, this.zonesCount);
  final int id;
  final String name, assureur, duree, price;
  final int zonesCount;
}

class _ProductCard extends StatelessWidget {
  const _ProductCard({
    required this.name,
    required this.assureur,
    this.logoUrl,
    required this.duree,
    required this.price,
    required this.zonesCount,
    required this.isSelected,
    required this.onTap,
    required this.onViewDetails,
  });

  final String name, assureur, duree, price;
  final String? logoUrl;
  final int zonesCount;
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
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Expanded(
                child: Text(
                  name,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1E293B),
                  ),
                  overflow: TextOverflow.ellipsis,
                  maxLines: 2,
                ),
              ),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  price,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: AppColors.primary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
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
              '$zonesCount zones couvertes',
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
            'Photo pour l’e-carte',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1E293B),
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'Vous pouvez l’ajouter ici ou à l’étape « Médical » (obligatoire avant le paiement). Portrait, visage visible — la même image servira à la carte numérique sur le web et dans l’app.',
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
              'J\'accepte les exclusions.',
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
