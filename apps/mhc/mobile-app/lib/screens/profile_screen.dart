import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().currentUser;
    if (user == null) {
      return const Center(child: Text('Non connecté'));
    }
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(user.displayName, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 4),
                Text(user.email, style: TextStyle(color: Colors.grey.shade700)),
                Text('@${user.username}', style: TextStyle(color: Colors.grey.shade600)),
                const SizedBox(height: 8),
                Chip(label: Text(user.role)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        if (user.telephone != null && user.telephone!.isNotEmpty)
          _InfoTile(icon: Icons.phone, label: 'Téléphone', value: user.telephone!),
        if (user.paysResidence != null && user.paysResidence!.isNotEmpty)
          _InfoTile(icon: Icons.location_on, label: 'Pays de résidence', value: user.paysResidence!),
        if (user.nationalite != null && user.nationalite!.isNotEmpty)
          _InfoTile(icon: Icons.flag, label: 'Nationalité', value: user.nationalite!),
        if (user.nomContactUrgence != null && user.nomContactUrgence!.isNotEmpty)
          _InfoTile(icon: Icons.emergency, label: 'Contact urgence', value: '${user.nomContactUrgence!} ${user.contactUrgence ?? ""}'.trim()),
      ],
    );
  }
}

class _InfoTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _InfoTile({required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(icon, color: Colors.teal),
        title: Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
        subtitle: Text(value),
      ),
    );
  }
}
