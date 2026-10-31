import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/constants/app_colors.dart';
import '../../core/widgets/mh_logo_header.dart';
import '../../core/widgets/mh_stripe.dart';
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
                builder: (context, _) {
                  return Stack(
                    alignment: Alignment.center,
                    children: [
                      Opacity(
                        opacity: 1.0 - _logo.value,
                        child: CustomPaint(
                          size: const Size(64, 96),
                          painter: _MhSymbolPainter(_symbol.value),
                        ),
                      ),
                      Opacity(
                        opacity: _logo.value,
                        // Le logo MyMHC contient déjà le nom — pas de doublon.
                        child: const MHOfficialLogo(height: 96),
                      ),
                    ],
                  );
                },
              ),
            ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 30,
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
            const Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: MhStripe(),
            ),
          ],
        ),
      ),
    );
  }
}

/// Les lignes du symbole MyMHC dessinées une à une (parallélogrammes inclinés
/// alternant violet et teal), remplacées ensuite par le logo PNG complet.
class _MhSymbolPainter extends CustomPainter {
  const _MhSymbolPainter(this.progress);

  final double progress;

  static const _colors = [
    AppColors.brandPurple,
    AppColors.brandTeal,
    AppColors.brandPurple,
    AppColors.brandTeal,
  ];

  @override
  void paint(Canvas canvas, Size size) {
    const barCount = 4;
    final barW = size.width / 6;
    final gap = size.width / 9;
    final paint = Paint()..isAntiAlias = true;
    for (var i = 0; i < barCount; i++) {
      // Chaque ligne apparaît en décalé, avec une légère translation verticale.
      final local = (progress * (barCount + 1) - i).clamp(0.0, 1.0);
      if (local <= 0) continue;
      final x = gap + i * (barW + gap * 0.55);
      final dy = (1 - local) * 16;
      paint.color = _colors[i].withValues(alpha: local);
      final top = 8.0 + dy;
      final bottom = size.height - 8.0 + dy;
      final slant = barW * 0.6;
      final path = Path()
        ..moveTo(x, bottom)
        ..lineTo(x + slant, top)
        ..lineTo(x + barW + slant, top)
        ..lineTo(x + barW, bottom)
        ..close();
      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(_MhSymbolPainter oldDelegate) =>
      oldDelegate.progress != progress;
}
