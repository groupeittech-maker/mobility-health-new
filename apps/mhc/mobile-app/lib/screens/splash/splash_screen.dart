import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/widgets/mh_logo_header.dart';
import '../../providers/auth_provider.dart';
import '../../services/auth_service.dart';
import '../../services/referent_navigation.dart';

/// Écran de démarrage – logo officiel Mobility HealthCare sur fond wallpaper.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _fadeAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeIn),
    );
    _controller.forward();
    _navigateAfterDelay();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _navigateAfterDelay() async {
    await Future.delayed(const Duration(milliseconds: 2500));
    if (!mounted) return;
    final isLoggedIn = await AuthService.instance.isLoggedIn;
    if (!mounted) return;
    if (!isLoggedIn) {
      context.go('/login');
      return;
    }
    final auth = context.read<AuthProvider>();
    await auth.checkAuth();
    if (!mounted) return;
    if (!auth.isAuthenticated) {
      context.go('/login');
      return;
    }
    final user = auth.currentUser!;
    if (user.isMedecinReferentMh) {
      context.go('/referent');
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ReferentPendingDeepLink.tryConsumeAfterReferentLogin();
      });
    } else {
      ReferentPendingDeepLink.clear();
      context.go('/home');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: SafeArea(
        child: Center(
          child: AnimatedBuilder(
            animation: _fadeAnimation,
            builder: (context, child) {
              return Opacity(
                opacity: _fadeAnimation.value,
                child: child,
              );
            },
            child: const MHLogoHeader(height: 120, compact: true),
          ),
        ),
      ),
    );
  }
}
