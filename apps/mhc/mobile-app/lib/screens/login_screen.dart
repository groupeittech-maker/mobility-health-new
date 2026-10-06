import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants/app_colors.dart';
import '../core/utils/api_error_helper.dart';
import '../core/widgets/mh_kit_widgets.dart';
import '../core/widgets/mh_logo_header.dart';
import '../core/widgets/mh_stripe.dart';
import '../core/widgets/mh_surface_card.dart';
import '../providers/auth_provider.dart';
import '../services/referent_navigation.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _obscurePassword = true;
  String? _errorMessage;
  bool _queryHandled = false;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_queryHandled) return;

    final query = GoRouterState.of(context).uri.queryParameters;
    final usernameOrEmail = query['username'];
    final passwordResetDone = query['password_reset'] == '1';
    final verified = query['verified'] == '1';

    if (usernameOrEmail != null && usernameOrEmail.isNotEmpty) {
      _usernameController.text = usernameOrEmail;
    }

    if (verified) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('E-mail vérifié avec succès ! Vous pouvez vous connecter.'),
            backgroundColor: AppColors.success,
          ),
        );
      });
    }

    if (passwordResetDone) {
      _errorMessage = null;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Mot de passe reinitialise. Vous pouvez vous connecter.'),
            backgroundColor: AppColors.success,
          ),
        );
      });
    }

    _queryHandled = true;
  }

  Future<void> _handleLogin() async {
    final auth = context.read<AuthProvider>();
    if (auth.loading) return;
    setState(() => _errorMessage = null);

    try {
      final user = await auth.login(
        _usernameController.text.trim(),
        _passwordController.text,
      );
      if (!mounted) return;
      if (user.isMedecinReferentMh) {
        context.go('/referent');
        WidgetsBinding.instance.addPostFrameCallback((_) {
          ReferentPendingDeepLink.tryConsumeAfterReferentLogin();
        });
      } else {
        ReferentPendingDeepLink.clear();
        context.go('/home');
      }
    } catch (e) {
      if (!mounted) return;
      final message = apiErrorToUserMessage(e);
      final email = _usernameController.text.trim();
      final isUnverifiedEmail = message.toLowerCase().contains('vérifi') ||
          message.toLowerCase().contains('verifie') ||
          message.toLowerCase().contains('verified');
      if (isUnverifiedEmail && email.contains('@')) {
        final goVerify = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('E-mail non vérifié'),
            content: const Text(
              'Votre adresse e-mail n\'a pas encore été vérifiée. Souhaitez-vous saisir le code de vérification ?',
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
              FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Vérifier')),
            ],
          ),
        );
        if (goVerify == true && mounted) {
          context.go('/verify-email?email=${Uri.encodeComponent(email)}');
          return;
        }
      }
      setState(() => _errorMessage = message);
    }
  }

  static final Uri _publicSiteUri = Uri.parse('https://mobilityhealth-care.com/');

  Future<void> _launchWebsite() async {
    if (await canLaunchUrl(_publicSiteUri)) {
      await launchUrl(_publicSiteUri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final loading = context.watch<AuthProvider>().loading;
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 8, 20, 0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    onPressed: () => context.go('/welcome'),
                    icon: const Icon(
                      Icons.arrow_back_ios_new,
                      size: 20,
                      color: AppColors.secondary,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      border: Border.all(color: const Color(0xFFD6CBE2)),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'FR',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: AppColors.secondary,
                          ),
                        ),
                        Icon(Icons.keyboard_arrow_down,
                            size: 16, color: AppColors.secondary),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 4),
            const MHLogoHeader(height: 56, compact: true),
            const SizedBox(height: 18),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Se connecter',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.poppins(
                          fontSize: 26,
                          fontWeight: FontWeight.bold,
                          color: AppColors.secondary,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Accédez à votre espace MyMHC\nen toute sécurité.',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.poppins(
                          fontSize: 13,
                          color: AppColors.mutedText,
                          height: 1.5,
                        ),
                      ),
                      const SizedBox(height: 20),
                      _buildUsernameField(loading),
                      const SizedBox(height: 14),
                      _buildPasswordField(loading),
                      if (_errorMessage != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          _errorMessage!,
                          style: const TextStyle(
                              color: Colors.red, fontSize: 14),
                          textAlign: TextAlign.center,
                        ),
                      ],
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: loading
                              ? null
                              : () => context.push('/forgot-password'),
                          child: Text(
                            'Mot de passe oublié ?',
                            style: GoogleFonts.poppins(
                              color: AppColors.brandTeal,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      MhSolidButton(
                        label: 'Se connecter',
                        onPressed: _handleLogin,
                        loading: loading,
                      ),
                      const SizedBox(height: 20),
                      const MhSocialLogin(),
                      const SizedBox(height: 18),
                      _buildProtectionCard(),
                      const SizedBox(height: 18),
                      _buildRegisterLink(loading),
                      const SizedBox(height: 10),
                      Center(
                        child: TextButton(
                          onPressed: _launchWebsite,
                          style: TextButton.styleFrom(
                            padding: EdgeInsets.zero,
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                          child: Text(
                            'mobilityhealth-care.com',
                            style: GoogleFonts.poppins(
                              fontSize: 12,
                              color: AppColors.primary,
                              fontWeight: FontWeight.w500,
                              decoration: TextDecoration.underline,
                              decorationColor: AppColors.primary,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Center(
                        child: Text(
                          'Your Health Has No Borders.',
                          style: TextStyle(
                            fontSize: 12,
                            color: AppColors.mutedText,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                  ),
                ),
              ),
            ),
            const MhStripe(),
          ],
        ),
      ),
    );
  }

  Widget _buildUsernameField(bool loading) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const MhFieldLabel('Adresse e-mail'),
        TextFormField(
          controller: _usernameController,
          keyboardType: TextInputType.emailAddress,
          decoration: MHSurfaceCard.input(
            hintText: 'votre@email.com',
            prefixIcon: const Icon(Icons.mail_outline,
                color: AppColors.mutedText, size: 20),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          ),
          textInputAction: TextInputAction.next,
          enabled: !loading,
        ),
        const SizedBox(height: 4),
        Text(
          'Voyageurs : e-mail. Administrateurs : nom d\'utilisateur.',
          style: GoogleFonts.poppins(fontSize: 11, color: AppColors.mutedText),
        ),
      ],
    );
  }

  Widget _buildPasswordField(bool loading) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const MhFieldLabel('Mot de passe'),
        TextFormField(
          controller: _passwordController,
          obscureText: _obscurePassword,
          decoration: MHSurfaceCard.input(
            hintText: 'Votre mot de passe',
            prefixIcon: const Icon(Icons.lock_outline,
                color: AppColors.mutedText, size: 20),
            suffixIcon: IconButton(
              icon: Icon(
                _obscurePassword ? Icons.visibility_off : Icons.visibility,
                color: AppColors.mutedText,
                size: 20,
              ),
              onPressed: () =>
                  setState(() => _obscurePassword = !_obscurePassword),
            ),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          ),
          textInputAction: TextInputAction.done,
          onFieldSubmitted: (_) => _handleLogin(),
          enabled: !loading,
        ),
      ],
    );
  }

  Widget _buildProtectionCard() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFF3EEF9),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.verified_user_outlined,
              color: AppColors.secondary, size: 26),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Vos données sont protégées',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppColors.secondary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Nous utilisons un chiffrement de niveau bancaire\n'
                  'pour sécuriser vos informations.',
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.grey.shade600,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRegisterLink(bool loading) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Flexible(
          child: Text(
            'Vous n\'avez pas encore de compte ?',
            style: GoogleFonts.poppins(
                color: Colors.black87, fontSize: 11.5),
          ),
        ),
        TextButton(
          onPressed: loading ? null : () => context.push('/register'),
          style: TextButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Créer un compte',
                style: GoogleFonts.poppins(
                  color: AppColors.brandTeal,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(width: 3),
              const Icon(Icons.arrow_forward,
                  size: 13, color: AppColors.brandTeal),
            ],
          ),
        ),
      ],
    );
  }
}
