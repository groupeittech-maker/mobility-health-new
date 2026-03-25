import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../models/product.dart';
import '../../services/api_services.dart';
import 'subscription_stepper.dart';
import 'step_voyage_screen.dart';
import 'step_produit_screen.dart';
import 'step_medical_screen.dart';
import 'step_paiement_screen.dart';
import 'step_attestation_screen.dart';

/// Flux "Nouvelle souscription" : 5 étapes (Voyage, Produit, Médical, Paiement, Attestation) – connecté API.
class NouvelleSouscriptionScreen extends StatefulWidget {
  const NouvelleSouscriptionScreen({super.key});

  @override
  State<NouvelleSouscriptionScreen> createState() => _NouvelleSouscriptionScreenState();
}

class _NouvelleSouscriptionScreenState extends State<NouvelleSouscriptionScreen> {
  int _currentStep = 1;
  int? _projetId;
  int? _subscriptionId;
  double _montant = 0;
  String? _medicalPhotoPath;
  List<ProductModel>? _products;
  VoyageFormData? _voyageData;
  bool _loadingProducts = false;

  final VoyagesService _voyagesService = VoyagesService();
  final SubscriptionsService _subscriptionsService = SubscriptionsService();
  final ProductsService _productsService = ProductsService();
  final VoyageDocumentsService _documentsService = VoyageDocumentsService();

  @override
  void initState() {
    super.initState();
    _loadProducts();
  }

  Future<void> _loadProducts() async {
    setState(() => _loadingProducts = true);
    try {
      final list = await _productsService.getProducts();
      if (mounted) setState(() {
        _products = list;
        _loadingProducts = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _loadingProducts = false);
        if (e is DioException && e.response?.statusCode == 401) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Text('Session expirée. Veuillez vous reconnecter.'),
              backgroundColor: AppColors.danger,
            ),
          );
        }
      }
    }
  }

  Future<void> _onVoyageContinue(VoyageFormData data) async {
    try {
      final notesLines = <String>[
        if ((data.residenceCountryName ?? '').trim().isNotEmpty)
          'Pays de résidence: ${data.residenceCountryName!.trim()}',
        'Pays de destination: ${data.destinationCountryName}',
        'Ville de destination: ${data.destinationCityName}',
      ];
      if (data.mineurs != null && data.mineurs!.isNotEmpty) {
        String fmtDate(DateTime d) =>
            '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
        notesLines.add(
          'Mineurs accompagnés: ' +
              data.mineurs!
                  .map(
                    (m) =>
                        '${m.nom} (né(e) le ${fmtDate(m.dateNaissance)}); passeport ${m.numeroPasseport}; validité ${fmtDate(m.validitePasseport)}',
                  )
                  .join('; '),
        );
      }
      final projet = await _voyagesService.createVoyage(
        titre: data.titre,
        destination: data.destination,
        dateDepart: data.dateDepart,
        dateRetour: data.dateRetour,
        nombreParticipants: data.nombreParticipants,
        notes: notesLines.join('\n'),
        destinationCountryId: data.destinationCountryId,
      );
      if (mounted) setState(() {
        _projetId = projet.id;
        _voyageData = data;
      });
      // Envoyer les pièces justificatives (passeport, billet, etc.)
      if (data.documents != null && data.documents!.isNotEmpty) {
        for (final doc in data.documents!) {
          try {
            await _documentsService.uploadDocument(
              projetId: projet.id,
              filePath: doc.path,
              docType: doc.docType,
            );
          } catch (docError) {
            if (mounted) {
              _showErrorSnackBar(docError);
            }
          }
        }
      }
      if (mounted) setState(() => _currentStep = 2);
    } catch (e) {
      if (mounted) {
        _showErrorSnackBar(e);
      }
    }
  }

  Future<void> _onProduitContinue(int productId, String? medicalPhotoPath) async {
    if (_projetId == null) return;
    try {
      final sub = await _subscriptionsService.startSubscription(
        produitAssuranceId: productId,
        projetVoyageId: _projetId,
        dateDebut: _voyageData?.dateDepart,
        destinationCountryId: _voyageData?.destinationCountryId,
        dureeJours: _voyageData?.dureeJours,
      );
      if (mounted) setState(() {
        _subscriptionId = sub.id;
        _montant = sub.prixApplique;
        _medicalPhotoPath = medicalPhotoPath;
        _currentStep = 3;
      });
    } catch (e) {
      if (mounted) {
        _showErrorSnackBar(e);
      }
    }
  }

  void _showErrorSnackBar(Object e) {
    final String message = (e is DioException && e.response?.statusCode == 401)
        ? 'Session expirée. Veuillez vous reconnecter.'
        : e.toString().replaceFirst('Exception: ', '');
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Erreur: $message'),
        backgroundColor: AppColors.danger,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // false : le clavier ne réduit pas la hauteur du body (évite Column stepper + Expanded
    // qui déborde dès que l’espace utile < hauteur du stepper). Le scroll des étapes gère
    // viewInsets via padding (ex. StepVoyageScreen).
    return Scaffold(
      resizeToAvoidBottomInset: false,
      backgroundColor: Colors.white,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text(
          'Nouvelle souscription',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: Color(0xFF1E293B),
            fontSize: 18,
          ),
        ),
        backgroundColor: const Color(0xFFf0fdfa),
        elevation: 0,
        foregroundColor: const Color(0xFF1E293B),
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SubscriptionStepper(currentStep: _currentStep),
          Expanded(
            child: _currentStep == 1
                ? StepVoyageScreen(onContinue: _onVoyageContinue)
                : _currentStep == 2
                    ? StepProduitScreen(
                        products: _products,
                        initialMedicalPhotoPath: _medicalPhotoPath,
                        onContinue: _onProduitContinue,
                      )
                    : _currentStep == 3 && _subscriptionId != null
                        ? StepMedicalScreen(
                            subscriptionId: _subscriptionId!,
                            medicalPhotoPath: _medicalPhotoPath,
                            onContinue: () => setState(() => _currentStep = 4),
                          )
                        : _currentStep == 4 && _subscriptionId != null
                            ? StepPaiementScreen(
                                subscriptionId: _subscriptionId!,
                                montant: _montant,
                                onContinue: () => setState(() => _currentStep = 5),
                              )
                            : _currentStep == 5 && _subscriptionId != null
                                ? StepAttestationScreen(
                                    subscriptionId: _subscriptionId!,
                                    onDone: () => Navigator.of(context).pop(),
                                  )
                                : _buildLoadingOrPlaceholder(),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingOrPlaceholder() {
    if (_currentStep == 2 && _loadingProducts) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.primary),
      );
    }
    final labels = {3: 'Médical', 4: 'Paiement', 5: 'Attestation'};
    return Container(
      color: const Color(0xFFE8F0F4),
      padding: const EdgeInsets.all(20),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Étape $_currentStep : ${labels[_currentStep] ?? ""}',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1E293B),
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            const Text(
              'Chargement…',
              style: TextStyle(color: Color(0xFF64748B)),
            ),
          ],
        ),
      ),
    );
  }
}
