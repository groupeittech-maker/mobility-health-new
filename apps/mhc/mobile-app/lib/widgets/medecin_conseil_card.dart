import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants/app_colors.dart';
import '../models/medecin_conseil.dart';

/// Carte consultable hors ligne : coordonnées du médecin-conseil de destination.
class MedecinConseilCard extends StatelessWidget {
  const MedecinConseilCard({
    super.key,
    required this.assignments,
    this.fromCache = false,
    this.onCall,
    this.onEmail,
  });

  final List<MedecinConseilAssignment> assignments;
  final bool fromCache;
  final Future<void> Function(String telephone)? onCall;
  final Future<void> Function(String email)? onEmail;

  static Future<void> launchPhone(String telephone) async {
    final uri = Uri(scheme: 'tel', path: telephone);
    await launchUrl(uri);
  }

  static Future<void> launchEmail(String email) async {
    final uri = Uri(scheme: 'mailto', path: email);
    await launchUrl(uri);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (assignments.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(Icons.medical_information_outlined, color: AppColors.secondary.withValues(alpha: 0.8)),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Aucun médecin-conseil n’est encore associé à une destination de vos souscriptions.',
                  style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.mutedText),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Médecin-conseil',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w600,
            color: const Color(0xFF1E293B),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          fromCache
              ? 'Disponible hors ligne — coordonnées de la destination choisie à la souscription.'
              : 'Coordonnées du médecin-conseil de votre destination de voyage.',
          style: theme.textTheme.bodySmall?.copyWith(color: AppColors.mutedText),
        ),
        const SizedBox(height: 12),
        ...assignments.map((assignment) => _AssignmentTile(
              assignment: assignment,
              onCall: onCall ?? launchPhone,
              onEmail: onEmail ?? launchEmail,
            )),
      ],
    );
  }
}

class _AssignmentTile extends StatelessWidget {
  const _AssignmentTile({
    required this.assignment,
    required this.onCall,
    required this.onEmail,
  });

  final MedecinConseilAssignment assignment;
  final Future<void> Function(String telephone) onCall;
  final Future<void> Function(String email) onEmail;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final contact = assignment.medecinConseil;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: AppColors.secondary.withValues(alpha: 0.12),
                  child: const Icon(Icons.health_and_safety, color: AppColors.secondary),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        contact?.nom?.isNotEmpty == true ? contact!.nom! : 'Médecin-conseil non renseigné',
                        style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        assignment.destinationLabel,
                        style: theme.textTheme.bodySmall?.copyWith(color: AppColors.mutedText),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (assignment.hasContact) ...[
              const SizedBox(height: 12),
              if (contact?.telephone?.isNotEmpty == true)
                _ContactAction(
                  icon: Icons.phone,
                  label: contact!.telephone!,
                  onTap: () => onCall(contact.telephone!),
                ),
              if (contact?.email?.isNotEmpty == true)
                _ContactAction(
                  icon: Icons.email_outlined,
                  label: contact!.email!,
                  onTap: () => onEmail(contact.email!),
                ),
            ] else
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(
                  'Aucun contact n’est encore associé à cette destination.',
                  style: theme.textTheme.bodySmall?.copyWith(color: AppColors.mutedText),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ContactAction extends StatelessWidget {
  const _ContactAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Row(
            children: [
              Icon(icon, size: 20, color: AppColors.primary),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
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
}
