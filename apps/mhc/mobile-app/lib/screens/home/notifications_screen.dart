import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/mh_layout.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../services/api_services.dart';

/// « Notifications » (cloche du header) : approbation de police, rappels,
/// messages du médecin-conseil, alertes SOS, factures…
class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  final _service = NotificationsService();
  List<Map<String, dynamic>> _items = const [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _error = null;
      if (_items.isEmpty) _loading = true;
    });
    try {
      final list = await _service.getNotifications();
      if (!mounted) return;
      setState(() {
        _items = list;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = apiErrorToUserMessage(e);
        _loading = false;
      });
    }
  }

  IconData _iconForType(String type) {
    switch (type) {
      case 'souscription_validee':
      case 'subscription_approved':
      case 'police_approved':
      case 'attestation_generee':
        return Icons.verified_user_outlined;
      case 'questionnaire_reminder':
      case 'rappel_questionnaire':
        return Icons.assignment_late_outlined;
      case 'medecin_conseil':
      case 'medecin_conseil_message':
        return Icons.medical_services_outlined;
      case 'sos_alert_received':
      case 'sos_alert_hospital':
        return Icons.emergency_outlined;
      case 'invoice_received':
        return Icons.receipt_long_outlined;
      case 'paiement':
      case 'payment_received':
        return Icons.payments_outlined;
      default:
        return Icons.notifications_outlined;
    }
  }

  Future<void> _open(Map<String, dynamic> n) async {
    final id = n['id'];
    if (id is int && n['is_read'] != true) {
      try {
        await _service.markAsRead(id);
      } catch (_) {}
      if (mounted) {
        setState(() {
          _items = [
            for (final it in _items)
              if (it['id'] == id) {...it, 'is_read': true} else it
          ];
        });
      }
    }
    final alerteId = n['alerte_id'];
    if (alerteId is int && alerteId > 0 && mounted) {
      context.push('/referent/dossier/$alerteId');
    }
  }

  String _formatDate(dynamic raw) {
    final d = DateTime.tryParse(raw?.toString() ?? '');
    if (d == null) return '';
    final local = d.toLocal();
    return '${local.day.toString().padLeft(2, '0')}/${local.month.toString().padLeft(2, '0')}/${local.year} '
        '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Notifications'),
      body: ColoredBox(
        color: kMhContentBackground,
        child: _loading
            ? const MhLoadingView()
            : RefreshIndicator(
                onRefresh: _load,
                child: _error != null && _items.isEmpty
                    ? ListView(
                        padding: const EdgeInsets.all(24),
                        children: [
                          const SizedBox(height: 80),
                          Center(
                            child: Column(
                              children: [
                                Text(_error!,
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(
                                        color: AppColors.danger)),
                                const SizedBox(height: 12),
                                FilledButton(
                                  onPressed: _load,
                                  child: const Text('Réessayer'),
                                ),
                              ],
                            ),
                          ),
                        ],
                      )
                    : _items.isEmpty
                        ? ListView(
                            padding: const EdgeInsets.all(24),
                            children: const [
                              SizedBox(height: 90),
                              Icon(Icons.notifications_none,
                                  size: 64, color: AppColors.mutedText),
                              SizedBox(height: 12),
                              Center(
                                child: Text(
                                  'Aucune notification pour le moment.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                      color: AppColors.mutedText,
                                      fontSize: 14),
                                ),
                              ),
                            ],
                          )
                        : ListView.separated(
                            padding: EdgeInsets.fromLTRB(20, 16, 20, 32 + MediaQuery.of(context).padding.bottom),
                            itemCount: _items.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 10),
                            itemBuilder: (_, i) {
                              final n = _items[i];
                              final unread = n['is_read'] != true;
                              final type =
                                  (n['type_notification'] ?? '').toString();
                              return MHSurfaceCard(
                                padding: EdgeInsets.zero,
                                borderRadius: 14,
                                child: ListTile(
                                  contentPadding:
                                      const EdgeInsets.symmetric(
                                          horizontal: 14, vertical: 6),
                                  leading: CircleAvatar(
                                    backgroundColor: unread
                                        ? const Color(0xFFEDE9FE)
                                        : const Color(0xFFF1F5F9),
                                    child: Icon(
                                      _iconForType(type),
                                      color: unread
                                          ? AppColors.secondary
                                          : AppColors.mutedText,
                                      size: 20,
                                    ),
                                  ),
                                  title: Text(
                                    (n['titre'] ?? 'Notification').toString(),
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: unread
                                          ? FontWeight.w700
                                          : FontWeight.w500,
                                      color: const Color(0xFF1E293B),
                                    ),
                                  ),
                                  subtitle: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        (n['message'] ?? '').toString(),
                                        style: const TextStyle(
                                            fontSize: 12,
                                            color: AppColors.mutedText,
                                            height: 1.35),
                                        maxLines: 3,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        _formatDate(n['created_at']),
                                        style: const TextStyle(
                                            fontSize: 10,
                                            color: AppColors.mutedText),
                                      ),
                                    ],
                                  ),
                                  trailing: unread
                                      ? Container(
                                          width: 8,
                                          height: 8,
                                          decoration: const BoxDecoration(
                                            color: Color(0xFFF03E4D),
                                            shape: BoxShape.circle,
                                          ),
                                        )
                                      : null,
                                  onTap: () => _open(n),
                                ),
                              );
                            },
                          ),
              ),
      ),
    );
  }
}
