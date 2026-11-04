import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';
import '../../services/referent_navigation.dart';

/// Écran de démarrage animé (retour test) : les lignes du symbole apparaissent
/// une à une, puis le logo « MyMHC » monte en fondu, et la signature s'affiche
/// en petit juste au-dessus de la bande inférieure. Transitions douces, sans
/// rebond ni zoom excessif ; le paramètre système de réduction des animations
/// est respecté ; la navigation n'attend pas la fin de l'animation.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _symbol;
  late final Animation<double> _logo;
  late final Animation<double> _signature;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1400),
      vsync: this,
    );
    _symbol = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.0, 0.55, curve: Curves.easeOut),
    );
    _logo = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.45, 0.9, curve: Curves.easeOut),
    );
    _signature = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.75, 1.0, curve: Curves.easeOut),
    );
    _controller.forward();
    _navigateAfterReady();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _navigateAfterReady() async {
    final authFuture = _resolveDestination();
    // Petite borne basse anti-flash uniquement : la navigation ne doit pas
    // attendre la fin de l'animation.
    await Future.wait([
      authFuture,
      Future.delayed(const Duration(milliseconds: 500)),
    ]);
    if (!mounted) return;
    final dest = await authFuture;
    if (!mounted) return;
    context.go(dest);
    if (dest == '/referent') {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ReferentPendingDeepLink.tryConsumeAfterReferentLogin();
      });
    } else if (dest == '/home') {
      ReferentPendingDeepLink.clear();
    }
  }

  Future<String> _resolveDestination() async {
    final isLoggedIn = await AuthService.instance.isLoggedIn;
    if (!isLoggedIn) return '/welcome';
    if (!mounted) return '/welcome';
    final auth = context.read<AuthProvider>();
    await auth.checkAuth();
    if (!auth.isAuthenticated || auth.currentUser == null) return '/welcome';
    if (auth.currentUser!.isMedecinReferentMh) return '/referent';
    return '/home';
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.disableAnimationsOf(context);
    if (reduceMotion && _controller.value < 1) {
      _controller.value = 1;
    }
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        bottom: false,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Center(
              child: AnimatedBuilder(
                animation: _controller,
                builder: (context, _) => _AnimatedLogo(
                  symbol: _symbol.value,
                  wordmark: _logo.value,
                ),
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 40,
              child: FadeTransition(
                opacity: _signature,
                child: const Text(
                  'Strength for life.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 11,
                    fontStyle: FontStyle.italic,
                    letterSpacing: 0.4,
                    color: AppColors.mutedText,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Logo MyMHC officiel reconstitué : les 5 lignes du symbole (découpées du
/// visuel « Logo MyMHC » du kit) glissent une à une le long de leur diagonale,
/// puis le mot « MyMHC » apparaît en fondu à droite.
class _AnimatedLogo extends StatelessWidget {
  const _AnimatedLogo({required this.symbol, required this.wordmark});

  final double symbol;
  final double wordmark;

  static const double _h = 64;
  // Proportions du visuel source : symbole 658x657, écart 90, mot 1841x657.
  static const double _symbolW = _h * 658 / 657;
  static const double _gap = _h * 90 / 657;
  static const double _wordW = _h * 1841 / 657;
  static const int _lines = 5;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: _symbolW,
          height: _h,
          child: Stack(
            children: [
              for (var i = 0; i < _lines; i++)
                Builder(builder: (_) {
                  final t = Curves.easeOut.transform(
                    (symbol * (_lines + 1) / 2 - i * 0.5).clamp(0.0, 1.0),
                  );
                  return Opacity(
                    opacity: t,
                    child: Transform.translate(
                      offset: Offset(-6 * (1 - t), 10 * (1 - t)),
                      child: Image.asset(
                        'assets/images/splash_line_$i.png',
                        width: _symbolW,
                        height: _h,
                        fit: BoxFit.contain,
                      ),
                    ),
                  );
                }),
            ],
          ),
        ),
        const SizedBox(width: _gap),
        Opacity(
          opacity: wordmark,
          child: Image.asset(
            'assets/images/splash_wordmark.png',
            width: _wordW,
            height: _h,
            fit: BoxFit.contain,
          ),
        ),
      ],
    );
  }
}
