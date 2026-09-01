import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import 'login_screen.dart';
import 'products_screen.dart';
import 'subscriptions_screen.dart';
import 'profile_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _activeIndex = 0;

  static const _tabs = [
    _TabItem(Icons.dashboard_outlined, Icons.dashboard, 'Accueil'),
    _TabItem(Icons.shopping_bag_outlined, Icons.shopping_bag, 'Produits'),
    _TabItem(Icons.description_outlined, Icons.description, 'Souscriptions'),
    _TabItem(Icons.person_outline, Icons.person, 'Profil'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_tabs[_activeIndex].label),
        backgroundColor: Colors.teal,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () async {
              await context.read<AuthProvider>().logout();
              if (!context.mounted) return;
              Navigator.of(context).pushAndRemoveUntil(
                MaterialPageRoute(builder: (_) => const LoginScreen()),
                (_) => false,
              );
            },
          ),
        ],
      ),
      body: IndexedStack(
        index: _activeIndex,
        children: [
          _HomeTab(onTabSelected: (i) => setState(() => _activeIndex = i)),
          const ProductsScreen(),
          const SubscriptionsScreen(),
          const ProfileScreen(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _activeIndex,
        onDestinationSelected: (i) => setState(() => _activeIndex = i),
        destinations: _tabs
            .map((t) => NavigationDestination(
                  icon: Icon(t.outline),
                  selectedIcon: Icon(t.filled),
                  label: t.label,
                ))
            .toList(),
      ),
    );
  }
}

class _TabItem {
  final IconData outline, filled;
  final String label;
  const _TabItem(this.outline, this.filled, this.label);
}

class _HomeTab extends StatelessWidget {
  final void Function(int) onTabSelected;

  const _HomeTab({required this.onTabSelected});

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().currentUser;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Bienvenue, ${user?.displayName ?? "Utilisateur"}',
                    style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                Text('Rôle: ${user?.role ?? "user"}', style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey.shade700)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          childAspectRatio: 1.2,
          children: [
            _QuickCard(
              icon: Icons.shopping_bag,
              label: 'Voir les produits',
              color: Colors.teal,
              onTap: () => onTabSelected(1),
            ),
            _QuickCard(
              icon: Icons.description,
              label: 'Mes souscriptions',
              color: Colors.blue,
              onTap: () => onTabSelected(2),
            ),
            _QuickCard(
              icon: Icons.person,
              label: 'Mon profil',
              color: Colors.orange,
              onTap: () => onTabSelected(3),
            ),
          ],
        ),
      ],
    );
  }
}

class _QuickCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _QuickCard({required this.icon, required this.label, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 40, color: color),
              const SizedBox(height: 8),
              Text(label, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w500)),
            ],
          ),
        ),
      ),
    );
  }
}
