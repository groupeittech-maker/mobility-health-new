import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../core/config/api_config.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
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

/// Flux « Nouvelle souscription » (kit MyMHC) : Voyage → Questionnaire →
/// Assurance → Paiement, puis attestation/e-carte hors stepper. Connecté API.
class NouvelleSouscriptionScreen extends StatefulWidget {
  const NouvelleSouscriptionScreen({super.key, this.resumeSubscriptionId});

  /// Reprise d'un dossier existant depuis l'historique : l'écran saute
  /// directement à l'étape où le dossier s'est arrêté.
  final int? resumeSubscriptionId;

  @override
  State<NouvelleSouscriptionScreen> createState() => _NouvelleSouscriptionScreenState();
}

class _NouvelleSouscriptionScreenState extends State<NouvelleSouscriptionScreen> {
  int _currentStep = 1;
  int? _projetId;
  int? _subscriptionId;
  double _montant = 0;
  double? _primePourPaiement;
  double? _coutPolice;
  double? _fraisPourPaiement;
  double? _taxesTotal;
  List<Map<String, dynamic>>? _taxes;
  /// Photo portrait pour l'e-carte, capturée à l'étape Voyage (kit).
  String? _medicalPhotoPath;
  /// Réponses du questionnaire médical (étape 2), soumises après la création
  /// de la souscription à l'étape Assurance.
  MedicalFormData? _medicalData;
  List<ProductModel>? _products;
  VoyageFormData? _voyageData;
  bool _loadingProducts = false;
  /// Devis par produit (POST /subscriptions/quote-prices), aligné sur le paiement.
  Map<int, SubscriptionQuoteLine> _devisParProduit = {};
  List<SurprimeAgeRow> _surprimesAge = [];
  double _fraisSurPrimePct = 15;
  int? _subscriberAge;
  String? _subscriberFullName;
  /// Produit choisi à l'étape Assurance (récapitulatif paiement).
  int? _selectedProductId;
  bool _loadingDevis = false;
  int _attestationReloadTick = 0;
  /// Après paiement : l'attestation est affichée hors du stepper (kit :
  /// les documents vivent dans « Documents et services », pas dans le flux).
  bool _showAttestation = false;

  final VoyagesService _voyagesService = VoyagesService();
  final SubscriptionsService _subscriptionsService = SubscriptionsService();
  final ProductsService _productsService = ProductsService();
  final CourtiersService _courtiersService = CourtiersService();
  final VoyageDocumentsService _documentsService = VoyageDocumentsService();
  String _canalDistribution = 'assureur';
  int? _selectedCourtierId;
  List<Map<String, dynamic>> _courtiers = const [];
  /// Dossier soumis à la décision (revue/approuvé/refusé) : les étapes
  /// précédentes sont verrouillées — le dossier conserve sa trace.
  bool _dossierLocked = false;

  void _onDossierStateChanged(String? state) {
    if (state != null && !_dossierLocked) {
      setState(() => _dossierLocked = true);
    }
  }

  @override
  void initState() {
    super.initState();
    AuthService.instance.getMe().then((u) {
      if (mounted) setState(() => _subscriberFullName = u.fullName);
    }).catchError((_) {});
    final resumeId = widget.resumeSubscriptionId;
    if (resumeId != null) {
      _resumeSubscription(resumeId);
    }
  }

  /// Reprend un dossier existant : la souscription et le questionnaire ont
  /// déjà été transmis, on repart directement à l'étape Paiement (qui gère
  /// l'état du dossier : à soumettre, en revue, approuvé, refusé).
  Future<void> _resumeSubscription(int subscriptionId) async {
    try {
      final sub = await _subscriptionsService.getSubscription(subscriptionId);
      if (!mounted) return;
      setState(() {
        _subscriptionId = sub.id;
        _projetId = sub.projetVoyageId;
        _montant = sub.prixApplique > 0
            ? sub.prixApplique
            : (sub.primeAssurance ?? 0) +
                (sub.coutPolice ?? 0) +
                (sub.fraisServices ?? 0) +
                (sub.taxesTotal ?? 0);
        _primePourPaiement = sub.primeAssurance;
        _coutPolice = sub.coutPolice;
        _fraisPourPaiement = sub.fraisServices;
        _taxesTotal = sub.taxesTotal;
        _taxes = sub.taxes;
        _currentStep = 4;
        _dossierLocked = sub.statut != 'en_attente';
      });
    } catch (e) {
      if (mounted) _showErrorSnackBar(e);
    }
  }

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
    // Dossier soumis (revue/approuvé/refusé) : on ne peut plus remonter
    // dans le formulaire — retour direct à l'écran précédent (historique).
    if (_dossierLocked || _currentStep <= 1) {
      Navigator.of(context).pop();
      return;
    }
    setState(() => _currentStep -= 1);
  }

  void _jumpToPreviousStep() {
    if (_dossierLocked || _currentStep <= 1) return;
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
      final age = await _voyageurAge();
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

  int? _ageFromDateTime(DateTime? d) {
    if (d == null) return null;
    final now = DateTime.now();
    var a = now.year - d.year;
    if (now.month < d.month || (now.month == d.month && now.day < d.day)) {
      a--;
    }
    return a;
  }

  Future<int?> _voyageurAge() async {
    if (_voyageData?.isChildOnly == true && _voyageData?.mineurs?.isNotEmpty == true) {
      final age = _ageFromDateTime(_voyageData!.mineurs!.first.dateNaissance);
      _subscriberAge = age;
      return age;
    }
    var age = _subscriberAge;
    if (age == null) {
      try {
        final u = await AuthService.instance.getMe();
        age = _ageFromDateNaissance(u.dateNaissance);
        _subscriberAge = age;
      } catch (_) {}
    }
    return age;
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
        if (data.isChildOnly) {
          final child = data.mineurs!.first;
          notesLines.addAll([
            'Pour un tiers: oui',
            '=== INFORMATIONS DU TIERS (BÉNÉFICIAIRE) ===',
            'Nom du tiers: ${child.nom}',
            'Date de naissance du tiers: ${fmtDate(child.dateNaissance)}',
            'Numéro de passeport du tiers: ${child.numeroPasseport}',
            'Date d\'expiration du passeport du tiers: ${fmtDate(child.validitePasseport)}',
            '=== FIN INFORMATIONS DU TIERS ===',
          ]);
        } else {
          notesLines.add(
            'Mineurs accompagnés: ${data.mineurs!
                .map(
                  (m) =>
                      '${m.nom} (né(e) le ${fmtDate(m.dateNaissance)}); passeport ${m.numeroPasseport}; validité ${fmtDate(m.validitePasseport)}',
                )
                .join('; ')}',
          );
        }
      }
      final projet = await _voyagesService.createVoyage(
        titre: data.titre,
        destination: data.destination,
        dateDepart: data.dateDepart,
        dateRetour: data.dateRetour,
        nombreParticipants: data.nombreParticipants,
        notes: notesLines.join('\n'),
        destinationCountryId: data.destinationCountryId,
        mineurs: (!data.isChildOnly && data.mineurs != null)
            ? data.mineurs!
                .map(
                  (m) => {
                    'nom': m.nom,
                    'date_naissance':
                        m.dateNaissance.toIso8601String().substring(0, 10),
                    'numero_passeport': m.numeroPasseport,
                    'validite_passeport':
                        m.validitePasseport.toIso8601String().substring(0, 10),
                  },
                )
                .toList()
            : null,
      );
      if (mounted) {
        setState(() {
          _projetId = projet.id;
          _voyageData = data;
          _medicalPhotoPath = data.ecartePhotoPath;
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

  /// Étape Questionnaire (kit) : on conserve les réponses puis on passe
  /// à l'étape Assurance — la soumission API a lieu après la création
  /// de la souscription (elle exige un `subscriptionId`).
  void _onMedicalContinue(MedicalFormData data) {
    setState(() {
      _medicalData = data;
      _currentStep = 3;
    });
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

  /// Soumet le questionnaire médical + la photo e-carte du voyage.
  Future<void> _submitMedicalAnswers(int subscriptionId) async {
    final data = _medicalData;
    if (data == null) return;
    final reponses = Map<String, dynamic>.from(data.reponses);

    final photoPath = _medicalPhotoPath?.trim();
    if (photoPath != null && photoPath.isNotEmpty) {
      final file = File(photoPath);
      if (await file.exists()) {
        final bytes = await file.readAsBytes();
        if (bytes.isNotEmpty && bytes.length <= 5 * 1024 * 1024) {
          final dataUrl = _dataUrlFromBytes(bytes);
          reponses['photo_medicale'] = dataUrl;
          reponses['photoMedicale'] = dataUrl;
          reponses['photo_identity'] = dataUrl;
        }
      }
    }
    await QuestionnaireService().submitMedical(subscriptionId, reponses);
  }

  String? _productLogoUrl(ProductModel? p) {
    if (p == null) return null;
    final img = p.imageUrl;
    if (img != null && img.trim().isNotEmpty) {
      if (img.startsWith('http')) return img;
      return '${ApiConfig.baseUrl}$img';
    }
    final assureurId = p.assureurId;
    if (assureurId != null) {
      return '${ApiConfig.baseUrl}/assureurs/$assureurId/logo';
    }
    return null;
  }

  String? _formatVoyageDates(VoyageFormData? d) {
    if (d == null) return null;
    String fmt(DateTime dt) =>
        '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}';
    final depart = fmt(d.dateDepart);
    final retour = d.dateRetour;
    if (retour == null) return 'Dès le $depart';
    return '$depart → ${fmt(retour)}';
  }

  Future<void> _onProduitContinue(int productId) async {
    if (_projetId == null) return;
    try {
      final age = await _voyageurAge();

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
      // La souscription existe : on transmet maintenant le questionnaire
      // médical (avec la photo e-carte du voyage) avant l'étape Paiement.
      await _submitMedicalAnswers(sub.id);
      if (mounted) {
        setState(() {
          _subscriptionId = sub.id;
          _selectedProductId = productId;
          _montant = sub.prixApplique;
          _primePourPaiement = sub.primeAssurance;
          _coutPolice = sub.coutPolice;
          _fraisPourPaiement = sub.fraisServices;
          _taxesTotal = sub.taxesTotal;
          _taxes = sub.taxes;
          _currentStep = 4;
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
      canPop: _currentStep == 1 || _dossierLocked || _showAttestation,
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
            if (!_showAttestation)
              SubscriptionStepper(currentStep: _currentStep),
            if (_currentStep > 1 && !_dossierLocked)
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
              child: _showAttestation
                  ? (_subscriptionId != null
                      ? StepAttestationScreen(
                          key: ValueKey(
                            'attestation-${_subscriptionId!}-$_attestationReloadTick',
                          ),
                          subscriptionId: _subscriptionId!,
                          onDone: () => Navigator.of(context).pop(),
                        )
                      : _buildLoadingOrPlaceholder())
                  : IndexedStack(
                      index: _currentStep - 1,
                      children: [
                        StepVoyageScreen(onContinue: _onVoyageContinue),
                        StepMedicalScreen(onContinue: _onMedicalContinue),
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
                            if (data != null &&
                                _canalDistribution == 'courtier') {
                              await _loadProductsForVoyage(data);
                              await _fetchDevisPrices();
                            }
                          },
                          onBackToVoyage: () =>
                              setState(() => _currentStep = 1),
                          onContinue: _onProduitContinue,
                          devisParProduit: _devisParProduit,
                          loadingDevis: _loadingDevis,
                          residenceCountryName:
                              _voyageData?.residenceCountryName,
                          destinationCountryName:
                              _voyageData?.destinationCountryName,
                          voyageDureeJours: _voyageData?.dureeJours,
                          subscriberAge: _subscriberAge,
                          surprimesAge: _surprimesAge,
                          fraisSurPrimePct: _fraisSurPrimePct,
                        ),
                        _subscriptionId != null
                            ? Builder(builder: (context) {
                                ProductModel? p;
                                for (final e in _products ?? const []) {
                                  if (e.id == _selectedProductId) p = e;
                                }
                                final d = _voyageData;
                                return StepPaiementScreen(
                                  subscriptionId: _subscriptionId!,
                                  montant: _montant,
                                  primeAssurance: _primePourPaiement,
                                  coutPolice: _coutPolice,
                                  fraisServices: _fraisPourPaiement,
                                  taxesTotal: _taxesTotal,
                                  taxes: _taxes,
                                  age: _subscriberAge,
                                  recapAssureur: p?.assureur,
                                  recapProduit: p?.nom,
                                  recapLogoUrl: _productLogoUrl(p),
                                  recapDestination: d == null
                                      ? null
                                      : '${d.destinationCityName}, ${d.destinationCountryName}',
                                  recapDates: _formatVoyageDates(d),
                                  recapAssure: _subscriberFullName,
                                  onDossierStateChanged:
                                      _onDossierStateChanged,
                                  onContinue: () => setState(() {
                                    _attestationReloadTick += 1;
                                    _showAttestation = true;
                                  }),
                                );
                              })
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
    if (_currentStep == 3 && _loadingProducts) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.primary),
      );
    }
    final labels = {2: 'Questionnaire', 3: 'Assurance', 4: 'Paiement'};
    return Container(
      color: kMhContentBackground,
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
