import 'package:country_code_picker/country_code_picker.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/constants/app_colors.dart';
import '../core/network/api_client.dart' as net;
import '../core/utils/api_error_helper.dart';
import '../core/widgets/mh_app_bar.dart';
import '../core/widgets/mh_kit_widgets.dart';
import '../core/widgets/mh_stripe.dart';
import '../core/widgets/mh_surface_card.dart';
import '../models/destination.dart';
import '../services/api_services.dart';
import '../services/reference_countries_fallback.dart';

/// Inscription en 3 écrans (kit MyMHC) :
/// 1. informations personnelles, 2. identifiants, 3. canal de vérification.
class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _pageController = PageController();
  final _formKeys = [
    GlobalKey<FormState>(),
    GlobalKey<FormState>(),
    GlobalKey<FormState>(),
  ];
  final DestinationsService _destinationsService = DestinationsService();

  // Étape 1 — informations personnelles
  final _nomController = TextEditingController();
  final _prenomController = TextEditingController();
  final _phoneController = TextEditingController();
  final _whatsappController = TextEditingController();
  DateTime? _dateNaissance;
  String _sexe = '';
  String? _paysResidence;
  String? _nationalite;
  late CountryCode _phoneCountryCode;
  late CountryCode _whatsappCountryCode;

  // Étape 2 — identifiants
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _contactUrgenceController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  // Étape 3 — canal de vérification + consentements
  String _canalVerification = 'email';
  bool _consentCgu = false;
  bool _consentConfidentialite = false;

  int _step = 0;
  bool _isLoading = false;
  bool _loadingReferenceCountries = true;
  String? _errorMessage;
  List<ReferenceCountryModel> _referenceCountries = const [];

  @override
  void initState() {
    super.initState();
    _phoneCountryCode = CountryCode.fromCountryCode('CG');
    _whatsappCountryCode = CountryCode.fromCountryCode('CG');
    _loadReferenceCountries();
  }

  @override
  void dispose() {
    _pageController.dispose();
    _nomController.dispose();
    _prenomController.dispose();
    _phoneController.dispose();
    _whatsappController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _contactUrgenceController.dispose();
    super.dispose();
  }

  void _goToStep(int step) {
    setState(() {
      _step = step;
      _errorMessage = null;
    });
    _pageController.animateToPage(
      step,
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeOut,
    );
  }

  void _next() {
    if (!(_formKeys[_step].currentState?.validate() ?? false)) return;
    if (_step == 0 && _dateNaissance == null) {
      setState(() => _errorMessage =
          'Veuillez sélectionner votre date de naissance');
      return;
    }
    if (_step == 0 && _sexe.isEmpty) {
      setState(() => _errorMessage = 'Veuillez sélectionner votre genre');
      return;
    }
    if (_step < 2) {
      _goToStep(_step + 1);
    } else {
      _handleRegister();
    }
  }

  void _previous() {
    if (_step > 0) {
      _goToStep(_step - 1);
    } else {
      context.pop();
    }
  }

  Future<void> _handleRegister() async {
    if (_isLoading) return;
    if (!_consentCgu || !_consentConfidentialite) {
      setState(() => _errorMessage =
          'Veuillez accepter les CGU et la politique de confidentialité');
      return;
    }

    setState(() {
      _errorMessage = null;
      _isLoading = true;
    });

    final email = _emailController.text.trim();
    final contactRaw = _contactUrgenceController.text.trim();
    final fullName =
        '${_prenomController.text.trim()} ${_nomController.text.trim()}'.trim();
    final body = <String, dynamic>{
      'email': email,
      'username': email,
      'password': _passwordController.text,
      'full_name': fullName,
      'date_naissance': _dateNaissance!.toIso8601String().substring(0, 10),
      'telephone': _phoneController.text.trim().isEmpty
          ? null
          : '${_phoneCountryCode.dialCode ?? ''}${_phoneController.text.trim().replaceAll(RegExp(r'[\s\-\.]'), '')}',
      'sexe': _sexe,
      'pays_residence': _paysResidence,
      'nationalite': _nationalite,
      'numero_whatsapp': _whatsappController.text.trim().isEmpty
          ? null
          : '${_whatsappCountryCode.dialCode ?? ''}${_whatsappController.text.trim().replaceAll(RegExp(r'[\s\-\.]'), '')}',
      'contact_urgence': contactRaw.isEmpty ? null : contactRaw,
      'canal_verification': _canalVerification,
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
        SnackBar(
          content: Text(switch (_canalVerification) {
            'sms' =>
              'Inscription enregistrée. Saisissez le code reçu par SMS pour activer votre compte.',
            'whatsapp' =>
              'Inscription enregistrée. Saisissez le code reçu par WhatsApp pour activer votre compte.',
            _ =>
              'Inscription enregistrée. Saisissez le code reçu par e-mail pour activer votre compte.',
          }),
          backgroundColor: AppColors.success,
        ),
      );
      context.go(
        '/verify-email?email=${Uri.encodeComponent(email)}&channel=$_canalVerification',
      );
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = apiErrorToUserMessage(e);
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = apiErrorToUserMessage(e);
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
      final fallback = await fetchReferenceCountriesFallback();
      if (!mounted) return;
      setState(() {
        _referenceCountries = fallback;
        _loadingReferenceCountries = false;
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
      appBar: MhAppBar(
        title: 'Créer votre compte',
        showBell: false,
        onBack: _previous,
      ),
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const SizedBox(height: 8),
            _StepsIndicator(step: _step),
            if (_errorMessage != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 0),
                child: Text(
                  _errorMessage!,
                  style:
                      const TextStyle(color: AppColors.danger, fontSize: 13),
                  textAlign: TextAlign.center,
                ),
              ),
            Expanded(
              child: PageView(
                controller: _pageController,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  _stepPersonal(),
                  _stepCredentials(),
                  _stepVerification(),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 8),
              child: MhSolidButton(
                label: _step == 2 ? 'Créer mon compte' : 'Suivant',
                loading: _isLoading,
                onPressed: _next,
              ),
            ),
            const MhStripe(),
          ],
        ),
      ),
    );
  }

  // -----------------------------------------------------------------------
  // Étape 1 : informations personnelles
  // -----------------------------------------------------------------------
  Widget _stepPersonal() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Form(
        key: _formKeys[0],
        child: Column(
          children: [
            const SizedBox(height: 8),
            _buildTextField(
              controller: _nomController,
              label: 'Nom',
              hint: 'Votre nom',
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Requis' : null,
            ),
            const SizedBox(height: 12),
            _buildTextField(
              controller: _prenomController,
              label: 'Prénom',
              hint: 'Votre prénom',
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Requis' : null,
            ),
            const SizedBox(height: 12),
            _buildDateField(
              'Date de naissance',
              _dateNaissance,
              (d) => setState(() => _dateNaissance = d),
            ),
            const SizedBox(height: 12),
            _buildSexeField(),
            const SizedBox(height: 12),
            _buildPhoneField(
              controller: _phoneController,
              countryCode: _phoneCountryCode,
              onCountryChanged: (c) =>
                  setState(() => _phoneCountryCode = c),
              label: 'Numéro de téléphone',
              isRequired: true,
            ),
            const SizedBox(height: 12),
            _buildPhoneField(
              controller: _whatsappController,
              countryCode: _whatsappCountryCode,
              onCountryChanged: (c) =>
                  setState(() => _whatsappCountryCode = c),
              label: 'Numéro whatsapp si différent',
              isRequired: false,
            ),
            const SizedBox(height: 12),
            _buildSearchableCountryPicker(
              'Pays de résidence',
              _paysResidence,
              (v) => setState(() => _paysResidence = v),
              hint: 'Sélectionnez votre pays',
            ),
            const SizedBox(height: 12),
            _buildSearchableCountryPicker(
              'Nationalité',
              _nationalite,
              (v) => setState(() => _nationalite = v),
              hint: 'Sélectionnez votre nationalité',
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  // -----------------------------------------------------------------------
  // Étape 2 : identifiants de connexion
  // -----------------------------------------------------------------------
  Widget _stepCredentials() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Form(
        key: _formKeys[1],
        child: Column(
          children: [
            const SizedBox(height: 8),
            Text(
              'Votre adresse e-mail servira d’identifiant.',
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                  fontSize: 13, color: AppColors.mutedText),
            ),
            const SizedBox(height: 16),
            _buildTextField(
              controller: _emailController,
              label: 'Adresse e-mail',
              hint: 'votre@email.com',
              keyboardType: TextInputType.emailAddress,
              validator: (v) {
                if (v == null || v.trim().isEmpty) return 'Requis';
                if (!RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$')
                    .hasMatch(v)) {
                  return 'Email invalide';
                }
                return null;
              },
            ),
            const SizedBox(height: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const MhFieldLabel('Mot de passe'),
                TextFormField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  validator: (v) {
                    if (v == null || v.isEmpty) return 'Requis';
                    if (v.length < 8) return 'Minimum 8 caractères';
                    return null;
                  },
                  decoration: MHSurfaceCard.input(
                    hintText: 'Votre mot de passe',
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword
                            ? Icons.visibility_off
                            : Icons.visibility,
                        color: AppColors.mutedText,
                      ),
                      onPressed: () => setState(
                          () => _obscurePassword = !_obscurePassword),
                    ),
                  ),
                  enabled: !_isLoading,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const MhFieldLabel('Confirmer le mot de passe'),
                TextFormField(
                  controller: _confirmPasswordController,
                  obscureText: _obscureConfirmPassword,
                  validator: (v) {
                    if (v == null || v.isEmpty) return 'Requis';
                    if (v != _passwordController.text) {
                      return 'Les mots de passe ne correspondent pas';
                    }
                    return null;
                  },
                  decoration: MHSurfaceCard.input(
                    hintText: 'Votre mot de passe',
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscureConfirmPassword
                            ? Icons.visibility_off
                            : Icons.visibility,
                        color: AppColors.mutedText,
                      ),
                      onPressed: () => setState(() =>
                          _obscureConfirmPassword = !_obscureConfirmPassword),
                    ),
                  ),
                  enabled: !_isLoading,
                ),
              ],
            ),
            const SizedBox(height: 12),
            _buildTextField(
              controller: _contactUrgenceController,
              label: 'Personne à contacter en cas d’urgence',
              hint: 'Ex. +242 05 123 45 67',
              keyboardType: TextInputType.phone,
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  // -----------------------------------------------------------------------
  // Étape 3 : canal de vérification + consentements
  // -----------------------------------------------------------------------
  Widget _stepVerification() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Form(
        key: _formKeys[2],
        child: Column(
          children: [
            const SizedBox(height: 8),
            Text(
              'Choisissez comment recevoir votre code de vérification.',
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                  fontSize: 13, color: AppColors.mutedText),
            ),
            const SizedBox(height: 16),
            _canalTile(
              'email',
              Icons.mail_outline,
              'E-mail',
              _emailController.text.trim().isEmpty
                  ? 'Votre adresse e-mail'
                  : _emailController.text.trim(),
            ),
            _canalTile(
              'sms',
              Icons.sms_outlined,
              'SMS',
              _phoneController.text.trim().isEmpty
                  ? 'Vers votre numéro de téléphone'
                  : 'Vers ${_phoneCountryCode.dialCode ?? ''}${_phoneController.text.trim()}',
            ),
            _canalTile(
              'whatsapp',
              Icons.chat_outlined,
              'WhatsApp',
              _whatsappController.text.trim().isNotEmpty
                  ? 'Vers ${_whatsappCountryCode.dialCode ?? ''}${_whatsappController.text.trim()}'
                  : _phoneController.text.trim().isEmpty
                      ? 'Vers votre numéro de téléphone'
                      : 'Vers ${_phoneCountryCode.dialCode ?? ''}${_phoneController.text.trim()}',
            ),
            const SizedBox(height: 16),
            MHSurfaceCard(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Consentements *',
                    style: GoogleFonts.poppins(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: AppColors.secondary,
                    ),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    value: _consentCgu,
                    onChanged: _isLoading
                        ? null
                        : (v) =>
                            setState(() => _consentCgu = v ?? false),
                    title: Text(
                      "J'accepte les conditions générales d'utilisation (CGU).",
                      style: GoogleFonts.poppins(
                          fontSize: 13, color: AppColors.secondary),
                    ),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    value: _consentConfidentialite,
                    onChanged: _isLoading
                        ? null
                        : (v) => setState(
                            () => _consentConfidentialite = v ?? false),
                    title: Text(
                      "J'accepte la politique de confidentialité.",
                      style: GoogleFonts.poppins(
                          fontSize: 13, color: AppColors.secondary),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('Déjà un compte ? ',
                    style: GoogleFonts.poppins(
                        color: AppColors.mutedText, fontSize: 13)),
                GestureDetector(
                  onTap: () => context.go('/login'),
                  child: Text(
                    'Se connecter',
                    style: GoogleFonts.poppins(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _canalTile(
    String value,
    IconData icon,
    String label,
    String subtitle, {
    bool enabled = true,
  }) {
    final selected = _canalVerification == value;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Opacity(
        opacity: enabled ? 1 : 0.55,
        child: InkWell(
          onTap: enabled
              ? () => setState(() => _canalVerification = value)
              : null,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: selected ? const Color(0xFFE9F9F6) : Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: selected
                    ? AppColors.brandTeal
                    : const Color(0xFFE8E2F0),
                width: selected ? 1.6 : 1,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  icon,
                  color: selected
                      ? const Color(0xFF087F72)
                      : AppColors.secondary,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        label,
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          color: selected
                              ? const Color(0xFF087F72)
                              : AppColors.secondary,
                        ),
                      ),
                      Text(
                        subtitle,
                        style: const TextStyle(
                            fontSize: 11, color: AppColors.mutedText),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                Icon(
                  selected
                      ? Icons.radio_button_checked
                      : Icons.radio_button_off,
                  color: selected
                      ? AppColors.brandTeal
                      : AppColors.mutedText,
                  size: 20,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // -----------------------------------------------------------------------
  // Champs communs
  // -----------------------------------------------------------------------
  /// Libellé au-dessus de la boîte + placeholder dans le champ (style kit).
  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    String? hint,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MhFieldLabel(label),
        TextFormField(
          controller: controller,
          keyboardType: keyboardType,
          validator: validator,
          decoration: MHSurfaceCard.input(hintText: hint),
          enabled: !_isLoading,
        ),
      ],
    );
  }

  Widget _buildDateField(
      String label, DateTime? value, void Function(DateTime?) onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MhFieldLabel(label),
        InkWell(
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
              suffixIcon: const Icon(Icons.calendar_today),
            ),
            child: Text(
              value != null
                  ? '${value.day.toString().padLeft(2, '0')}/${value.month.toString().padLeft(2, '0')}/${value.year}'
                  : 'JJ / MM / AAAA',
              style: TextStyle(
                  color:
                      value != null ? Colors.black87 : AppColors.mutedText),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSexeField() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const MhFieldLabel('Genre'),
        DropdownButtonFormField<String>(
          initialValue: _sexe.isEmpty ? null : _sexe,
          decoration: MHSurfaceCard.input(),
          hint: const Text('Sélectionnez votre genre'),
      items: const [
        DropdownMenuItem(value: 'M', child: Text('Homme')),
        DropdownMenuItem(value: 'F', child: Text('Femme')),
        DropdownMenuItem(value: 'Autre', child: Text('Autre')),
      ],
          onChanged:
              _isLoading ? null : (v) => setState(() => _sexe = v ?? ''),
          validator: (_) => _sexe.isEmpty ? 'Requis' : null,
        ),
      ],
    );
  }

  Widget _buildSearchableCountryPicker(
      String label, String? value, void Function(String?) onChanged,
      {String hint = 'Sélectionnez votre pays'}) {
    final displayValue = _countryLabelFromCode(value);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MhFieldLabel(label),
        InkWell(
          onTap: (_isLoading || _loadingReferenceCountries)
              ? null
              : () async {
                  final selected =
                      await _showCountrySearchDialog(label, value);
                  if (selected != null && mounted) onChanged(selected);
                },
          borderRadius: BorderRadius.circular(8),
          child: InputDecorator(
            decoration: MHSurfaceCard.input(
              suffixIcon: const Icon(Icons.keyboard_arrow_down,
                  color: AppColors.mutedText),
            ),
            child: Text(
              _loadingReferenceCountries
                  ? 'Chargement...'
                  : (displayValue ?? hint),
              style: TextStyle(
                color: displayValue != null
                    ? Colors.black87
                    : AppColors.mutedText,
                fontSize: 15,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
      ],
    );
  }

  Future<String?> _showCountrySearchDialog(String label, String? currentValue) {
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

  /// Téléphone : une seule boîte « drapeau +242 | Votre numéro » comme le kit.
  Widget _buildPhoneField({
    required TextEditingController controller,
    required CountryCode countryCode,
    required void Function(CountryCode) onCountryChanged,
    required String label,
    required bool isRequired,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MhFieldLabel(label),
        Container(
          decoration: BoxDecoration(
            color: AppColors.surfaceFieldFill,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: AppColors.surfaceFieldBorder),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              CountryCodePicker(
                padding: EdgeInsets.zero,
                onChanged: onCountryChanged,
                initialSelection: countryCode.code ?? 'CG',
                favorite: const ['+242', 'CG', '+33', 'FR', '+221', 'SN'],
                showCountryOnly: false,
                showOnlyCountryWhenClosed: false,
                alignLeft: false,
                textStyle: const TextStyle(fontSize: 15),
                dialogTextStyle: const TextStyle(fontSize: 15),
                searchDecoration: const InputDecoration(
                    hintText: 'Rechercher un pays',
                    border: OutlineInputBorder()),
              ),
              Container(
                width: 1,
                height: 24,
                color: AppColors.surfaceFieldBorder,
              ),
              Expanded(
                child: TextFormField(
                  controller: controller,
                  keyboardType: TextInputType.phone,
                  validator: isRequired
                      ? (v) => (v == null || v.trim().isEmpty)
                          ? 'Requis'
                          : null
                      : null,
                  decoration: const InputDecoration(
                    hintText: 'Votre numéro',
                    hintStyle: TextStyle(color: AppColors.mutedText),
                    border: InputBorder.none,
                    contentPadding:
                        EdgeInsets.symmetric(horizontal: 12, vertical: 14),
                  ),
                  enabled: !_isLoading,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Indicateur 3 étapes du kit (cercles numérotés reliés, violet actif).
class _StepsIndicator extends StatelessWidget {
  const _StepsIndicator({required this.step});

  final int step;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 60, vertical: 8),
      child: Row(
        children: List.generate(5, (i) {
          if (i.isOdd) {
            return Expanded(
              child: Container(
                height: 2,
                color: (i ~/ 2) < step
                    ? AppColors.brandPurple
                    : const Color(0xFFDCD4E9),
              ),
            );
          }
          final index = i ~/ 2;
          final active = index == step;
          final done = index < step;
          return Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: done || active
                  ? AppColors.brandPurple
                  : const Color(0xFFEEEAF5),
            ),
            child: Center(
              child: done
                  ? const Icon(Icons.check, color: Colors.white, size: 15)
                  : Text(
                      '${index + 1}',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: active
                            ? Colors.white
                            : AppColors.brandPurple,
                      ),
                    ),
            ),
          );
        }),
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
              .where((country) =>
                  country.nom.toLowerCase().contains(normalizedQuery))
              .toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.label)),
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
                        child: Text('Aucun résultat',
                            style: TextStyle(color: Color(0xFF64748B))))
                    : ListView.builder(
                        itemCount: _filteredList.length,
                        itemBuilder: (_, i) {
                          final country = _filteredList[i];
                          return ListTile(
                            title: Text(country.nom),
                            subtitle: Text(country.code),
                            selected: country.code == widget.currentValue,
                            onTap: () =>
                                Navigator.of(context).pop(country.code),
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
