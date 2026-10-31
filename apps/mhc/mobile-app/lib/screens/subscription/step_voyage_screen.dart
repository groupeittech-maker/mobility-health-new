import 'dart:convert' show base64Decode;
import 'dart:io' show File;
import 'dart:math' show max, min;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../core/widgets/mh_text_highlight.dart';
import '../../models/destination.dart';
import '../../services/account_service.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';

/// Durée maximale d'un voyage couvert (workflow MyMHC V3).
const int kMaxTripDays = 92;

/// Un mineur accompagnant (identité, passeport, photo du passeport en pièce jointe).
class MineurEntry {
  const MineurEntry({
    required this.nom,
    this.prenom,
    this.nationalite,
    this.lienParente,
    this.enfantId,
    required this.dateNaissance,
    required this.numeroPasseport,
    required this.validitePasseport,
    required this.photoPasseportPath,
    this.photoPortraitPath,
  });
  final String nom;
  final String? prenom;
  final String? nationalite;
  final String? lienParente;
  final int? enfantId;
  final DateTime dateNaissance;
  final String numeroPasseport;
  final DateTime validitePasseport;
  final String photoPasseportPath;
  final String? photoPortraitPath;
}

/// Pièce justificative (chemin local + type pour l'API).
class VoyageDocEntry {
  const VoyageDocEntry({required this.path, required this.docType, this.label});
  final String path;
  final String docType; // passport, travel_booking, other, etc.
  final String? label;  // Libellé affiché (ex. "Passeport", "Billet")
}

/// Données voyage pour création du projet (API).
class VoyageFormData {
  const VoyageFormData({
    required this.titre,
    required this.destination,
    required this.destinationCountryId,
    required this.destinationCountryName,
    required this.destinationCityName,
    required this.dateDepart,
    this.residenceCountryName,
    this.dateRetour,
    this.nombreParticipants = 1,
    this.dureeJours,
    this.mineurs,
    this.documents,
    this.isChildOnly = false,
    this.ecartePhotoPath,
  });
  final String titre;
  final String destination;
  final int destinationCountryId;
  final String destinationCountryName;
  final String destinationCityName;
  final DateTime dateDepart;
  final String? residenceCountryName;
  final DateTime? dateRetour;
  final int nombreParticipants;
  final int? dureeJours;
  final List<MineurEntry>? mineurs;
  final List<VoyageDocEntry>? documents;
  final bool isChildOnly;
  /// Photo portrait pour l'e-carte (kit : distincte du document de voyage).
  final String? ecartePhotoPath;
}

/// Étape 1 : Informations sur le voyage (destination, dates, transport, mineurs).
/// Libellé de la pièce d'identité du souscripteur (obligatoire).
const String kIdentityDocLabel = 'Pièce d’identité';

/// Bouton « + Ajouter » compact : aligné sur la marge droite de la carte,
/// à la même distance du bord que le titre de section à gauche.
final ButtonStyle _addButtonStyle = TextButton.styleFrom(
  padding: EdgeInsets.zero,
  minimumSize: const Size(0, 36),
  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
  foregroundColor: AppColors.secondary,
);

class StepVoyageScreen extends StatefulWidget {
  const StepVoyageScreen({
    super.key,
    required this.onContinue,
  });

  final void Function(VoyageFormData data) onContinue;

  @override
  State<StepVoyageScreen> createState() => _StepVoyageScreenState();
}

class _StepVoyageScreenState extends State<StepVoyageScreen> {
  final _formKey = GlobalKey<FormState>();
  final DestinationsService _destinationsService = DestinationsService();

  String? _pays, _ville, _transport;
  int? _paysId;
  DateTime? _dateDepart, _dateRetour;
  bool _avecMineurs = false;
  bool _voyagePourEnfant = false;
  final List<MineurEntry> _enfantsVoyageurs = [];
  final List<MineurEntry> _mineurs = [];
  final List<VoyageDocEntry> _documents = [];
  /// Photo portrait dédiée à l'e-carte (kit « Pièces justificatives »).
  String? _ecartePhotoPath;
  List<DestinationCountryModel> _destinationCountries = const [];
  List<String> _countryOptionsFiltered = const [];
  List<DestinationCityModel> _destinationCities = const [];
  List<ReferenceCountryModel> _referenceCountries = const [];
  final Map<int, List<DestinationCityModel>> _citiesByCountryId = {};
  bool _loadingDestinations = true;
  bool _loadingCities = false;
  String? _destinationsError;
  String? _citiesError;
  String? _residenceCountryRaw;
  String? _residenceCountryCode;
  bool _loadingResidenceCountry = true;
  /// Erreurs affichées sous les champs recherche pays/ville (sans FormField async).
  String? _paysFieldError;
  String? _villeFieldError;

  int get _dureeJours {
    if (_dateDepart == null || _dateRetour == null) return 0;
    return _dateRetour!.difference(_dateDepart!).inDays;
  }

  void _rebuildCountryOptions() {
    _countryOptionsFiltered = _destinationCountries
        .where((country) => !_isResidenceDestinationConflict(country))
        .map((country) => country.nom)
        .toList();
  }

  List<String> get _cityOptions {
    return _destinationCities.map((city) => city.nom).toList();
  }

  @override
  void initState() {
    super.initState();
    final cached = DestinationsService.peekDestinationCountriesCache();
    if (cached != null && cached.isNotEmpty) {
      _destinationCountries = cached;
      _loadingDestinations = false;
      _rebuildCountryOptions();
    }
    _loadDestinations();
    _loadReferenceCountries();
    _loadResidenceCountry();
  }

  Future<void> _loadResidenceCountry() async {
    try {
      final user = await AuthService.instance.getMe();
      if (!mounted) return;
      setState(() {
        _residenceCountryRaw = user.paysResidence?.trim();
        _synchronizeResidenceCountry();
        _loadingResidenceCountry = false;
      });
    } catch (_) {
      // Le backend garde de toute façon la validation finale.
      if (!mounted) return;
      setState(() {
        _loadingResidenceCountry = false;
      });
    }
  }

  Future<void> _loadReferenceCountries() async {
    try {
      final countries = await _destinationsService.getReferenceCountries();
      if (!mounted) return;
      setState(() {
        _referenceCountries = countries;
        _synchronizeResidenceCountry();
      });
    } catch (_) {
      // On garde un fallback avec les destinations déjà chargées.
    }
  }

  bool _isSameCountry(String? first, String? second) {
    String normalize(String? value) => (value ?? '')
        .toLowerCase()
        .trim()
        .replaceAll(RegExp(r'\s+'), '')
        .replaceAll('é', 'e')
        .replaceAll('è', 'e')
        .replaceAll('ê', 'e')
        .replaceAll('ë', 'e')
        .replaceAll('à', 'a')
        .replaceAll('â', 'a')
        .replaceAll('ä', 'a')
        .replaceAll('î', 'i')
        .replaceAll('ï', 'i')
        .replaceAll('ô', 'o')
        .replaceAll('ö', 'o')
        .replaceAll('ù', 'u')
        .replaceAll('û', 'u')
        .replaceAll('ü', 'u')
        .replaceAll('ç', 'c');
    final normalizedFirst = normalize(first);
    final normalizedSecond = normalize(second);
    return normalizedFirst.isNotEmpty && normalizedFirst == normalizedSecond;
  }

  bool _isSameCountryCode(String? first, String? second) {
    final normalizedFirst = (first ?? '').trim().toUpperCase();
    final normalizedSecond = (second ?? '').trim().toUpperCase();
    return normalizedFirst.isNotEmpty && normalizedFirst == normalizedSecond;
  }

  ReferenceCountryModel? _resolveReferenceCountry(String? value) {
    final rawValue = (value ?? '').trim();
    if (rawValue.isEmpty) return null;

    for (final country in _referenceCountries) {
      if (_isSameCountryCode(country.code, rawValue) ||
          _isSameCountry(country.nom, rawValue)) {
        return country;
      }
    }

    for (final country in _destinationCountries) {
      if (_isSameCountryCode(country.code, rawValue) ||
          _isSameCountry(country.nom, rawValue)) {
        return ReferenceCountryModel(code: country.code, nom: country.nom);
      }
    }

    return null;
  }

  DestinationCountryModel? _findCountryByName(String? value) {
    if (value == null || value.isEmpty) return null;
    return _destinationCountries.cast<DestinationCountryModel?>().firstWhere(
      (item) => item?.nom == value,
      orElse: () => null,
    );
  }

  void _synchronizeResidenceCountry() {
    final resolvedCountry = _resolveReferenceCountry(_residenceCountryRaw);
    _residenceCountryCode = resolvedCountry?.code;
    final selectedCountry = _findCountryByName(_pays);
    if (_isResidenceDestinationConflict(selectedCountry)) {
      _pays = null;
      _paysId = null;
      _ville = null;
      _destinationCities = const [];
    }
    _rebuildCountryOptions();
  }

  bool _isResidenceDestinationConflict(DestinationCountryModel? country) {
    if (country == null) return false;
    return _isSameCountryCode(country.code, _residenceCountryCode) ||
        _isSameCountry(country.nom, _residenceCountryRaw);
  }

  bool get _hasResidenceCountry => (_residenceCountryRaw ?? '').trim().isNotEmpty;

  String? get _residenceCountryLabel {
    return _resolveReferenceCountry(_residenceCountryRaw)?.nom ?? _residenceCountryRaw;
  }

  bool get _isDestinationSameAsResidence {
    final selectedCountry = _findCountryByName(_pays);
    return _isResidenceDestinationConflict(selectedCountry);
  }

  Future<void> _loadDestinations() async {
    final blocking = _destinationCountries.isEmpty;
    if (blocking) {
      setState(() {
        _loadingDestinations = true;
        _destinationsError = null;
      });
    } else {
      setState(() => _destinationsError = null);
    }
    try {
      final countries = await _destinationsService.getDestinationCountries(
        includeCities: false,
      );
      if (!mounted) return;
      setState(() {
        _destinationCountries = countries;
        _synchronizeResidenceCountry();
        _loadingDestinations = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingDestinations = false;
        if (_destinationCountries.isEmpty) {
          _destinationsError = e.toString().replaceFirst('Exception: ', '');
        }
      });
    }
  }

  Future<void> _loadCitiesForCountry(int countryId) async {
    final cachedCities = _citiesByCountryId[countryId];
    if (cachedCities != null) {
      setState(() {
        _destinationCities = cachedCities;
        _loadingCities = false;
        _citiesError = null;
      });
      return;
    }

    setState(() {
      _loadingCities = true;
      _citiesError = null;
      _destinationCities = const [];
    });

    try {
      final cities = await _destinationsService.getDestinationCities(countryId);
      if (!mounted || _paysId != countryId) return;
      setState(() {
        _citiesByCountryId[countryId] = cities;
        _destinationCities = cities;
        _loadingCities = false;
      });
    } catch (e) {
      if (!mounted || _paysId != countryId) return;
      setState(() {
        _loadingCities = false;
        _citiesError = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  void _onDestinationCountryChanged(String? value) {
    if (!_hasResidenceCountry) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Veuillez d\'abord renseigner votre pays de résidence dans votre profil avant de souscrire.',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }

    final selectedCountry = _findCountryByName(value);
    if (_isResidenceDestinationConflict(selectedCountry)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Le pays de destination doit être différent de votre pays de résidence.',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }

    setState(() {
      _paysFieldError = null;
      _pays = value;
      _paysId = selectedCountry?.id;
      _ville = null;
      _villeFieldError = null;
      _citiesError = null;
      _destinationCities = const [];
      _loadingCities = selectedCountry != null;
    });

    if (selectedCountry?.id != null) {
      _loadCitiesForCountry(selectedCountry!.id);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);
    // Inclure le clavier : sinon Column du formulaire déborde quand un champ a le focus.
    final bottomPadding = mq.padding.bottom + mq.viewInsets.bottom + 24;
    return Container(
      color: kMhContentBackground,
      child: SingleChildScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: EdgeInsets.fromLTRB(20, 20, 20, bottomPadding),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const MHSectionTitle(title: 'Informations sur le voyage'),
              const SizedBox(height: 16),
              MHSurfaceCard(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
              if (_loadingDestinations)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Center(
                    child: CircularProgressIndicator(color: AppColors.primary),
                  ),
                )
              else if (_destinationsError != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.danger.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: AppColors.danger.withValues(alpha: 0.2),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Impossible de charger les destinations.',
                        style: theme.textTheme.titleSmall?.copyWith(
                          color: AppColors.danger,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _destinationsError!,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: const Color(0xFF64748B),
                        ),
                      ),
                      const SizedBox(height: 8),
                      FilledButton(
                        onPressed: _loadDestinations,
                        child: const Text('Réessayer'),
                      ),
                    ],
                  ),
                )
              else ...[
                _dropdown(
                  'Pays de destination *',
                  _pays,
                  (v) {
                    _onDestinationCountryChanged(v);
                  },
                  _countryOptionsFiltered,
                  enabled: _hasResidenceCountry,
                  emptyLabel: _loadingResidenceCountry
                      ? 'Chargement...'
                      : 'Renseignez d\'abord votre pays de résidence',
                  selectionError: _paysFieldError,
                ),
                if (_loadingResidenceCountry) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Chargement du pays de residence...',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: const Color(0xFF64748B),
                    ),
                  ),
                ] else if ((_residenceCountryLabel ?? '').isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Pays de residence: $_residenceCountryLabel',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: const Color(0xFF64748B),
                    ),
                  ),
                ] else if (_loadingResidenceCountry == false &&
                    _residenceCountryRaw == null) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Veuillez renseigner votre pays de residence dans votre profil avant de souscrire.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: AppColors.danger,
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                _dropdown(
                  'Ville de destination *',
                  _ville,
                  (v) => setState(() {
                    _ville = v;
                    _villeFieldError = null;
                  }),
                  _cityOptions,
                  enabled: _paysId != null && !_loadingCities && _cityOptions.isNotEmpty,
                  emptyLabel: _paysId == null
                      ? (!_hasResidenceCountry
                          ? 'Renseignez d\'abord votre pays de residence'
                          : 'Choisir d\'abord un pays')
                      : _loadingCities
                          ? 'Chargement des villes...'
                          : (_citiesError != null
                              ? 'Impossible de charger les villes'
                              : 'Aucune ville disponible'),
                  selectionError: _villeFieldError,
                ),
                if (_citiesError != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    _citiesError!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: AppColors.danger,
                    ),
                  ),
                ],
              ],
              const SizedBox(height: 12),
              _dropdown('Moyen de transport *', _transport, (v) => setState(() => _transport = v),
                  ['Avion', 'Train', 'Voiture', 'Bateau']),
              const SizedBox(height: 12),
              _dateRangeField(),
              const SizedBox(height: 12),
              InputDecorator(
                decoration: MHSurfaceCard.input(labelText: 'Durée du séjour'),
                child: Text(
                  _dureeJours > 0 ? '$_dureeJours jours' : 'Calcul automatique',
                  style: TextStyle(
                    color: _dureeJours > 0 ? const Color(0xFF1E293B) : const Color(0xFF64748B),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Qui est le voyageur assuré ? *',
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppColors.secondary,
                ),
              ),
              RadioGroup<String>(
                groupValue: _voyagePourEnfant
                    ? 'child_only'
                    : (_avecMineurs ? 'with_children' : 'adult'),
                onChanged: (v) {
                  if (v == null) return;
                  setState(() {
                    _voyagePourEnfant = v == 'child_only';
                    _avecMineurs = v == 'with_children';
                    // Changer de « voyageur assuré » retire aussi les photos
                    // de passeport des enfants qui ne voyagent plus.
                    if (!_voyagePourEnfant && _enfantsVoyageurs.isNotEmpty) {
                      final paths = <String>{};
                      for (final e in _enfantsVoyageurs) {
                        paths.add(e.photoPasseportPath);
                        final pp = e.photoPortraitPath;
                        if (pp != null) paths.add(pp);
                      }
                      _documents.removeWhere((d) => paths.contains(d.path));
                      _enfantsVoyageurs.clear();
                    }
                    if (!_avecMineurs && _mineurs.isNotEmpty) {
                      final paths =
                          _mineurs.map((m) => m.photoPasseportPath).toSet();
                      _documents.removeWhere((d) => paths.contains(d.path));
                      _mineurs.clear();
                    }
                  });
                },
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Radio<String>(
                          value: 'adult',
                          activeColor: AppColors.primary,
                        ),
                        Text('Moi (adulte)'),
                      ],
                    ),
                    Row(
                      children: [
                        Radio<String>(
                          value: 'with_children',
                          activeColor: AppColors.primary,
                        ),
                        Text('Moi + enfants mineurs'),
                      ],
                    ),
                    Row(
                      children: [
                        Radio<String>(
                          value: 'child_only',
                          activeColor: AppColors.primary,
                        ),
                        Text('Enfants mineurs uniquement'),
                      ],
                    ),
                  ],
                ),
              ),
              if (_voyagePourEnfant) ...[
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        'Enfants voyageurs',
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: AppColors.secondary,
                        ),
                      ),
                    ),
                    TextButton.icon(
                      style: _addButtonStyle,
                      onPressed: _ajouterEnfantVoyageur,
                      icon: const Icon(Icons.add, size: 20),
                      label: const Text('Ajouter un enfant'),
                    ),
                  ],
                ),
                if (_enfantsVoyageurs.isEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text(
                      'Aucun enfant voyageur ajouté. Le parent reste abonné, les enfants ont leur propre numéro de police.',
                      style: theme.textTheme.bodySmall?.copyWith(color: const Color(0xFF64748B)),
                    ),
                  )
                else
                  ..._enfantsVoyageurs.asMap().entries.map((entry) {
                    final i = entry.key;
                    final e = entry.value;
                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceCard,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(e.nom, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                                Text(
                                  'Né(e) le ${e.dateNaissance.day.toString().padLeft(2, '0')}/${e.dateNaissance.month.toString().padLeft(2, '0')}/${e.dateNaissance.year} · Passeport ${e.numeroPasseport} · Valide jusqu\'au ${e.validitePasseport.day.toString().padLeft(2, '0')}/${e.validitePasseport.month.toString().padLeft(2, '0')}/${e.validitePasseport.year}',
                                  style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                ),
                              ],
                            ),
                          ),
                          IconButton(
                            onPressed: () => _modifierEnfantVoyageur(i),
                            icon: const Icon(Icons.edit_outlined, color: AppColors.secondary, size: 22),
                            tooltip: 'Modifier',
                          ),
                          IconButton(
                            onPressed: () => setState(() {
                              _documents.removeWhere((d) =>
                                  d.path == e.photoPasseportPath ||
                                  d.path == e.photoPortraitPath);
                              _enfantsVoyageurs.removeAt(i);
                            }),
                            icon: const Icon(Icons.delete_outline, color: AppColors.danger, size: 22),
                            tooltip: 'Supprimer',
                          ),
                        ],
                      ),
                    );
                  }),
                const SizedBox(height: 8),
              ],
              if (_avecMineurs) ...[
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        'Enfants accompagnés',
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: AppColors.secondary,
                        ),
                      ),
                    ),
                    TextButton.icon(
                      style: _addButtonStyle,
                      onPressed: _ajouterMineur,
                      icon: const Icon(Icons.add, size: 20),
                      label: const Text('Ajouter un enfant'),
                    ),
                  ],
                ),
                if (_mineurs.isEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text(
                      'Aucun enfant ajouté. Utilisez « Ajouter un enfant » pour saisir l’identité, le passeport et la photo du passeport.',
                      style: theme.textTheme.bodySmall?.copyWith(color: const Color(0xFF64748B)),
                    ),
                  )
                else
                  ..._mineurs.map((m) {
                    return Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceCard,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(m.nom, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                                Text(
                                  'Né(e) le ${m.dateNaissance.day.toString().padLeft(2, '0')}/${m.dateNaissance.month.toString().padLeft(2, '0')}/${m.dateNaissance.year} · Passeport ${m.numeroPasseport} · Valide jusqu\'au ${m.validitePasseport.day.toString().padLeft(2, '0')}/${m.validitePasseport.month.toString().padLeft(2, '0')}/${m.validitePasseport.year}',
                                  style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                ),
                              ],
                            ),
                          ),
                          IconButton(
                            onPressed: () => _modifierMineur(m),
                            icon: const Icon(Icons.edit_outlined, color: AppColors.secondary, size: 22),
                            tooltip: 'Modifier',
                          ),
                          IconButton(
                            onPressed: () => setState(() {
                              _documents.removeWhere((d) =>
                                  d.path == m.photoPasseportPath ||
                                  d.path == m.photoPortraitPath);
                              _mineurs.remove(m);
                            }),
                            icon: const Icon(Icons.delete_outline, color: AppColors.danger, size: 22),
                            tooltip: 'Supprimer',
                          ),
                        ],
                      ),
                    );
                  }),
                const SizedBox(height: 8),
              ],
              const SizedBox(height: 20),
              Text(
                'Pièces justificatives',
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppColors.secondary,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Prenez une photo ou joignez vos documents (pièce d’identité obligatoire, billet, etc.)',
                style: theme.textTheme.bodySmall?.copyWith(color: const Color(0xFF64748B)),
              ),
              const SizedBox(height: 12),
              _buildEcartePhotoField(theme),
              const SizedBox(height: 12),
              _buildDocButtons(theme),
              if (_documents.isNotEmpty) ...[
                const SizedBox(height: 12),
                ..._documents.asMap().entries.map((e) {
                  final doc = e.value;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceCard,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Row(
                      children: [
                        Icon(_docIcon(doc.docType), color: AppColors.primary, size: 24),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                doc.label ?? _docTypeLabel(doc.docType),
                                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
                              ),
                              Text(
                                doc.path.split(RegExp(r'[/\\]')).last,
                                style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          onPressed: () => setState(() => _documents.remove(doc)),
                          icon: const Icon(Icons.delete_outline, color: AppColors.danger, size: 22),
                          tooltip: 'Supprimer',
                        ),
                      ],
                    ),
                  );
                }),
              ],
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton(
                  onPressed: () {
                    if (!_formKey.currentState!.validate()) return;
                    if (!_hasResidenceCountry) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            'Veuillez d\'abord renseigner votre pays de résidence dans votre profil avant de souscrire.',
                          ),
                          backgroundColor: AppColors.danger,
                        ),
                      );
                      return;
                    }
                    if (_pays == null || _paysId == null) {
                      setState(() {
                        _paysFieldError = 'Requis';
                        _villeFieldError = null;
                      });
                      return;
                    }
                    if (_ville == null || _ville!.isEmpty) {
                      setState(() => _villeFieldError = 'Requis');
                      return;
                    }
                    if (_isDestinationSameAsResidence) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            'Le pays de destination doit être différent de votre pays de résidence.',
                          ),
                          backgroundColor: AppColors.danger,
                        ),
                      );
                      return;
                    }
                    if (_voyagePourEnfant && _enfantsVoyageurs.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            'Veuillez ajouter au moins un enfant voyageur.',
                          ),
                          backgroundColor: AppColors.danger,
                        ),
                      );
                      return;
                    }
                    if (_avecMineurs && _mineurs.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            'Veuillez ajouter les informations du ou des enfants mineurs accompagnants.',
                          ),
                          backgroundColor: AppColors.danger,
                        ),
                      );
                      return;
                    }
                    // La validité du passeport doit couvrir toute la période
                    // du voyage (jusqu'à la date de retour).
                    final today = DateUtils.dateOnly(DateTime.now());
                    final finVoyage = _dateRetour != null
                        ? DateUtils.dateOnly(_dateRetour!)
                        : today;
                    final passeports = <String, DateTime>{
                      for (final m in _mineurs) m.nom: m.validitePasseport,
                      for (final m in _enfantsVoyageurs) m.nom: m.validitePasseport,
                    };
                    final expiredEntry = passeports.entries.where(
                      (e) => DateUtils.dateOnly(e.value).isBefore(finVoyage),
                    );
                    if (expiredEntry.isNotEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            'Le passeport de ${expiredEntry.first.key} expire avant la fin du voyage. '
                            'Corrigez les informations avant de continuer.',
                          ),
                          backgroundColor: AppColors.danger,
                        ),
                      );
                      return;
                    }
                    // Un enfant accompagné doit être mineur pendant toute la
                    // période de couverture.
                    final majeur = [..._mineurs, ..._enfantsVoyageurs].where((m) {
                      var age = finVoyage.year - m.dateNaissance.year;
                      if (finVoyage.month < m.dateNaissance.month ||
                          (finVoyage.month == m.dateNaissance.month &&
                              finVoyage.day < m.dateNaissance.day)) {
                        age--;
                      }
                      return age >= 18;
                    });
                    if (majeur.isNotEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            '${majeur.first.nom} sera majeur(e) pendant la période de couverture : '
                            'un enfant accompagné doit rester mineur durant tout le voyage.',
                          ),
                          backgroundColor: AppColors.danger,
                        ),
                      );
                      return;
                    }
                    // La pièce d'identité du parent reste obligatoire même s'il
                    // ne voyage pas : c'est lui qui souscrit pour les enfants.
                    if (!_documents.any((d) => d.label == kIdentityDocLabel)) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            'Ajoutez votre pièce d\'identité (obligatoire).',
                          ),
                          backgroundColor: AppColors.danger,
                        ),
                      );
                      return;
                    }
                    if (!_voyagePourEnfant &&
                        (_ecartePhotoPath == null || _ecartePhotoPath!.isEmpty)) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            'Ajoutez une photo portrait pour l\'e-carte (caméra ou galerie).',
                          ),
                          backgroundColor: AppColors.danger,
                        ),
                      );
                      return;
                    }
                    final titre = 'Voyage vers $_ville, $_pays';
                    if (titre.isEmpty) return;
                    final List<MineurEntry>? mineurs = _voyagePourEnfant
                        ? (_enfantsVoyageurs.isNotEmpty ? List<MineurEntry>.from(_enfantsVoyageurs) : null)
                        : (_avecMineurs && _mineurs.isNotEmpty ? List<MineurEntry>.from(_mineurs) : null);
                    widget.onContinue(VoyageFormData(
                      titre: titre,
                      destination: _ville ?? '',
                      destinationCountryId: _paysId!,
                      destinationCountryName: _pays ?? '',
                      destinationCityName: _ville ?? '',
                      residenceCountryName: _residenceCountryLabel ?? _residenceCountryRaw,
                      dateDepart: _dateDepart ?? DateTime.now(),
                      dateRetour: _dateRetour,
                      nombreParticipants: 1,
                      dureeJours: _dureeJours > 0 ? _dureeJours : null,
                      mineurs: mineurs,
                      documents: _documents.isNotEmpty ? List.from(_documents) : null,
                      isChildOnly: _voyagePourEnfant,
                      ecartePhotoPath: _voyagePourEnfant
                          ? (_ecartePhotoPath ??
                              (_enfantsVoyageurs.isNotEmpty
                                  ? (_enfantsVoyageurs.first.photoPortraitPath ??
                                      _enfantsVoyageurs.first.photoPasseportPath)
                                  : null))
                          : _ecartePhotoPath,
                    ));
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.secondary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text('Continuer vers le questionnaire'),
                ),
              ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Champ « Photo pour l'e-carte » (kit) : photo portrait distincte du
  /// document de voyage — caméra ou galerie.
  Widget _buildEcartePhotoField(ThemeData theme) {
    final hasPhoto = _ecartePhotoPath != null && _ecartePhotoPath!.isNotEmpty;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surfaceCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: hasPhoto
              ? const Color(0xFFE2E8F0)
              : AppColors.brandTeal.withValues(alpha: 0.45),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.account_circle_outlined,
                  color: AppColors.primary, size: 22),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Photo pour l’e-carte *',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppColors.secondary,
                  ),
                ),
              ),
            ],
          ),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: _pickEcartePhoto,
              icon: const Icon(Icons.add_a_photo_outlined, size: 18),
              label: Text(hasPhoto ? 'Changer' : 'Prendre une photo'),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            hasPhoto
                ? _ecartePhotoPath!.split(RegExp(r'[/\\]')).last
                : 'Photo portrait (visage visible) — distincte du document de voyage.',
            style: theme.textTheme.bodySmall?.copyWith(
              color: const Color(0xFF64748B),
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Future<void> _pickEcartePhoto() async {
    final source = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt, color: AppColors.primary),
              title: const Text('Prendre une photo'),
              onTap: () => Navigator.of(ctx).pop('camera'),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library, color: AppColors.primary),
              title: const Text('Choisir une photo'),
              onTap: () => Navigator.of(ctx).pop('gallery'),
            ),
          ],
        ),
      ),
    );
    if (source == null || !mounted) return;
    final picker = ImagePicker();
    final xfile = await picker.pickImage(
      source: source == 'camera' ? ImageSource.camera : ImageSource.gallery,
      imageQuality: 85,
    );
    if (xfile != null && mounted) {
      setState(() => _ecartePhotoPath = xfile.path);
    }
  }

  Widget _buildDocButtons(ThemeData theme) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        _docActionChip(
          icon: Icons.badge_outlined,
          label: kIdentityDocLabel,
          docType: 'passport',
          theme: theme,
        ),
        _docActionChip(
          icon: Icons.confirmation_number_outlined,
          label: 'Billet / réservation',
          docType: 'travel_booking',
          theme: theme,
        ),
        _docActionChip(
          icon: Icons.description_outlined,
          label: 'Autre document',
          docType: 'other',
          theme: theme,
        ),
      ],
    );
  }

  Widget _docActionChip({
    required IconData icon,
    required String label,
    required String docType,
    required ThemeData theme,
  }) {
    return Material(
      color: AppColors.surfaceCard,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: () => _showDocSourceSheet(docType, label),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(color: const Color(0xFFE2E8F0)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 20, color: AppColors.primary),
              const SizedBox(width: 8),
              Text(label, style: theme.textTheme.labelLarge?.copyWith(
                fontWeight: FontWeight.bold,
                color: AppColors.secondary,
              )),
              const SizedBox(width: 4),
              const Icon(Icons.add_circle_outline, size: 18, color: AppColors.primary),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _showDocSourceSheet(String docType, String label) async {
    final source = await showModalBottomSheet<String>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt, color: AppColors.primary),
              title: const Text('Prendre une photo'),
              onTap: () => Navigator.of(ctx).pop('camera'),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library, color: AppColors.primary),
              title: const Text('Choisir une photo'),
              onTap: () => Navigator.of(ctx).pop('gallery'),
            ),
            ListTile(
              leading: const Icon(Icons.attach_file, color: AppColors.primary),
              title: const Text('Joindre un fichier (PDF, image)'),
              onTap: () => Navigator.of(ctx).pop('file'),
            ),
          ],
        ),
      ),
    );
    if (source == null || !mounted) return;
    String? path;
    if (source == 'camera') {
      final picker = ImagePicker();
      final xfile = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
      path = xfile?.path;
    } else if (source == 'gallery') {
      final picker = ImagePicker();
      final xfile = await picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
      path = xfile?.path;
    } else if (source == 'file') {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['jpg', 'jpeg', 'png', 'pdf'],
        withData: false,
      );
      path = result?.files.single.path;
    }
    if (path != null && mounted) {
      setState(() => _documents.add(VoyageDocEntry(path: path!, docType: docType, label: label)));
    }
  }

  IconData _docIcon(String docType) {
    switch (docType) {
      case 'passport':
        return Icons.badge_outlined;
      case 'travel_booking':
        return Icons.confirmation_number_outlined;
      default:
        return Icons.description_outlined;
    }
  }

  String _docTypeLabel(String docType) {
    switch (docType) {
      case 'passport':
        return kIdentityDocLabel;
      case 'travel_booking':
        return 'Billet / réservation';
      default:
        return 'Document';
    }
  }

  Future<void> _ajouterMineur() async {
    final result = await showModalBottomSheet<MineurEntry>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => const _AjouterMineurSheet(),
    );
    if (result != null && mounted) {
      setState(() {
        _mineurs.add(result);
        _documents.add(
          VoyageDocEntry(
            path: result.photoPasseportPath,
            docType: 'passport',
            label: 'Passeport (enfant) — ${result.nom}',
          ),
        );
        if (result.photoPortraitPath != null) {
          _documents.add(
            VoyageDocEntry(
              path: result.photoPortraitPath!,
              docType: 'photo_enfant',
              label: 'Photo enfant — ${result.nom}',
            ),
          );
        }
      });
    }
  }

  Future<void> _modifierMineur(MineurEntry existing) async {
    final result = await showModalBottomSheet<MineurEntry>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _AjouterMineurSheet(initial: existing),
    );
    if (result != null && mounted) {
      setState(() {
        _documents.removeWhere((d) =>
            d.path == existing.photoPasseportPath ||
            d.path == existing.photoPortraitPath);
        final index = _mineurs.indexOf(existing);
        if (index >= 0) _mineurs[index] = result;
        _documents.add(
          VoyageDocEntry(
            path: result.photoPasseportPath,
            docType: 'passport',
            label: 'Passeport (enfant) — ${result.nom}',
          ),
        );
        if (result.photoPortraitPath != null) {
          _documents.add(
            VoyageDocEntry(
              path: result.photoPortraitPath!,
              docType: 'photo_enfant',
              label: 'Photo enfant — ${result.nom}',
            ),
          );
        }
      });
    }
  }

  Future<void> _modifierEnfantVoyageur(int index) async {
    if (index < 0 || index >= _enfantsVoyageurs.length) return;
    final existing = _enfantsVoyageurs[index];
    final result = await showModalBottomSheet<MineurEntry>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _AjouterMineurSheet(initial: existing),
    );
    if (result != null && mounted) {
      setState(() {
        _documents.removeWhere((d) =>
            d.path == existing.photoPasseportPath ||
            d.path == existing.photoPortraitPath);
        _enfantsVoyageurs[index] = result;
        _documents.add(
          VoyageDocEntry(
            path: result.photoPasseportPath,
            docType: 'passport',
            label: 'Passeport (enfant voyageur) — ${result.nom}',
          ),
        );
        if (result.photoPortraitPath != null) {
          _documents.add(
            VoyageDocEntry(
              path: result.photoPortraitPath!,
              docType: 'photo_enfant',
              label: 'Photo enfant (voyageur) — ${result.nom}',
            ),
          );
        }
      });
    }
  }

  Future<void> _ajouterEnfantVoyageur() async {
    final result = await showModalBottomSheet<MineurEntry>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => const _AjouterMineurSheet(),
    );
    if (result != null && mounted) {
      setState(() {
        _enfantsVoyageurs.add(result);
        _documents.add(
          VoyageDocEntry(
            path: result.photoPasseportPath,
            docType: 'passport',
            label: 'Passeport (enfant voyageur) — ${result.nom}',
          ),
        );
        if (result.photoPortraitPath != null) {
          _documents.add(
            VoyageDocEntry(
              path: result.photoPortraitPath!,
              docType: 'photo_enfant',
              label: 'Photo enfant (voyageur) — ${result.nom}',
            ),
          );
        }
      });
    }
  }

  Future<String?> _searchableDropdown(String label, List<String> options) {
    return showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _DestinationSearchSheet(title: label, options: options),
    );
  }

  Widget _dropdown(
    String label,
    String? value,
    ValueChanged<String?> onChanged,
    List<String> options, {
    bool enabled = true,
    String emptyLabel = 'Sélectionner',
    String? selectionError,
  }) {
    if (!enabled) {
      return InputDecorator(
        decoration: MHSurfaceCard.input(labelText: label),
        child: Text(
          emptyLabel,
          style: const TextStyle(color: Color(0xFF64748B)),
        ),
      );
    }

    final useSearch = options.length >= 4;
    if (useSearch) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: enabled
                ? () async {
                    final selected = await _searchableDropdown(label, options);
                    if (!mounted || selected == null) return;
                    onChanged(selected);
                  }
                : null,
            child: InputDecorator(
              decoration: MHSurfaceCard.input(
                labelText: label,
                suffixIcon: const Icon(Icons.search),
                errorText: selectionError,
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      value ?? 'Sélectionner',
                      style: TextStyle(
                        color: value != null ? const Color(0xFF1E293B) : const Color(0xFF64748B),
                      ),
                      overflow: TextOverflow.ellipsis,
                      maxLines: 1,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      );
    }
    return DropdownButtonFormField<String>(
      key: ValueKey(value),
      initialValue: value,
      decoration: MHSurfaceCard.input(labelText: label),
      items: [
        const DropdownMenuItem(value: null, child: Text('Sélectionner')),
        ...options.map((e) => DropdownMenuItem(value: e, child: Text(e))),
      ],
      onChanged: onChanged,
      validator: label.contains('*') ? (v) => v == null || v.isEmpty ? 'Requis' : null : null,
    );
  }

  /// « Date de départ & Date de retour » en une seule case : sélection de la
  /// plage complète dans le calendrier natif (showDateRangePicker).
  Widget _dateRangeField() {
    String fmt(DateTime d) =>
        '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
    final label = (_dateDepart != null && _dateRetour != null)
        ? '${fmt(_dateDepart!)}  →  ${fmt(_dateRetour!)}'
        : 'Sélectionner';
    return InkWell(
      onTap: () async {
        final now = DateTime.now();
        final picked = await showDateRangePicker(
          context: context,
          initialDateRange: (_dateDepart != null && _dateRetour != null)
              ? DateTimeRange(start: _dateDepart!, end: _dateRetour!)
              : null,
          firstDate: now,
          lastDate: now.add(const Duration(days: 365 * 2)),
          helpText: 'Dates de départ et de retour',
          confirmText: 'Valider',
          cancelText: 'Annuler',
          saveText: 'Valider',
          builder: (ctx, child) => Theme(
            // Chiffres en blanc sur les bandes violettes (retour test).
            data: Theme.of(ctx).copyWith(
              datePickerTheme: DatePickerThemeData(
                rangeSelectionBackgroundColor: AppColors.secondary,
                dayForegroundColor: WidgetStateProperty.resolveWith((states) =>
                    states.contains(WidgetState.selected)
                        ? Colors.white
                        : null),
                dayOverlayColor: WidgetStateProperty.resolveWith((states) =>
                    states.contains(WidgetState.selected)
                        ? Colors.white.withValues(alpha: 0.14)
                        : null),
                rangePickerHeaderForegroundColor: AppColors.secondary,
              ),
            ),
            child: child!,
          ),
        );
        if (picked != null) {
          // Voyage limité à 92 jours (workflow MyMHC V3).
          if (picked.end.difference(picked.start).inDays > kMaxTripDays) {
            if (!mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
              content: Text('La durée du voyage est limitée à $kMaxTripDays jours.'),
              backgroundColor: AppColors.danger,
            ));
            return;
          }
          setState(() {
            _dateDepart = picked.start;
            _dateRetour = picked.end;
          });
        }
      },
      child: InputDecorator(
        decoration: MHSurfaceCard.input(
          labelText: 'Date de départ & Date de retour',
          suffixIcon: const Icon(Icons.date_range, size: 20),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: (_dateDepart != null && _dateRetour != null)
                ? const Color(0xFF1E293B)
                : const Color(0xFF64748B),
          ),
        ),
      ),
    );
  }
}

/// Bottom sheet de recherche (pays / ville) : évite les débordements de [AlertDialog] + clavier sur Android.
class _DestinationSearchSheet extends StatefulWidget {
  const _DestinationSearchSheet({
    required this.title,
    required this.options,
  });

  final String title;
  final List<String> options;

  @override
  State<_DestinationSearchSheet> createState() => _DestinationSearchSheetState();
}

class _DestinationSearchSheetState extends State<_DestinationSearchSheet> {
  late final TextEditingController _searchController;
  late List<String> _filtered;

  /// Recherche insensible aux accents : « cote » trouve « Côte d'Ivoire ».
  static String _normalizeSearch(String s) {
    const accents = {
      'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
      'à': 'a', 'â': 'a', 'ä': 'a',
      'î': 'i', 'ï': 'i',
      'ô': 'o', 'ö': 'o',
      'ù': 'u', 'û': 'u', 'ü': 'u',
      'ç': 'c', 'ñ': 'n',
    };
    var out = s.toLowerCase().trim();
    accents.forEach((k, v) => out = out.replaceAll(k, v));
    return out;
  }

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController();
    _filtered = List<String>.from(widget.options);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);
    final kb = mq.viewInsets.bottom;
    final hardCap = max(120.0, mq.size.height - kb - mq.padding.top - 12);

    Widget sheetBody(double height) {
      return SizedBox(
        height: height,
        child: Material(
          color: AppColors.surfaceCard,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
          clipBehavior: Clip.antiAlias,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 10),
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE2E8F0),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        widget.title,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: const Color(0xFF1E293B),
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.of(context).pop(),
                      tooltip: 'Fermer',
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: TextField(
                  controller: _searchController,
                  autofocus: true,
                  decoration: const InputDecoration(
                    hintText: 'Rechercher...',
                    prefixIcon: Icon(Icons.search),
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  onChanged: (q) {
                    final qq = _normalizeSearch(q);
                    setState(() {
                      _filtered = qq.isEmpty
                          ? List<String>.from(widget.options)
                          : widget.options.where((o) => _normalizeSearch(o).contains(qq)).toList();
                    });
                  },
                ),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: _filtered.isEmpty
                    ? const Center(
                        child: Text('Aucun résultat', style: TextStyle(color: Color(0xFF64748B))),
                      )
                    : ListView.builder(
                        itemCount: _filtered.length,
                        itemBuilder: (_, i) {
                          final opt = _filtered[i];
                          return ListTile(
                            title: Text(opt),
                            dense: true,
                            onTap: () {
                              FocusManager.instance.primaryFocus?.unfocus();
                              Navigator.of(context).pop(opt);
                            },
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      );
    }

    return Padding(
      padding: EdgeInsets.only(bottom: kb),
      child: LayoutBuilder(
        builder: (context, constraints) {
          var maxH = constraints.maxHeight;
          if (!maxH.isFinite || maxH <= 0 || maxH > hardCap) {
            maxH = hardCap;
          }
          final h = min(maxH * 0.92, hardCap * 0.88);
          return sheetBody(min(h, maxH));
        },
      ),
    );
  }
}

/// Formulaire « enfant accompagné » en bottom sheet (même approche que la recherche pays).
/// [initial] pré-remplit le formulaire pour modifier un enfant existant.
class _AjouterMineurSheet extends StatefulWidget {
  const _AjouterMineurSheet({this.initial});

  final MineurEntry? initial;

  @override
  State<_AjouterMineurSheet> createState() => _AjouterMineurSheetState();
}

class _AjouterMineurSheetState extends State<_AjouterMineurSheet> {
  late final TextEditingController _nomController;
  late final TextEditingController _prenomController;
  late final TextEditingController _nationaliteController;
  late final TextEditingController _parenteController;
  late final TextEditingController _passeportController;
  DateTime? _dateNaissance;
  DateTime? _validitePasseport;
  String? _photoPath;
  String? _portraitPath;
  int? _enfantId;
  List<Map<String, dynamic>> _savedEnfants = const [];
  bool _loadingEnfants = false;

  bool get _isEditing => widget.initial != null;

  @override
  void initState() {
    super.initState();
    final existing = widget.initial;
    _enfantId = existing?.enfantId;
    if (!_isEditing) _loadSavedEnfants();
    _nomController = TextEditingController(text: existing?.nom ?? '');
    _prenomController = TextEditingController(text: existing?.prenom ?? '');
    _nationaliteController =
        TextEditingController(text: existing?.nationalite ?? '');
    _parenteController =
        TextEditingController(text: existing?.lienParente ?? '');
    _passeportController =
        TextEditingController(text: existing?.numeroPasseport ?? '');
    _dateNaissance = existing?.dateNaissance;
    _validitePasseport = existing?.validitePasseport;
    _photoPath = existing?.photoPasseportPath;
    _portraitPath = existing?.photoPortraitPath;
  }

  @override
  void dispose() {
    _nomController.dispose();
    _prenomController.dispose();
    _nationaliteController.dispose();
    _parenteController.dispose();
    _passeportController.dispose();
    super.dispose();
  }

  /// §4.3 : réutiliser un profil enfant enregistré sans ressaisie.
  Future<void> _loadSavedEnfants() async {
    setState(() => _loadingEnfants = true);
    try {
      final list = await EnfantsService.instance.list();
      if (mounted) {
        setState(() => _savedEnfants =
            list.where((e) => e['actif'] != false).toList());
      }
    } catch (_) {
      // Profils indisponibles : saisie manuelle normale.
    } finally {
      if (mounted) setState(() => _loadingEnfants = false);
    }
  }

  DateTime? _parseDate(dynamic v) {
    if (v == null) return null;
    return DateTime.tryParse(v.toString().substring(0, 10));
  }

  Future<void> _applySavedEnfant(Map<String, dynamic> e) async {
    _enfantId = e['id'] as int?;
    _nomController.text = (e['nom'] ?? '').toString();
    _prenomController.text = (e['prenom'] ?? '').toString();
    _nationaliteController.text = (e['nationalite'] ?? '').toString();
    _parenteController.text = (e['lien_parente'] ?? '').toString();
    _passeportController.text = (e['numero_piece'] ?? '').toString();
    _dateNaissance = _parseDate(e['date_naissance']);
    _validitePasseport = _parseDate(e['validite_piece']);
    // La copie de la pièce enregistrée est un data URL : on la réécrit dans un
    // fichier temporaire pour la joindre au dossier de souscription.
    final dataUrl = (e['copie_piece_data_url'] ?? '').toString();
    if (dataUrl.startsWith('data:')) {
      try {
        final bytes = base64Decode(dataUrl.split(',').last);
        final ext = dataUrl.contains('image/png') ? 'png' : 'jpg';
        final dir = await getTemporaryDirectory();
        final f = File(
            '${dir.path}/piece_enfant_${_enfantId ?? DateTime.now().millisecondsSinceEpoch}.$ext');
        await f.writeAsBytes(bytes, flush: true);
        _photoPath = f.path;
      } catch (_) {
        _photoPath = null;
      }
    }
    final portraitUrl = (e['photo_data_url'] ?? '').toString();
    if (portraitUrl.startsWith('data:')) {
      try {
        final bytes = base64Decode(portraitUrl.split(',').last);
        final ext = portraitUrl.contains('image/png') ? 'png' : 'jpg';
        final dir = await getTemporaryDirectory();
        final f = File(
            '${dir.path}/portrait_enfant_${_enfantId ?? DateTime.now().millisecondsSinceEpoch}.$ext');
        await f.writeAsBytes(bytes, flush: true);
        _portraitPath = f.path;
      } catch (_) {
        _portraitPath = null;
      }
    }
    if (mounted) setState(() {});
  }

  Future<void> _pickPhoto(String source, {required bool portrait}) async {
    String? path;
    if (source == 'camera') {
      final picker = ImagePicker();
      final xfile = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
      path = xfile?.path;
    } else if (source == 'gallery') {
      final picker = ImagePicker();
      final xfile = await picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
      path = xfile?.path;
    } else if (source == 'file') {
      final pick = await FilePicker.platform.pickFiles(
        type: portrait ? FileType.image : FileType.custom,
        allowedExtensions: portrait ? null : ['jpg', 'jpeg', 'png', 'pdf'],
        withData: false,
      );
      path = pick?.files.single.path;
    }
    if (path != null && mounted) {
      setState(() => portrait ? _portraitPath = path : _photoPath = path);
    }
  }

  Future<void> _showPhotoSheet({bool portrait = false}) async {
    final source = await showModalBottomSheet<String>(
      context: context,
      builder: (sheetCtx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt, color: AppColors.primary),
              title: const Text('Prendre une photo'),
              onTap: () => Navigator.pop(sheetCtx, 'camera'),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library, color: AppColors.primary),
              title: const Text('Choisir une image'),
              onTap: () => Navigator.pop(sheetCtx, 'gallery'),
            ),
            ListTile(
              leading: const Icon(Icons.attach_file, color: AppColors.primary),
              title: const Text('Joindre un fichier'),
              onTap: () => Navigator.pop(sheetCtx, 'file'),
            ),
          ],
        ),
      ),
    );
    if (source != null) await _pickPhoto(source, portrait: portrait);
  }

  void _trySubmit() {
    if (_nomController.text.trim().isEmpty ||
        _dateNaissance == null ||
        _nationaliteController.text.trim().isEmpty ||
        _passeportController.text.trim().isEmpty ||
        _validitePasseport == null ||
        _photoPath == null ||
        _portraitPath == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Veuillez remplir tous les champs obligatoires : identité, copie de la pièce et photo individuelle.',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }
    // Passeport expiré : bloque la suite de la souscription.
    final today = DateUtils.dateOnly(DateTime.now());
    if (DateUtils.dateOnly(_validitePasseport!).isBefore(today)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'La date de validité du passeport est dépassée : le passeport est expiré.',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }
    String? opt(TextEditingController c) =>
        c.text.trim().isEmpty ? null : c.text.trim();
    Navigator.of(context).pop(
      MineurEntry(
        nom: _nomController.text.trim(),
        prenom: opt(_prenomController),
        nationalite: opt(_nationaliteController),
        lienParente: opt(_parenteController),
        enfantId: _enfantId,
        dateNaissance: _dateNaissance!,
        numeroPasseport: _passeportController.text.trim(),
        validitePasseport: _validitePasseport!,
        photoPasseportPath: _photoPath!,
        photoPortraitPath: _portraitPath,
      ),
    );
  }

  Widget _sheetShell(double height, Widget child) {
    return SizedBox(
      height: height,
      child: Material(
        color: AppColors.surfaceCard,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
        clipBehavior: Clip.antiAlias,
        child: child,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final mq = MediaQuery.of(context);
    final kb = mq.viewInsets.bottom;
    final hardCap = max(120.0, mq.size.height - kb - mq.padding.top - 12);

    final inner = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 10),
        Center(
          child: Container(
            width: 36,
            height: 4,
            decoration: BoxDecoration(
              color: const Color(0xFFE2E8F0),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 8, 4),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  _isEditing ? 'Modifier l\'enfant' : 'Enfant accompagné',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: const Color(0xFF1E293B),
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(context).pop(),
                tooltip: 'Fermer',
              ),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_savedEnfants.isNotEmpty) ...[
                  DropdownButtonFormField<int>(
                    initialValue: _enfantId,
                    decoration: MHSurfaceCard.input(
                        labelText:
                            'Enfant enregistré (réutilise son profil)'),
                    items: [
                      const DropdownMenuItem<int>(
                        value: null,
                        child: Text('— Nouvel enfant —'),
                      ),
                      ..._savedEnfants.map(
                        (e) => DropdownMenuItem<int>(
                          value: e['id'] as int?,
                          child: Text(
                            '${e['prenom'] ?? ''} ${e['nom'] ?? ''}'.trim(),
                          ),
                        ),
                      ),
                    ],
                    onChanged: (id) {
                      final e = _savedEnfants
                          .firstWhere((x) => x['id'] == id, orElse: () => {});
                      if (e.isNotEmpty) {
                        _applySavedEnfant(e);
                      } else {
                        setState(() => _enfantId = null);
                      }
                    },
                  ),
                  const SizedBox(height: 16),
                ] else if (_loadingEnfants)
                  const Padding(
                    padding: EdgeInsets.only(bottom: 12),
                    child: LinearProgressIndicator(minHeight: 2),
                  ),
                TextField(
                  controller: _nomController,
                  decoration: MHSurfaceCard.input(labelText: 'Nom de l\'enfant *'),
                  textCapitalization: TextCapitalization.words,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _prenomController,
                  decoration:
                      MHSurfaceCard.input(labelText: 'Prénom(s) de l\'enfant'),
                  textCapitalization: TextCapitalization.words,
                ),
                const SizedBox(height: 16),
                InkWell(
                  onTap: () async {
                    final d = await showDatePicker(
                      context: context,
                      initialDate: _dateNaissance ?? DateTime.now().subtract(const Duration(days: 365 * 5)),
                      firstDate: DateTime(2000),
                      lastDate: DateTime.now(),
                    );
                    if (d != null && mounted) setState(() => _dateNaissance = d);
                  },
                  child: InputDecorator(
                    decoration: MHSurfaceCard.input(labelText: 'Date de naissance *'),
                    child: Text(
                      _dateNaissance != null
                          ? '${_dateNaissance!.day.toString().padLeft(2, '0')}/${_dateNaissance!.month.toString().padLeft(2, '0')}/${_dateNaissance!.year}'
                          : 'Sélectionner',
                      style: TextStyle(
                        color: _dateNaissance != null ? const Color(0xFF1E293B) : const Color(0xFF64748B),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _nationaliteController,
                  decoration:
                      MHSurfaceCard.input(labelText: 'Nationalité *'),
                  textCapitalization: TextCapitalization.words,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _parenteController,
                  decoration: MHSurfaceCard.input(
                      labelText: 'Lien de parenté (facultatif)',
                      hintText: 'Ex. : fille, fils'),
                  textCapitalization: TextCapitalization.words,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _passeportController,
                  decoration: MHSurfaceCard.input(labelText: 'Numéro de passeport *'),
                  textCapitalization: TextCapitalization.characters,
                ),
                const SizedBox(height: 16),
                InkWell(
                  onTap: () async {
                    final d = await showDatePicker(
                      context: context,
                      initialDate: _validitePasseport ?? DateTime.now().add(const Duration(days: 365 * 3)),
                      firstDate: DateTime.now(),
                      lastDate: DateTime.now().add(const Duration(days: 365 * 20)),
                    );
                    if (d != null && mounted) setState(() => _validitePasseport = d);
                  },
                  child: InputDecorator(
                    decoration: MHSurfaceCard.input(labelText: 'Validité du passeport (expiration) *'),
                    child: Text(
                      _validitePasseport != null
                          ? '${_validitePasseport!.day.toString().padLeft(2, '0')}/${_validitePasseport!.month.toString().padLeft(2, '0')}/${_validitePasseport!.year}'
                          : 'Sélectionner',
                      style: TextStyle(
                        color: _validitePasseport != null ? const Color(0xFF1E293B) : const Color(0xFF64748B),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  'Copie de la pièce d\'identité (passeport) *',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppColors.secondary,
                  ),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => _showPhotoSheet(),
                  icon: const Icon(Icons.add_photo_alternate_outlined, size: 20),
                  label: Text(_photoPath == null ? 'Ajouter la copie' : 'Changer la copie'),
                ),
                if (_photoPath != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    _photoPath!.split(RegExp(r'[/\\]')).last,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
                const SizedBox(height: 16),
                Text(
                  'Photo individuelle de l\'enfant (visage visible) *',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: AppColors.secondary,
                  ),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => _showPhotoSheet(portrait: true),
                  icon: const Icon(Icons.face_retouching_natural, size: 20),
                  label: Text(_portraitPath == null ? 'Ajouter la photo' : 'Changer la photo'),
                ),
                if (_portraitPath != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    _portraitPath!.split(RegExp(r'[/\\]')).last,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Annuler'),
              ),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: _trySubmit,
                child: Text(_isEditing ? 'Enregistrer' : 'Ajouter'),
              ),
            ],
          ),
        ),
      ],
    );

    return Padding(
      padding: EdgeInsets.only(bottom: kb),
      child: LayoutBuilder(
        builder: (context, constraints) {
          var maxH = constraints.maxHeight;
          if (!maxH.isFinite || maxH <= 0 || maxH > hardCap) {
            maxH = hardCap;
          }
          final h = min(maxH * 0.95, hardCap * 0.88);
          return _sheetShell(min(h, maxH), inner);
        },
      ),
    );
  }
}
