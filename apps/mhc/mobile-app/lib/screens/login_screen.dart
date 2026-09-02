import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants/app_colors.dart';
import '../core/theme/app_theme.dart';
import '../core/widgets/mh_logo_header.dart';
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
    final pendingEmailVerify = query['pending_email_verify'] == '1';

    if (usernameOrEmail != null && usernameOrEmail.isNotEmpty) {
      _usernameController.text = usernameOrEmail;
    }

    if (pendingEmailVerify) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Vérifiez votre boîte e-mail : après activation du compte sur le web (code à 6 chiffres), vous pourrez vous connecter ici.',
            ),
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
      setState(() => _errorMessage = e.toString().replaceFirst('Exception: ', ''));
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
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            physics: const NeverScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                const SizedBox(height: 24),
                _buildLogo(),
                const SizedBox(height: 24),
                Text(
                  'Connexion',
                  style: GoogleFonts.poppins(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    color: AppColors.secondary,
                  ),
                ),
                const SizedBox(height: 20),
                MHAuthCard(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _buildUsernameField(),
                      const SizedBox(height: 16),
                      _buildPasswordField(),
                      if (_errorMessage != null) ...[
                        const SizedBox(height: 12),
                        Text(
                          _errorMessage!,
                          style: const TextStyle(color: Colors.red, fontSize: 14),
                          textAlign: TextAlign.center,
                        ),
                      ],
                      const SizedBox(height: 6),
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: context.watch<AuthProvider>().loading
                              ? null
                              : () => context.push('/forgot-password'),
                          child: Text(
                            'Mot de passe oublié ?',
                            style: GoogleFonts.poppins(
                              color: AppColors.primary,
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 20),
                      _buildLoginButton(),
                      const SizedBox(height: 24),
                      _buildDivider(),
                      const SizedBox(height: 16),
                      _buildRegisterLink(),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: _launchWebsite,
                  child: Text(
                    'Retour à l\'accueil',
                    style: GoogleFonts.poppins(
                      color: AppColors.primary,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextButton(
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
                const SizedBox(height: 16),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLogo() {
    return const MHLogoHeader(height: 72);
  }

  Widget _buildUsernameField() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Nom d\'utilisateur ou Email',
          style: GoogleFonts.poppins(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: AppColors.secondary,
          ),
        ),
        const SizedBox(height: 8),
        TextFormField(
          controller: _usernameController,
          decoration: MHSurfaceCard.input(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          ),
          textInputAction: TextInputAction.next,
          enabled: !context.watch<AuthProvider>().loading,
        ),
      ],
    );
  }

  Widget _buildPasswordField() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Mot de passe',
          style: GoogleFonts.poppins(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: AppColors.secondary,
          ),
        ),
        const SizedBox(height: 8),
        TextFormField(
          controller: _passwordController,
          obscureText: _obscurePassword,
          decoration: MHSurfaceCard.input(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            suffixIcon: IconButton(
              icon: Icon(
                _obscurePassword ? Icons.visibility_off : Icons.visibility,
                color: AppColors.mutedText,
              ),
              onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
            ),
          ),
          textInputAction: TextInputAction.done,
          onFieldSubmitted: (_) => _handleLogin(),
          enabled: !context.watch<AuthProvider>().loading,
        ),
      ],
    );
  }

  Widget _buildLoginButton() {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [AppColors.secondary, AppColors.primary],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ),
          borderRadius: BorderRadius.circular(8),
          boxShadow: [
            BoxShadow(
              color: AppColors.secondary.withValues(alpha: 0.3),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: context.watch<AuthProvider>().loading ? null : _handleLogin,
            borderRadius: BorderRadius.circular(8),
            child: Center(
              child: context.watch<AuthProvider>().loading
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : Text(
                      'Se connecter',
                      style: GoogleFonts.poppins(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDivider() {
    return Row(
      children: [
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) => SizedBox(
              height: 1,
              width: constraints.maxWidth,
              child: CustomPaint(
                size: Size(constraints.maxWidth, 1),
                painter: _DashedLinePainter(),
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child:           Text(
            'ou',
            style: GoogleFonts.poppins(color: AppColors.mutedText, fontSize: 14),
          ),
        ),
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) => SizedBox(
              height: 1,
              width: constraints.maxWidth,
              child: CustomPaint(
                size: Size(constraints.maxWidth, 1),
                painter: _DashedLinePainter(),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRegisterLink() {
    return RichText(
      text: TextSpan(
        style: GoogleFonts.poppins(color: Colors.black87, fontSize: 14),
        children: [
          const TextSpan(text: 'Pas encore de compte ? '),
          WidgetSpan(
            alignment: PlaceholderAlignment.baseline,
            baseline: TextBaseline.alphabetic,
            child: GestureDetector(
              onTap: context.watch<AuthProvider>().loading
                  ? null
                  : () => context.push('/register'),
              child:                 Text(
                  'S\'inscrire',
                  style: GoogleFonts.poppins(
                    color: AppColors.primary,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
class _DashedLinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.mutedText.withValues(alpha: 0.5)
      ..strokeWidth = 1;
    const dashWidth = 5;
    const dashSpace = 4;
    double startX = 0;
    while (startX < size.width) {
      canvas.drawLine(
        Offset(startX, 0),
        Offset((startX + dashWidth).clamp(0, size.width), 0),
        paint,
      );
      startX += dashWidth + dashSpace;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

