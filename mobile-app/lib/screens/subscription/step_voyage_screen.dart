import 'dart:math' show max, min;

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/constants/app_colors.dart';
import '../../models/destination.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';

/// Un mineur accompagnant (identité, passeport, photo du passeport en pièce jointe).
class MineurEntry {
  const MineurEntry({
    required this.nom,
    required this.dateNaissance,
    required this.numeroPasseport,
    required this.validitePasseport,
    required this.photoPasseportPath,
  });
  final String nom;
  final DateTime dateNaissance;
  final String numeroPasseport;
  final DateTime validitePasseport;
  final String photoPasseportPath;
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
}

/// Étape 1 : Informations sur le voyage (destination, dates, transport, participants, mineurs).
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
  int _participants = 1;
  bool _avecMineurs = false;
  final List<MineurEntry> _mineurs = [];
  final List<VoyageDocEntry> _documents = [];
  List<DestinationCountryModel> _destinationCountries = const [];
  List<DestinationCityModel> _destinationCities = const [];
  List<ReferenceCountryModel> _referenceCountries = const [];
  final Map<int, List<DestinationCityModel>> _citiesByCountryId = {};
  bool _loadingDestinations = true;
  bool _loadingCities = false;
  String? _destinationsError;
  String? _citiesError;
  String? _residenceCountryRaw;
  String? _residenceCountryCode;
  /// Erreurs affichées sous les champs recherche pays/ville (sans FormField async).
  String? _paysFieldError;
  String? _villeFieldError;

  int get _dureeJours {
    if (_dateDepart == null || _dateRetour == null) return 0;
    return _dateRetour!.difference(_dateDepart!).inDays;
  }

  List<String> get _countryOptions => _destinationCountries
      .where((country) => !_isResidenceDestinationConflict(country))
      .map((country) => country.nom)
      .toList();

  List<String> get _cityOptions {
    return _destinationCities.map((city) => city.nom).toList();
  }

  @override
  void initState() {
    super.initState();
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
      });
    } catch (_) {
      // Le backend garde de toute façon la validation finale.
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
    setState(() {
      _loadingDestinations = true;
      _destinationsError = null;
    });
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
        _destinationsError = e.toString().replaceFirst('Exception: ', '');
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
      color: const Color(0xFFE8F0F4),
      child: SingleChildScrollView(
        keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
        padding: EdgeInsets.fromLTRB(20, 20, 20, bottomPadding),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Informations sur le voyage',
                style: theme.textTheme.titleLarge?.copyWith(
                  color: AppColors.primary,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Divider(color: Color(0xFFE2E8F0), thickness: 1),
              const SizedBox(height: 16),
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
                  _countryOptions,
                  enabled: _hasResidenceCountry,
                  emptyLabel: 'Renseignez d\'abord votre pays de résidence',
                  selectionError: _paysFieldError,
                ),
                if ((_residenceCountryLabel ?? '').isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Pays de residence: $_residenceCountryLabel',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: const Color(0xFF64748B),
                    ),
                  ),
                ] else ...[
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
              Row(
                children: [
                  Expanded(
                    child: _dateField('Date de départ', _dateDepart, (d) => setState(() => _dateDepart = d)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _dateField('Date de retour', _dateRetour, (d) => setState(() => _dateRetour = d)),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              InputDecorator(
                decoration: const InputDecoration(
                  labelText: 'Durée du séjour',
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(),
                ),
                child: Text(
                  _dureeJours > 0 ? '$_dureeJours jours' : 'Calcul automatique',
                  style: TextStyle(
                    color: _dureeJours > 0 ? const Color(0xFF1E293B) : const Color(0xFF64748B),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              TextFormField(
                initialValue: '1',
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Nombre de participants *',
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(),
                ),
                onChanged: (v) => setState(() => _participants = int.tryParse(v) ?? 1),
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Requis';
                  if (int.tryParse(v) == null || int.parse(v) < 1) return 'Minimum 1';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              Text(
                'Voyagez-vous avec des enfants mineurs ? *',
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: const Color(0xFF1E293B),
                ),
              ),
              Row(
                children: [
                  Radio<bool>(
                    value: true,
                    groupValue: _avecMineurs,
                    onChanged: (v) => setState(() => _avecMineurs = true),
                    activeColor: AppColors.primary,
                  ),
                  const Text('Oui'),
                  const SizedBox(width: 24),
                  Radio<bool>(
                    value: false,
                    groupValue: _avecMineurs,
                    onChanged: (v) => setState(() => _avecMineurs = false),
                    activeColor: AppColors.primary,
                  ),
                  const Text('Non'),
                ],
              ),
              if (_avecMineurs) ...[
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Enfants accompagnés',
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: const Color(0xFF1E293B),
                      ),
                    ),
                    TextButton.icon(
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
                        color: Colors.white,
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
                            onPressed: () => setState(() {
                              _documents.removeWhere((d) => d.path == m.photoPasseportPath);
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
                  fontWeight: FontWeight.w600,
                  color: const Color(0xFF1E293B),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Prenez une photo ou joignez vos documents (passeport, billet, etc.)',
                style: theme.textTheme.bodySmall?.copyWith(color: const Color(0xFF64748B)),
              ),
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
                      color: Colors.white,
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
                    final titre = 'Voyage vers $_ville, $_pays';
                    if (titre.isEmpty) return;
                    widget.onContinue(VoyageFormData(
                      titre: titre,
                      destination: _ville ?? '',
                      destinationCountryId: _paysId!,
                      destinationCountryName: _pays ?? '',
                      destinationCityName: _ville ?? '',
                      residenceCountryName: _residenceCountryLabel ?? _residenceCountryRaw,
                      dateDepart: _dateDepart ?? DateTime.now(),
                      dateRetour: _dateRetour,
                      nombreParticipants: _participants,
                      dureeJours: _dureeJours > 0 ? _dureeJours : null,
                      mineurs: _avecMineurs && _mineurs.isNotEmpty ? List.from(_mineurs) : null,
                      documents: _documents.isNotEmpty ? List.from(_documents) : null,
                    ));
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text('Continuer vers le choix du produit'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDocButtons(ThemeData theme) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        _docActionChip(
          icon: Icons.badge_outlined,
          label: 'Passeport',
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
      color: Colors.white,
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
              Text(label, style: theme.textTheme.labelLarge?.copyWith(color: const Color(0xFF1E293B))),
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
        return 'Passeport';
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
        decoration: InputDecoration(
          labelText: label,
          filled: true,
          fillColor: Colors.white,
          border: const OutlineInputBorder(),
        ),
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
              decoration: InputDecoration(
                labelText: label,
                filled: true,
                fillColor: Colors.white,
                border: const OutlineInputBorder(),
                focusedBorder: OutlineInputBorder(
                  borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
                  borderRadius: BorderRadius.circular(8),
                ),
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
      value: value ?? (options.isNotEmpty ? null : null),
      decoration: InputDecoration(
        labelText: label,
        filled: true,
        fillColor: Colors.white,
        border: const OutlineInputBorder(),
        focusedBorder: OutlineInputBorder(
          borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
          borderRadius: BorderRadius.circular(8),
        ),
      ),
      items: [const DropdownMenuItem(value: null, child: Text('Sélectionner'))]
          ..addAll(options.map((e) => DropdownMenuItem(value: e, child: Text(e)))),
      onChanged: onChanged,
      validator: label.contains('*') ? (v) => v == null || v.isEmpty ? 'Requis' : null : null,
    );
  }

  Widget _dateField(String label, DateTime? value, ValueChanged<DateTime?> onChanged) {
    return InkWell(
      onTap: () async {
        final d = await showDatePicker(
          context: context,
          initialDate: value ?? DateTime.now(),
          firstDate: DateTime.now(),
          lastDate: DateTime.now().add(const Duration(days: 365 * 2)),
        );
        if (d != null) onChanged(d);
      },
      child: InputDecorator(
        decoration: InputDecoration(
          labelText: label,
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(),
          suffixIcon: Icon(Icons.calendar_today, size: 20),
        ),
        child: Text(
          value != null
              ? '${value.day.toString().padLeft(2, '0')}/${value.month.toString().padLeft(2, '0')}/${value.year}'
              : 'Sélectionner',
          style: TextStyle(
            color: value != null ? const Color(0xFF1E293B) : const Color(0xFF64748B),
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
          color: Colors.white,
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
                    final qq = q.trim().toLowerCase();
                    setState(() {
                      _filtered = qq.isEmpty
                          ? List<String>.from(widget.options)
                          : widget.options.where((o) => o.toLowerCase().contains(qq)).toList();
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
class _AjouterMineurSheet extends StatefulWidget {
  const _AjouterMineurSheet();

  @override
  State<_AjouterMineurSheet> createState() => _AjouterMineurSheetState();
}

class _AjouterMineurSheetState extends State<_AjouterMineurSheet> {
  late final TextEditingController _nomController;
  late final TextEditingController _passeportController;
  DateTime? _dateNaissance;
  DateTime? _validitePasseport;
  String? _photoPath;

  @override
  void initState() {
    super.initState();
    _nomController = TextEditingController();
    _passeportController = TextEditingController();
  }

  @override
  void dispose() {
    _nomController.dispose();
    _passeportController.dispose();
    super.dispose();
  }

  Future<void> _pickPassportPhoto(String source) async {
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
        type: FileType.custom,
        allowedExtensions: ['jpg', 'jpeg', 'png', 'pdf'],
        withData: false,
      );
      path = pick?.files.single.path;
    }
    if (path != null && mounted) setState(() => _photoPath = path);
  }

  Future<void> _showPhotoSheet() async {
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
    if (source != null) await _pickPassportPhoto(source);
  }

  void _trySubmit() {
    if (_nomController.text.trim().isEmpty ||
        _dateNaissance == null ||
        _passeportController.text.trim().isEmpty ||
        _validitePasseport == null ||
        _photoPath == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Veuillez remplir tous les champs obligatoires, y compris la photo du passeport.',
          ),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }
    Navigator.of(context).pop(
      MineurEntry(
        nom: _nomController.text.trim(),
        dateNaissance: _dateNaissance!,
        numeroPasseport: _passeportController.text.trim(),
        validitePasseport: _validitePasseport!,
        photoPasseportPath: _photoPath!,
      ),
    );
  }

  Widget _sheetShell(double height, Widget child) {
    return SizedBox(
      height: height,
      child: Material(
        color: Colors.white,
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
                  'Enfant accompagné',
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
                TextField(
                  controller: _nomController,
                  decoration: const InputDecoration(
                    labelText: 'Nom de l\'enfant *',
                    border: OutlineInputBorder(),
                  ),
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
                    decoration: const InputDecoration(
                      labelText: 'Date de naissance *',
                      border: OutlineInputBorder(),
                    ),
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
                  controller: _passeportController,
                  decoration: const InputDecoration(
                    labelText: 'Numéro de passeport *',
                    border: OutlineInputBorder(),
                  ),
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
                    decoration: const InputDecoration(
                      labelText: 'Validité du passeport (expiration) *',
                      border: OutlineInputBorder(),
                    ),
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
                  'Photo du passeport *',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: const Color(0xFF1E293B),
                  ),
                ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _showPhotoSheet,
                  icon: const Icon(Icons.add_photo_alternate_outlined, size: 20),
                  label: Text(_photoPath == null ? 'Ajouter la photo' : 'Changer la photo'),
                ),
                if (_photoPath != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    _photoPath!.split(RegExp(r'[/\\]')).last,
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
                child: const Text('Ajouter'),
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
