import 'package:country_code_picker/country_code_picker.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/constants/app_colors.dart';
import '../core/network/api_client.dart' as net;
import '../core/widgets/mh_logo_header.dart';
import '../core/widgets/mh_surface_card.dart';
import '../models/destination.dart';
import '../services/api_services.dart';

/// Page d'inscription simplifiée : informations civiles et identifiants.
class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final DestinationsService _destinationsService = DestinationsService();
  final _nomController = TextEditingController();
  final _prenomController = TextEditingController();
  final _emailController = TextEditingController();
  final _phoneController = TextEditingController();
  final _nomContactUrgenceController = TextEditingController();
  final _contactUrgenceController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  DateTime? _dateNaissance;
  String _sexe = '';
  String? _paysResidence;
  String? _nationalite;
  late CountryCode _phoneCountryCode;
  late CountryCode _contactUrgenceCountryCode;

  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  bool _isLoading = false;
  bool _loadingReferenceCountries = true;
  String? _errorMessage;
  List<ReferenceCountryModel> _referenceCountries = const [];

  @override
  void initState() {
    super.initState();
    _phoneCountryCode = CountryCode.fromCountryCode('SN');
    _contactUrgenceCountryCode = CountryCode.fromCountryCode('SN');
    _loadReferenceCountries();
  }

  @override
  void dispose() {
    _nomController.dispose();
    _prenomController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _nomContactUrgenceController.dispose();
    _contactUrgenceController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _handleRegister() async {
    if (_isLoading || !_formKey.currentState!.validate()) return;
    if (_dateNaissance == null) {
      setState(() => _errorMessage = 'Veuillez sélectionner votre date de naissance');
      return;
    }
    if (_sexe.isEmpty) {
      setState(() => _errorMessage = 'Veuillez sélectionner votre sexe');
      return;
    }
    setState(() {
      _errorMessage = null;
      _isLoading = true;
    });

    final nom = _nomController.text.trim();
    final prenom = _prenomController.text.trim();
    final fullName = [nom, prenom].where((part) => part.isNotEmpty).join(' ');
    final email = _emailController.text.trim();

    final body = <String, dynamic>{
      'email': email,
      'username': email,
      'password': _passwordController.text,
      'full_name': fullName.isEmpty ? null : fullName,
      'date_naissance': _dateNaissance!.toIso8601String().substring(0, 10),
      'telephone': _phoneController.text.trim().isEmpty
          ? null
          : '${_phoneCountryCode.dialCode ?? ''}${_phoneController.text.trim().replaceAll(RegExp(r'[\s\-\.]'), '')}',
      'sexe': _sexe,
      'pays_residence': _paysResidence,
      'nationalite': _nationalite,
      'nom_contact_urgence': _nomContactUrgenceController.text.trim().isEmpty
          ? null
          : _nomContactUrgenceController.text.trim(),
      'contact_urgence': _contactUrgenceController.text.trim().isEmpty
          ? null
          : '${_contactUrgenceCountryCode.dialCode ?? ''}${_contactUrgenceController.text.trim().replaceAll(RegExp(r'[\s\-\.]'), '')}',
    };

    try {
      await net.ApiClient().post<Map<String, dynamic>>(
        '/auth/register',
        body: body,
        fromJson: (d) => d as Map<String, dynamic>,
      );
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Inscription enregistrée. Saisissez le code reçu par e-mail sur le site web pour activer votre compte, puis connectez-vous ici.',
          ),
          backgroundColor: AppColors.success,
        ),
      );
      context.go(
        '/login?username=${Uri.encodeComponent(email)}&pending_email_verify=1',
      );
    } on DioException catch (e) {
      if (!mounted) return;
      final msg = e.response?.data is Map && e.response!.data['detail'] != null
          ? e.response!.data['detail'].toString()
          : e.toString().replaceFirst('DioException: ', '');
      setState(() {
        _errorMessage = msg;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  Future<void> _loadReferenceCountries() async {
    try {
      final countries = await _destinationsService.getReferenceCountries();
      if (!mounted) return;
      setState(() {
        _referenceCountries = countries;
        _loadingReferenceCountries = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingReferenceCountries = false;
        _errorMessage = 'Impossible de charger la liste des pays. Vérifiez votre connexion puis réessayez.';
      });
    }
  }

  String? _countryLabelFromCode(String? code) {
    if (code == null || code.trim().isEmpty) return null;
    for (final country in _referenceCountries) {
      if (country.code.toUpperCase() == code.trim().toUpperCase()) {
        return country.nom;
      }
    }
    return code;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        backgroundColor: AppColors.cardBg,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppColors.primary),
          onPressed: () => context.pop(),
        ),
        title: Text(
          'Inscription',
          style: GoogleFonts.poppins(
            fontWeight: FontWeight.w600,
            color: AppColors.primary,
          ),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 16),
                const MHLogoHeader(height: 72, compact: true),
                const SizedBox(height: 24),
                MHSurfaceCard(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _sectionTitle('Informations civiles', 'Identité et coordonnées'),
                      Row(
                        children: [
                          Expanded(
                            child: _buildTextField(
                              controller: _nomController,
                              label: 'Nom *',
                              validator: (v) => (v == null || v.trim().isEmpty) ? 'Requis' : null,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _buildTextField(
                              controller: _prenomController,
                              label: 'Prénom *',
                              validator: (v) => (v == null || v.trim().isEmpty) ? 'Requis' : null,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: _emailController,
                        label: 'Email *',
                        keyboardType: TextInputType.emailAddress,
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) return 'Requis';
                          if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(v)) return 'Email invalide';
                          return null;
                        },
                      ),
                      const SizedBox(height: 12),
                      _buildDateField('Date de naissance *', _dateNaissance, (d) => setState(() => _dateNaissance = d)),
                      const SizedBox(height: 12),
                      _buildSexeField(),
                      const SizedBox(height: 12),
                      _buildPhoneField(
                        controller: _phoneController,
                        countryCode: _phoneCountryCode,
                        onCountryChanged: (c) => setState(() => _phoneCountryCode = c),
                        label: 'Téléphone *',
                        isRequired: true,
                      ),
                      const SizedBox(height: 12),
                      _buildSearchableCountryPicker(
                        'Pays de résidence',
                        _paysResidence,
                        (v) => setState(() => _paysResidence = v),
                      ),
                      const SizedBox(height: 12),
                      _buildSearchableCountryPicker(
                        'Nationalité',
                        _nationalite,
                        (v) => setState(() => _nationalite = v),
                      ),
                      const SizedBox(height: 12),
                      _buildTextField(
                        controller: _nomContactUrgenceController,
                        label: 'Nom du contact urgence',
                      ),
                      const SizedBox(height: 12),
                      _buildPhoneField(
                        controller: _contactUrgenceController,
                        countryCode: _contactUrgenceCountryCode,
                        onCountryChanged: (c) => setState(() => _contactUrgenceCountryCode = c),
                        label: 'Téléphone du contact urgence',
                        isRequired: false,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                MHSurfaceCard(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _sectionTitle('Identifiants de connexion', 'Votre adresse e-mail servira d\'identifiant'),
                      _buildPasswordField(),
                      const SizedBox(height: 12),
                      _buildConfirmPasswordField(),
                      if (_errorMessage != null) ...[
                        const SizedBox(height: 12),
                        Text(
                          _errorMessage!,
                          style: const TextStyle(color: AppColors.danger, fontSize: 14),
                          textAlign: TextAlign.center,
                        ),
                      ],
                      const SizedBox(height: 24),
                      SizedBox(
                        height: 52,
                        child: FilledButton(
                          onPressed: _isLoading ? null : _handleRegister,
                          style: FilledButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                          child: _isLoading
                              ? const SizedBox(
                                  width: 24,
                                  height: 24,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                )
                              : Text('S\'inscrire', style: GoogleFonts.poppins(fontWeight: FontWeight.w600)),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('Déjà un compte ? ', style: GoogleFonts.poppins(color: AppColors.mutedText)),
                    TextButton(
                      onPressed: () => context.go('/login'),
                      child: Text('Se connecter', style: GoogleFonts.poppins(color: AppColors.primary, fontWeight: FontWeight.w600)),
                    ),
                  ],
                ),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _sectionTitle(String title, String subtitle) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: AppColors.secondary,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: GoogleFonts.poppins(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: AppColors.secondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
  }) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      validator: validator,
      decoration: MHSurfaceCard.input(labelText: label),
      enabled: !_isLoading,
    );
  }

  Widget _buildPasswordField() {
    return TextFormField(
      controller: _passwordController,
      obscureText: _obscurePassword,
      validator: (v) {
        if (v == null || v.isEmpty) return 'Requis';
        if (v.length < 8) return 'Minimum 8 caractères';
        return null;
      },
      decoration: MHSurfaceCard.input(
        labelText: 'Mot de passe *',
        suffixIcon: IconButton(
          icon: Icon(_obscurePassword ? Icons.visibility_off : Icons.visibility, color: AppColors.mutedText),
          onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
        ),
      ),
      enabled: !_isLoading,
    );
  }

  Widget _buildConfirmPasswordField() {
    return TextFormField(
      controller: _confirmPasswordController,
      obscureText: _obscureConfirmPassword,
      validator: (v) {
        if (v == null || v.isEmpty) return 'Requis';
        if (v != _passwordController.text) return 'Les mots de passe ne correspondent pas';
        return null;
      },
      decoration: MHSurfaceCard.input(
        labelText: 'Confirmer le mot de passe *',
        suffixIcon: IconButton(
          icon: Icon(
            _obscureConfirmPassword ? Icons.visibility_off : Icons.visibility,
            color: AppColors.mutedText,
          ),
          onPressed: () => setState(() => _obscureConfirmPassword = !_obscureConfirmPassword),
        ),
      ),
      enabled: !_isLoading,
    );
  }

  Widget _buildDateField(String label, DateTime? value, void Function(DateTime?) onChanged) {
    return InkWell(
      onTap: _isLoading
          ? null
          : () async {
              final date = await showDatePicker(
                context: context,
                initialDate: value ?? DateTime(2000),
                firstDate: DateTime(1900),
                lastDate: DateTime(2100),
              );
              if (date != null) onChanged(date);
            },
      borderRadius: BorderRadius.circular(8),
      child: InputDecorator(
        decoration: MHSurfaceCard.input(
          labelText: label,
          suffixIcon: const Icon(Icons.calendar_today),
        ),
        child: Text(
          value != null
              ? '${value.day.toString().padLeft(2, '0')}/${value.month.toString().padLeft(2, '0')}/${value.year}'
              : 'Sélectionner',
          style: TextStyle(color: value != null ? Colors.black87 : AppColors.mutedText),
        ),
      ),
    );
  }

  Widget _buildSexeField() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Sexe *',
          style: GoogleFonts.poppins(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: AppColors.secondary,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: _ChoiceChip(
                label: 'Homme',
                selected: _sexe == 'M',
                onTap: () => setState(() => _sexe = 'M'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _ChoiceChip(
                label: 'Femme',
                selected: _sexe == 'F',
                onTap: () => setState(() => _sexe = 'F'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSearchableCountryPicker(String label, String? value, void Function(String?) onChanged) {
    return FormField<String?>(
      initialValue: value,
      builder: (state) {
        final displayValue = _countryLabelFromCode(value);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            InkWell(
              onTap: (_isLoading || _loadingReferenceCountries)
                  ? null
                  : () async {
                      final selected = await _showCountrySearchDialog(label, value);
                      if (selected != null && mounted) {
                        onChanged(selected);
                        state.didChange(selected);
                      }
                    },
              borderRadius: BorderRadius.circular(8),
              child: InputDecorator(
                decoration: MHSurfaceCard.input(
                  labelText: label,
                  suffixIcon: const Icon(Icons.search, color: AppColors.mutedText),
                ),
                child: Text(
                  _loadingReferenceCountries ? 'Chargement...' : (displayValue ?? 'Choisir...'),
                  style: TextStyle(
                    color: displayValue != null ? Colors.black87 : AppColors.mutedText,
                    fontSize: 16,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Future<String?> _showCountrySearchDialog(String label, String? currentValue) async {
    return Navigator.of(context).push<String>(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => _CountrySearchPage(
          label: label,
          currentValue: currentValue,
          countries: _referenceCountries,
        ),
      ),
    );
  }

  Widget _buildPhoneField({
    required TextEditingController controller,
    required CountryCode countryCode,
    required void Function(CountryCode) onCountryChanged,
    required String label,
    required bool isRequired,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CountryCodePicker(
          padding: EdgeInsets.zero,
          onChanged: onCountryChanged,
          initialSelection: countryCode.code ?? 'SN',
          favorite: const ['+221', 'SN', '+33', 'FR'],
          showCountryOnly: false,
          showOnlyCountryWhenClosed: false,
          alignLeft: false,
          textStyle: const TextStyle(fontSize: 16),
          dialogTextStyle: const TextStyle(fontSize: 16),
          searchDecoration: const InputDecoration(hintText: 'Rechercher un pays', border: OutlineInputBorder()),
          boxDecoration: BoxDecoration(
            color: AppColors.surfaceFieldFill,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppColors.surfaceFieldBorder),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: TextFormField(
            controller: controller,
            keyboardType: TextInputType.phone,
            validator: isRequired ? (v) => (v == null || v.trim().isEmpty) ? 'Requis' : null : null,
            decoration: MHSurfaceCard.input(
              labelText: label,
              hintText: '771234567',
            ),
            enabled: !_isLoading,
          ),
        ),
      ],
    );
  }
}

class _ChoiceChip extends StatelessWidget {
  const _ChoiceChip({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? AppColors.primary.withValues(alpha: 0.15) : AppColors.surfaceFieldFill,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            border: Border.all(
              color: selected ? AppColors.primary : AppColors.surfaceFieldBorder,
              width: selected ? 2 : 1,
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
                color: selected ? AppColors.primary : AppColors.mutedText,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CountrySearchPage extends StatefulWidget {
  const _CountrySearchPage({
    required this.label,
    required this.currentValue,
    required this.countries,
  });

  final String label;
  final String? currentValue;
  final List<ReferenceCountryModel> countries;

  @override
  State<_CountrySearchPage> createState() => _CountrySearchPageState();
}

class _CountrySearchPageState extends State<_CountrySearchPage> {
  late final TextEditingController _searchController;
  late List<ReferenceCountryModel> _filteredList;

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController();
    _filteredList = List.from(widget.countries);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _filterCountries(String query) {
    final normalizedQuery = query.trim().toLowerCase();
    setState(() {
      _filteredList = normalizedQuery.isEmpty
          ? List.from(widget.countries)
          : widget.countries
              .where((country) => country.nom.toLowerCase().contains(normalizedQuery))
              .toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.label),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TextField(
                controller: _searchController,
                autofocus: true,
                decoration: const InputDecoration(
                  hintText: 'Rechercher un pays...',
                  prefixIcon: Icon(Icons.search),
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                onChanged: _filterCountries,
              ),
              const SizedBox(height: 12),
              Expanded(
                child: _filteredList.isEmpty
                    ? const Center(
                        child: Text(
                          'Aucun résultat',
                          style: TextStyle(color: Color(0xFF64748B)),
                        ),
                      )
                    : ListView.builder(
                        itemCount: _filteredList.length,
                        itemBuilder: (_, i) {
                          final country = _filteredList[i];
                          return ListTile(
                            title: Text(country.nom),
                            subtitle: Text(country.code),
                            selected: country.code == widget.currentValue,
                            onTap: () => Navigator.of(context).pop(country.code),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
