import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/widgets/mh_logo_header.dart';
import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';
import '../../services/referent_navigation.dart';

/// Écran de démarrage – logo officiel Mobility HealthCare, fade + scale.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 900),
      vsync: this,
    );
    _fadeAnimation = CurvedAnimation(parent: _controller, curve: Curves.easeOut);
    _scaleAnimation = Tween<double>(begin: 0.78, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOutBack),
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
    await Future.wait([
      authFuture,
      Future.delayed(const Duration(milliseconds: 900)),
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
    if (!isLoggedIn) return '/login';
    if (!mounted) return '/login';
    final auth = context.read<AuthProvider>();
    await auth.checkAuth();
    if (!auth.isAuthenticated || auth.currentUser == null) return '/login';
    if (auth.currentUser!.isMedecinReferentMh) return '/referent';
    return '/home';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: Center(
          child: AnimatedBuilder(
            animation: _controller,
            builder: (context, child) {
              return Opacity(
                opacity: _fadeAnimation.value,
                child: Transform.scale(
                  scale: _scaleAnimation.value,
                  child: child,
                ),
              );
            },
            child: const MHLogoHeader(height: 72, compact: true),
          ),
        ),
      ),
    );
  }
}
