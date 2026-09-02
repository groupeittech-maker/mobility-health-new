import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/constants/app_colors.dart';
import '../core/widgets/mh_logo_header.dart';
import '../core/widgets/mh_surface_card.dart';
import '../services/auth_service.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final AuthService _auth = AuthService.instance;
  final TextEditingController _identifierController = TextEditingController();
  final TextEditingController _codeController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();

  int _currentStep = 1;
  bool _loading = false;
  String? _errorMessage;
  String? _successMessage;
  String? _maskedEmail;
  String _resetEmail = '';
  String _resetToken = '';
  int _remainingTime = 600;
  int? _remainingAttempts;
  Timer? _timer;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void dispose() {
    _timer?.cancel();
    _identifierController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _handleIdentifierStep() async {
    final value = _identifierController.text.trim();
    if (value.isEmpty) {
      _setError('Veuillez saisir votre email ou nom d\'utilisateur');
      return;
    }

    _setLoading(true);
    _clearMessages();
    try {
      final lookup = await _auth.getMaskedEmail(value);
      final exists = lookup['exists'] == true;
      final email = lookup['email']?.toString() ?? '';
      final masked = lookup['masked_email']?.toString();

      if (!exists || email.isEmpty) {
        throw Exception('Cet email n\'existe pas dans le systeme.');
      }

      _resetEmail = email;
      _maskedEmail = masked ?? _maskEmail(email);

      await _sendResetCode(showSentMessage: true);
    } catch (e) {
      _setError(_cleanException(e));
    } finally {
      _setLoading(false);
    }
  }

  Future<void> _sendResetCode({bool showSentMessage = false}) async {
    try {
      final response = await _auth.requestPasswordReset(_resetEmail);

      _remainingAttempts = null;
      _startTimer();
      _goToStep(2);

      if (showSentMessage) {
        final alreadySent = response['code_already_sent'] == true;
        _setSuccess(
          alreadySent
              ? 'Un code est deja actif. Veuillez verifier votre boite mail.'
              : 'Code de reinitialisation envoye par email.',
        );
      }
    } catch (e) {
      final message = _cleanException(e);
      if (message.toLowerCase().contains('trop de tentatives')) {
        _setError(message);
        _remainingTime = 0;
      } else {
        rethrow;
      }
    }
  }

  Future<void> _handleVerifyCodeStep() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) {
      _setError('Veuillez saisir le code recu par email');
      return;
    }

    if (_resetEmail.isEmpty) {
      _setError('Veuillez recommencer la procedure de reinitialisation');
      _goToStep(1);
      return;
    }

    _setLoading(true);
    _clearMessages();
    try {
      _resetToken = await _auth.verifyResetCode(
        email: _resetEmail,
        code: code,
      );
      _timer?.cancel();
      _remainingAttempts = null;
      _setSuccess('Code verifie avec succes.');
      _goToStep(3);
    } catch (e) {
      final message = _cleanException(e);
      _updateRemainingAttempts(message);
      _setError(message);
    } finally {
      _setLoading(false);
    }
  }

  Future<void> _handleResetPasswordStep() async {
    final password = _passwordController.text;
    final confirmPassword = _confirmPasswordController.text;

    if (password != confirmPassword) {
      _setError('Les mots de passe ne correspondent pas');
      return;
    }
    if (password.length < 8) {
      _setError('Le mot de passe doit contenir au moins 8 caracteres');
      return;
    }
    if (_resetEmail.isEmpty || _resetToken.isEmpty) {
      _setError('Veuillez d\'abord verifier le code de reinitialisation');
      _goToStep(2);
      return;
    }

    _setLoading(true);
    _clearMessages();
    try {
      await _auth.resetPassword(
        email: _resetEmail,
        token: _resetToken,
        newPassword: password,
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Mot de passe reinitialise avec succes.'),
          backgroundColor: AppColors.success,
        ),
      );

      final encodedEmail = Uri.encodeComponent(_resetEmail);
      context.go('/login?password_reset=1&username=$encodedEmail');
    } catch (e) {
      _setError(_cleanException(e));
    } finally {
      _setLoading(false);
    }
  }

  void _goToStep(int step) {
    if (!mounted) return;
    setState(() {
      _currentStep = step;
      _errorMessage = null;
      _successMessage = null;
    });
  }

  void _startTimer() {
    _timer?.cancel();
    _remainingTime = 600;
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_remainingTime <= 0) {
        timer.cancel();
        setState(() => _remainingTime = 0);
        return;
      }
      setState(() => _remainingTime -= 1);
    });
  }

  void _setLoading(bool value) {
    if (!mounted) return;
    setState(() => _loading = value);
  }

  void _setError(String message) {
    if (!mounted) return;
    setState(() {
      _errorMessage = message;
      _successMessage = null;
    });
  }

  void _setSuccess(String message) {
    if (!mounted) return;
    setState(() {
      _successMessage = message;
      _errorMessage = null;
    });
  }

  void _clearMessages() {
    if (!mounted) return;
    setState(() {
      _errorMessage = null;
      _successMessage = null;
    });
  }

  void _updateRemainingAttempts(String message) {
    final match = RegExp(r'(\d+)\s+tentative').firstMatch(message);
    if (match == null) return;
    final value = int.tryParse(match.group(1) ?? '');
    if (!mounted) return;
    setState(() => _remainingAttempts = value);
  }

  String _cleanException(Object error) {
    return error.toString().replaceFirst('Exception: ', '');
  }

  String _maskEmail(String email) {
    final parts = email.split('@');
    if (parts.length != 2) return '***@***';
    final local = parts[0];
    final domain = parts[1];
    final maskedLocal = local.length > 2 ? '${local.substring(0, 2)}***' : '***';
    return '$maskedLocal@$domain';
  }

  String _formatTime(int seconds) {
    final minutes = (seconds ~/ 60).toString().padLeft(2, '0');
    final secs = (seconds % 60).toString().padLeft(2, '0');
    return '$minutes:$secs';
  }

  _PasswordStrength _checkPasswordStrength(String password) {
    if (password.isEmpty) return const _PasswordStrength('', AppColors.mutedText);

    var score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (RegExp(r'[a-z]').hasMatch(password)) score++;
    if (RegExp(r'[A-Z]').hasMatch(password)) score++;
    if (RegExp(r'[0-9]').hasMatch(password)) score++;
    if (RegExp(r'[^A-Za-z0-9]').hasMatch(password)) score++;

    if (score <= 2) {
      return const _PasswordStrength('Faible', AppColors.danger);
    }
    if (score <= 4) {
      return const _PasswordStrength('Moyen', AppColors.warning);
    }
    return const _PasswordStrength('Fort', AppColors.success);
  }

  @override
  Widget build(BuildContext context) {
    final strength = _checkPasswordStrength(_passwordController.text);
    final passwordsMatch = _confirmPasswordController.text.isEmpty
        ? null
        : _passwordController.text == _confirmPasswordController.text;

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        backgroundColor: AppColors.cardBg,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: AppColors.primary),
          onPressed: _loading ? null : () => context.pop(),
        ),
        title: Text(
          'Mot de passe oublie',
          style: GoogleFonts.poppins(
            fontWeight: FontWeight.w600,
            color: AppColors.primary,
          ),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const MHLogoHeader(height: 100, compact: true),
              const SizedBox(height: 24),
              Text(
                'Reinitialisation du mot de passe',
                textAlign: TextAlign.center,
                style: GoogleFonts.poppins(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: AppColors.secondary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Suivez les 3 etapes pour recevoir un code, le verifier, puis definir un nouveau mot de passe.',
                textAlign: TextAlign.center,
                style: GoogleFonts.poppins(
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                  color: AppColors.secondary,
                ),
              ),
              const SizedBox(height: 24),
              _buildStepIndicators(),
              const SizedBox(height: 24),
              if (_errorMessage != null) _buildBanner(_errorMessage!, AppColors.danger),
              if (_successMessage != null)
                _buildBanner(_successMessage!, AppColors.success),
              if (_errorMessage != null || _successMessage != null)
                const SizedBox(height: 16),
              _buildStepCard(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  child: switch (_currentStep) {
                    1 => _buildStepOne(),
                    2 => _buildStepTwo(),
                    _ => _buildStepThree(strength, passwordsMatch),
                  },
                ),
              ),
              const SizedBox(height: 16),
              TextButton(
                onPressed: _loading ? null : () => context.go('/login'),
                child: Text(
                  'Retour a la connexion',
                  style: GoogleFonts.poppins(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStepIndicators() {
    return Row(
      children: [
        _StepIndicator(number: 1, label: 'Email', active: _currentStep == 1),
        const SizedBox(width: 8),
        _StepIndicator(number: 2, label: 'Code', active: _currentStep == 2),
        const SizedBox(width: 8),
        _StepIndicator(number: 3, label: 'Nouveau mot de passe', active: _currentStep == 3),
      ],
    );
  }

  Widget _buildStepCard({required Widget child}) {
    return MHSurfaceCard(
      padding: const EdgeInsets.all(20),
      child: child,
    );
  }

  Widget _buildStepOne() {
    return Column(
      key: const ValueKey(1),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _sectionTitle('Etape 1', 'Identifiez votre compte'),
        const SizedBox(height: 12),
        _buildTextField(
          controller: _identifierController,
          label: 'Email ou nom d\'utilisateur',
          enabled: !_loading,
          keyboardType: TextInputType.emailAddress,
        ),
        const SizedBox(height: 12),
        Text(
          'Nous verifierons le compte puis enverrons un code de reinitialisation a l\'adresse email associee.',
          style: GoogleFonts.poppins(
            fontSize: 12,
            color: AppColors.mutedText,
          ),
        ),
        const SizedBox(height: 20),
        _buildPrimaryButton(
          label: _loading ? 'Verification...' : 'Envoyer le code',
          onPressed: _loading ? null : _handleIdentifierStep,
        ),
      ],
    );
  }

  Widget _buildStepTwo() {
    final timerColor =
        _remainingTime < 60 ? AppColors.warning : AppColors.mutedText;

    return Column(
      key: const ValueKey(2),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _sectionTitle('Etape 2', 'Verifier le code recu'),
        const SizedBox(height: 12),
        if (_maskedEmail != null)
          _infoLine('Code envoye a : $_maskedEmail'),
        if (_remainingTime > 0) ...[
          const SizedBox(height: 8),
          Text(
            'Temps restant : ${_formatTime(_remainingTime)}',
            style: GoogleFonts.poppins(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: timerColor,
            ),
          ),
        ],
        if (_remainingAttempts != null) ...[
          const SizedBox(height: 8),
          Text(
            'Tentatives restantes : $_remainingAttempts',
            style: GoogleFonts.poppins(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.warning,
            ),
          ),
        ],
        const SizedBox(height: 12),
        _buildTextField(
          controller: _codeController,
          label: 'Code a 6 chiffres',
          enabled: !_loading,
          keyboardType: TextInputType.number,
          onChanged: (value) {
            final digitsOnly = value.replaceAll(RegExp(r'[^0-9]'), '');
            if (digitsOnly == value) return;
            _codeController.value = TextEditingValue(
              text: digitsOnly,
              selection: TextSelection.collapsed(offset: digitsOnly.length),
            );
          },
        ),
        const SizedBox(height: 20),
        _buildPrimaryButton(
          label: _loading ? 'Verification...' : 'Verifier le code',
          onPressed: _loading ? null : _handleVerifyCodeStep,
        ),
        const SizedBox(height: 12),
        OutlinedButton(
          onPressed: _loading || _resetEmail.isEmpty ? null : () async {
            _setLoading(true);
            _clearMessages();
            try {
              await _sendResetCode(showSentMessage: true);
            } catch (e) {
              _setError(_cleanException(e));
            } finally {
              _setLoading(false);
            }
          },
          child: Text(
            'Renvoyer le code',
            style: GoogleFonts.poppins(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }

  Widget _buildStepThree(
    _PasswordStrength strength,
    bool? passwordsMatch,
  ) {
    return Column(
      key: const ValueKey(3),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _sectionTitle('Etape 3', 'Choisir un nouveau mot de passe'),
        const SizedBox(height: 12),
        _buildPasswordField(
          controller: _passwordController,
          label: 'Nouveau mot de passe',
          obscureText: _obscurePassword,
          onToggleVisibility: () {
            setState(() => _obscurePassword = !_obscurePassword);
          },
        ),
        const SizedBox(height: 8),
        Text(
          strength.label.isEmpty ? '' : 'Force : ${strength.label}',
          style: GoogleFonts.poppins(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: strength.color,
          ),
        ),
        const SizedBox(height: 12),
        _buildPasswordField(
          controller: _confirmPasswordController,
          label: 'Confirmer le mot de passe',
          obscureText: _obscureConfirmPassword,
          onToggleVisibility: () {
            setState(
              () => _obscureConfirmPassword = !_obscureConfirmPassword,
            );
          },
        ),
        if (passwordsMatch != null) ...[
          const SizedBox(height: 8),
          Text(
            passwordsMatch
                ? 'Les mots de passe correspondent.'
                : 'Les mots de passe ne correspondent pas.',
            style: GoogleFonts.poppins(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: passwordsMatch ? AppColors.success : AppColors.danger,
            ),
          ),
        ],
        const SizedBox(height: 20),
        _buildPrimaryButton(
          label: _loading
              ? 'Reinitialisation...'
              : 'Reinitialiser le mot de passe',
          onPressed: _loading ? null : _handleResetPasswordStep,
        ),
      ],
    );
  }

  Widget _buildPrimaryButton({
    required String label,
    required VoidCallback? onPressed,
  }) {
    return SizedBox(
      height: 52,
      child: FilledButton(
        onPressed: onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
        child: _loading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : Text(
                label,
                style: GoogleFonts.poppins(fontWeight: FontWeight.w600),
              ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required bool enabled,
    TextInputType? keyboardType,
    ValueChanged<String>? onChanged,
  }) {
    return TextField(
      controller: controller,
      enabled: enabled,
      keyboardType: keyboardType,
      onChanged: (_) {
        onChanged?.call(controller.text);
        if (_errorMessage != null || _successMessage != null) {
          _clearMessages();
        }
        if (mounted) setState(() {});
      },
      decoration: MHSurfaceCard.input(labelText: label),
    );
  }

  Widget _buildPasswordField({
    required TextEditingController controller,
    required String label,
    required bool obscureText,
    required VoidCallback onToggleVisibility,
  }) {
    return TextField(
      controller: controller,
      enabled: !_loading,
      obscureText: obscureText,
      onChanged: (_) {
        if (_errorMessage != null || _successMessage != null) {
          _clearMessages();
        }
        if (mounted) setState(() {});
      },
      decoration: MHSurfaceCard.input(
        labelText: label,
        suffixIcon: IconButton(
          onPressed: onToggleVisibility,
          icon: Icon(
            obscureText ? Icons.visibility_off : Icons.visibility,
            color: AppColors.mutedText,
          ),
        ),
      ),
    );
  }

  Widget _sectionTitle(String title, String subtitle) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: GoogleFonts.poppins(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            color: AppColors.secondary,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: GoogleFonts.poppins(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: AppColors.secondary,
          ),
        ),
      ],
    );
  }

  Widget _buildBanner(String text, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        text,
        style: GoogleFonts.poppins(
          fontSize: 13,
          fontWeight: FontWeight.w500,
          color: color,
        ),
      ),
    );
  }

  Widget _infoLine(String text) {
    return Text(
      text,
      style: GoogleFonts.poppins(
        fontSize: 12,
        color: AppColors.mutedText,
      ),
    );
  }
}

class _StepIndicator extends StatelessWidget {
  const _StepIndicator({
    required this.number,
    required this.label,
    required this.active,
  });

  final int number;
  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final color = active ? AppColors.primary : const Color(0xFFCBD5E1);
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          color: active
              ? AppColors.primary.withValues(alpha: 0.12)
              : const Color(0xFFF8FAFC),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color),
        ),
        child: Column(
          children: [
            CircleAvatar(
              radius: 14,
              backgroundColor: color,
              child: Text(
                '$number',
                style: GoogleFonts.poppins(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              label,
              textAlign: TextAlign.center,
              style: GoogleFonts.poppins(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: active ? AppColors.primary : AppColors.mutedText,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PasswordStrength {
  const _PasswordStrength(this.label, this.color);

  final String label;
  final Color color;
}
