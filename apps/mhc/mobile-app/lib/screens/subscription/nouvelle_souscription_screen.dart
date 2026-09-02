import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../models/product.dart';
import '../../models/subscription_quote.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';
import 'subscription_stepper.dart';
import 'step_voyage_screen.dart';
import 'step_produit_screen.dart';
import 'step_medical_screen.dart';
import 'step_paiement_screen.dart';
import 'step_attestation_screen.dart';

int? _optInt(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value.toString().trim());
}

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
  double? _primePourPaiement;
  double? _fraisPourPaiement;
  String? _medicalPhotoPath;
  List<ProductModel>? _products;
  VoyageFormData? _voyageData;
  bool _loadingProducts = false;
  /// Devis par produit (POST /subscriptions/quote-prices), aligné sur le paiement.
  Map<int, SubscriptionQuoteLine> _devisParProduit = {};
  List<SurprimeAgeRow> _surprimesAge = [];
  double _fraisSurPrimePct = 15;
  int? _subscriberAge;
  bool _loadingDevis = false;
  int _attestationReloadTick = 0;

  final VoyagesService _voyagesService = VoyagesService();
  final SubscriptionsService _subscriptionsService = SubscriptionsService();
  final ProductsService _productsService = ProductsService();
  final CourtiersService _courtiersService = CourtiersService();
  final VoyageDocumentsService _documentsService = VoyageDocumentsService();
  String _canalDistribution = 'assureur';
  int? _selectedCourtierId;
  List<Map<String, dynamic>> _courtiers = const [];

  Future<List<Map<String, dynamic>>> _loadCourtiersForProducts(
    List<ProductModel> products,
  ) async {
    final assureurIds = products
        .map((p) => p.assureurId)
        .whereType<int>()
        .toSet()
        .toList()
      ..sort();
    if (assureurIds.isEmpty) return const [];

    final byId = <int, Map<String, dynamic>>{};
    for (final assureurId in assureurIds) {
      try {
        final rows = await _courtiersService.getCourtiers(assureurId: assureurId);
        for (final c in rows) {
          final id = _optInt(c['id']);
          if (id != null) byId[id] = c;
        }
      } on DioException catch (e) {
        // Endpoint éventuellement absent/non exposé selon environnement.
        if (e.response?.statusCode != 404) rethrow;
      }
    }

    if (byId.isNotEmpty) {
      final list = byId.values.toList();
      list.sort((a, b) => (a['nom']?.toString() ?? '').compareTo(b['nom']?.toString() ?? ''));
      return list;
    }

    // Fallback: récupérer tout puis filtrer par assureur lié.
    try {
      final all = await _courtiersService.getCourtiers();
      final filtered = all.where((c) {
        final aid = _optInt(c['assureur_id']);
        return aid != null && assureurIds.contains(aid);
      }).toList();
      filtered.sort((a, b) => (a['nom']?.toString() ?? '').compareTo(b['nom']?.toString() ?? ''));
      return filtered;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return const [];
      rethrow;
    }
  }

  void _goToPreviousStep() {
    if (_currentStep > 1) {
      setState(() => _currentStep -= 1);
      return;
    }
    Navigator.of(context).pop();
  }

  void _jumpToPreviousStep() {
    if (_currentStep <= 1) return;
    setState(() => _currentStep -= 1);
  }

  /// Produits filtrés par territoire assureur (résidence vs destination selon zone tarifaire).
  Future<void> _loadProductsForVoyage(VoyageFormData data) async {
    setState(() => _loadingProducts = true);
    try {
      final baseProducts = await _productsService.getProducts(
        limit: 500,
        estActif: true,
        filterByVoyageAssureur: true,
        residenceCountryName: data.residenceCountryName,
        destinationCountryId: data.destinationCountryId,
        destinationCountryName: data.destinationCountryName,
        canalDistribution: 'assureur',
      );
      final list = baseProducts;
      final courtiers = await _loadCourtiersForProducts(baseProducts);
      if (mounted) {
        setState(() {
          _products = list;
          _courtiers = courtiers;
          if (_selectedCourtierId != null &&
              !_courtiers.any((c) => _optInt(c['id']) == _selectedCourtierId)) {
            _selectedCourtierId = null;
          }
          _loadingProducts = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loadingProducts = false;
          _products = [];
        });
        if (e is DioException && e.response?.statusCode == 401) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Session expirée. Veuillez vous reconnecter.'),
              backgroundColor: AppColors.danger,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Impossible de charger les produits : ${e.toString()}'),
              backgroundColor: AppColors.danger,
            ),
          );
        }
      }
    }
  }

  Future<void> _fetchDevisPrices() async {
    final pid = _projetId;
    final products = _products;
    if (pid == null || products == null || products.isEmpty) return;
    if (!mounted) return;
    setState(() => _loadingDevis = true);
    try {
      var age = _subscriberAge;
      if (age == null) {
        try {
          final u = await AuthService.instance.getMe();
          age = _ageFromDateNaissance(u.dateNaissance);
          _subscriberAge = age;
        } catch (_) {}
      }
      final ids = products.map((e) => e.id).toList();
      final result = await _subscriptionsService.quotePrices(
        projetVoyageId: pid,
        produitAssuranceIds: ids,
        destinationCountryId: _voyageData?.destinationCountryId,
        dureeJours: _voyageData?.dureeJours,
        age: age,
      );
      if (mounted) {
        setState(() {
          _devisParProduit = result.byProductId;
          _surprimesAge = result.surprimesAge;
          _fraisSurPrimePct = result.fraisSurPrimePct;
          _loadingDevis = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loadingDevis = false);
    }
  }

  int? _ageFromDateNaissance(String? raw) {
    if (raw == null || raw.trim().isEmpty) return null;
    final d = DateTime.tryParse(raw);
    if (d == null) return null;
    final now = DateTime.now();
    var a = now.year - d.year;
    if (now.month < d.month || (now.month == d.month && now.day < d.day)) {
      a--;
    }
    return a;
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
          'Mineurs accompagnés: ${data.mineurs!
              .map(
                (m) =>
                    '${m.nom} (né(e) le ${fmtDate(m.dateNaissance)}); passeport ${m.numeroPasseport}; validité ${fmtDate(m.validitePasseport)}',
              )
              .join('; ')}',
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
      if (mounted) {
        setState(() {
          _projetId = projet.id;
          _voyageData = data;
        });
      }
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
      await _loadProductsForVoyage(data);
      await _fetchDevisPrices();
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
      var age = _subscriberAge;
      if (age == null) {
        try {
          final u = await AuthService.instance.getMe();
          age = _ageFromDateNaissance(u.dateNaissance);
          _subscriberAge = age;
        } catch (_) {}
      }

      int? autoCourtierId;
      if (_canalDistribution == 'courtier') {
        ProductModel? product;
        for (final p in (_products ?? const <ProductModel>[])) {
          if (p.id == productId) {
            product = p;
            break;
          }
        }
        final aid = product?.assureurId;
        if (aid != null && _selectedCourtierId != null) {
          final selected = _courtiers.where((c) {
            final cid = _optInt(c['id']);
            final courtierAssureurId = _optInt(c['assureur_id']);
            return cid == _selectedCourtierId && courtierAssureurId == aid;
          }).toList();
          if (selected.isNotEmpty) {
            autoCourtierId = _optInt(selected.first['id']);
          }
        }
        if (aid != null) {
          final linked = _courtiers.where((c) => _optInt(c['assureur_id']) == aid).toList();
          if (linked.isNotEmpty && autoCourtierId == null) {
            autoCourtierId = _optInt(linked.first['id']);
          }
        }
        if (autoCourtierId == null) {
          throw Exception('Aucun courtier eligible n\'a ete trouve pour ce produit.');
        }
      }
      final sub = await _subscriptionsService.startSubscription(
        produitAssuranceId: productId,
        projetVoyageId: _projetId,
        dateDebut: _voyageData?.dateDepart,
        destinationCountryId: _voyageData?.destinationCountryId,
        canalDistribution: _canalDistribution,
        courtierId: _canalDistribution == 'courtier' ? autoCourtierId : null,
        dureeJours: _voyageData?.dureeJours,
        age: age,
      );
      if (mounted) {
        setState(() {
          _subscriptionId = sub.id;
          _montant = sub.prixApplique;
          _primePourPaiement = sub.primeAssurance;
          _fraisPourPaiement = sub.fraisServices;
          _medicalPhotoPath = medicalPhotoPath;
          _currentStep = 3;
        });
      }
    } catch (e) {
      if (mounted) {
        _showErrorSnackBar(e);
      }
    }
  }

  void _showErrorSnackBar(Object e) {
    String message;
    if (e is DioException) {
      if (e.response?.statusCode == 401) {
        message = 'Session expirée. Veuillez vous reconnecter.';
      } else {
        final data = e.response?.data;
        String? apiMessage;
        if (data is Map) {
          final detail = data['detail'] ?? data['message'] ?? data['error'];
          if (detail is String && detail.trim().isNotEmpty) {
            apiMessage = detail.trim();
          } else if (detail is List && detail.isNotEmpty) {
            apiMessage = detail.join(', ');
          }
        } else if (data is String && data.trim().isNotEmpty) {
          apiMessage = data.trim();
        }
        message = apiMessage ??
            e.message?.trim() ??
            'Erreur serveur (${e.response?.statusCode ?? 'inconnue'}).';
      }
    } else {
      message = e.toString().replaceFirst('Exception: ', '');
    }
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
    return PopScope(
      canPop: _currentStep == 1,
      onPopInvokedWithResult: (didPop, _) {
        if (didPop) return;
        _goToPreviousStep();
      },
      child: Scaffold(
        resizeToAvoidBottomInset: false,
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: _goToPreviousStep,
          ),
        title: const Text(
          'Nouvelle souscription',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: Color(0xFF1E293B),
            fontSize: 18,
          ),
        ),
        backgroundColor: AppColors.cardBg,
        elevation: 0,
        foregroundColor: const Color(0xFF1E293B),
      ),
        body: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SubscriptionStepper(currentStep: _currentStep),
            if (_currentStep > 1)
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: _jumpToPreviousStep,
                    icon: const Icon(Icons.arrow_back, size: 18),
                    label: const Text('Étape précédente'),
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.primary,
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                  ),
                ),
              ),
            Expanded(
              child: IndexedStack(
                index: _currentStep - 1,
                children: [
                  StepVoyageScreen(onContinue: _onVoyageContinue),
                  StepProduitScreen(
                    products: _products,
                    canalDistribution: _canalDistribution,
                    selectedCourtierId: _selectedCourtierId,
                    courtiers: _courtiers,
                    onCanalChanged: (v) async {
                      setState(() {
                        _canalDistribution = v;
                      });
                      final data = _voyageData;
                      if (data != null) {
                        await _loadProductsForVoyage(data);
                        await _fetchDevisPrices();
                      }
                    },
                    onCourtierChanged: (id) async {
                      setState(() => _selectedCourtierId = id);
                      final data = _voyageData;
                      if (data != null && _canalDistribution == 'courtier') {
                        await _loadProductsForVoyage(data);
                        await _fetchDevisPrices();
                      }
                    },
                    initialMedicalPhotoPath: _medicalPhotoPath,
                    onBackToVoyage: () => setState(() => _currentStep = 1),
                    onContinue: _onProduitContinue,
                    devisParProduit: _devisParProduit,
                    loadingDevis: _loadingDevis,
                    residenceCountryName: _voyageData?.residenceCountryName,
                    destinationCountryName: _voyageData?.destinationCountryName,
                    voyageDureeJours: _voyageData?.dureeJours,
                    subscriberAge: _subscriberAge,
                    surprimesAge: _surprimesAge,
                    fraisSurPrimePct: _fraisSurPrimePct,
                  ),
                  _subscriptionId != null
                      ? StepMedicalScreen(
                          subscriptionId: _subscriptionId!,
                          medicalPhotoPath: _medicalPhotoPath,
                          onContinue: () => setState(() => _currentStep = 4),
                        )
                      : _buildLoadingOrPlaceholder(),
                  _subscriptionId != null
                      ? StepPaiementScreen(
                          subscriptionId: _subscriptionId!,
                          montant: _montant,
                          primeAssurance: _primePourPaiement,
                          fraisServices: _fraisPourPaiement,
                          onContinue: () => setState(() {
                            _attestationReloadTick += 1;
                            _currentStep = 5;
                          }),
                        )
                      : _buildLoadingOrPlaceholder(),
                  _subscriptionId != null
                      ? StepAttestationScreen(
                          key: ValueKey(
                            'attestation-${_subscriptionId!}-$_attestationReloadTick',
                          ),
                          subscriptionId: _subscriptionId!,
                          onDone: () => Navigator.of(context).pop(),
                        )
                      : _buildLoadingOrPlaceholder(),
                ],
              ),
            ),
          ],
        ),
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
