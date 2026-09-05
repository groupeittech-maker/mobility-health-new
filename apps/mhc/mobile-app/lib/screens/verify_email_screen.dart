import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/constants/app_colors.dart';
import '../core/widgets/mh_logo_header.dart';
import '../core/widgets/mh_surface_card.dart';
import '../services/auth_service.dart';

/// Vérification du code OTP e-mail après inscription (aligné sur verify-email.html).
class VerifyEmailScreen extends StatefulWidget {
  const VerifyEmailScreen({super.key, required this.email});

  final String email;

  @override
  State<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends State<VerifyEmailScreen> {
  final _auth = AuthService.instance;
  final _codeController = TextEditingController();
  bool _loading = false;
  String? _errorMessage;
  int _resendCooldown = 60;
  Timer? _cooldownTimer;

  @override
  void initState() {
    super.initState();
    _startResendCooldown();
  }

  @override
  void dispose() {
    _cooldownTimer?.cancel();
    _codeController.dispose();
    super.dispose();
  }

  void _startResendCooldown([int seconds = 60]) {
    _cooldownTimer?.cancel();
    setState(() => _resendCooldown = seconds);
    _cooldownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_resendCooldown <= 1) {
        timer.cancel();
        setState(() => _resendCooldown = 0);
      } else {
        setState(() => _resendCooldown -= 1);
      }
    });
  }

  Future<void> _verify() async {
    final code = _codeController.text.trim();
    if (code.length != 6) {
      setState(() => _errorMessage = 'Le code doit contenir 6 chiffres');
      return;
    }
    setState(() {
      _errorMessage = null;
      _loading = true;
    });
    try {
      final result = await _auth.verifyEmail(email: widget.email, code: code);
      if (!mounted) return;
      final message = result['message']?.toString() ?? 'Compte activé. Vous pouvez vous connecter.';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message), backgroundColor: AppColors.success),
      );
      context.go(
        '/login?username=${Uri.encodeComponent(widget.email)}&verified=1',
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  Future<void> _resendCode() async {
    if (_resendCooldown > 0 || _loading) return;
    setState(() {
      _errorMessage = null;
      _loading = true;
    });
    try {
      await _auth.resendVerificationCode(widget.email);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Un nouveau code a été envoyé à votre adresse e-mail.'),
          backgroundColor: AppColors.success,
        ),
      );
      _startResendCooldown(60);
    } catch (e) {
      if (!mounted) return;
      setState(() => _errorMessage = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
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
          onPressed: () => context.go('/register'),
        ),
        title: Text(
          'Vérification e-mail',
          style: GoogleFonts.poppins(fontWeight: FontWeight.w600, color: AppColors.primary),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24),
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
                    Text(
                      'Activez votre compte',
                      style: GoogleFonts.poppins(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: AppColors.secondary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Saisissez le code à 6 chiffres envoyé à :',
                      style: GoogleFonts.poppins(fontSize: 14, color: AppColors.mutedText),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      widget.email,
                      style: GoogleFonts.poppins(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: AppColors.primary,
                      ),
                    ),
                    const SizedBox(height: 20),
                    TextFormField(
                      controller: _codeController,
                      keyboardType: TextInputType.number,
                      maxLength: 6,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 24, letterSpacing: 8, fontWeight: FontWeight.bold),
                      decoration: MHSurfaceCard.input(
                        labelText: 'Code de vérification *',
                      ).copyWith(counterText: ''),
                      enabled: !_loading,
                      onFieldSubmitted: (_) => _verify(),
                    ),
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
                        onPressed: _loading ? null : _verify,
                        style: FilledButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                        ),
                        child: _loading
                            ? const SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : Text('Vérifier', style: GoogleFonts.poppins(fontWeight: FontWeight.w600)),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Center(
                      child: TextButton(
                        onPressed: (_resendCooldown > 0 || _loading) ? null : _resendCode,
                        child: Text(
                          _resendCooldown > 0
                              ? 'Renvoyer le code (${_resendCooldown}s)'
                              : 'Renvoyer le code',
                          style: GoogleFonts.poppins(color: AppColors.primary, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}
