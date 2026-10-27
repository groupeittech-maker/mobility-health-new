import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../services/account_service.dart';

const _statutLabels = {
  'recue': 'Reçue',
  'en_analyse': 'En cours d\'analyse',
  'infos_requises': 'Informations requises',
  'traitee': 'Traitée',
  'cloturee': 'Clôturée',
};

Color _statutColor(String statut) {
  switch (statut) {
    case 'traitee':
    case 'cloturee':
      return AppColors.success;
    case 'infos_requises':
      return Colors.orange.shade700;
    case 'en_analyse':
      return AppColors.secondary;
    default:
      return AppColors.mutedText;
  }
}

/// Réclamations (workflow V3 §8.1) : liste, dépôt, suivi avec échanges,
/// contestation d'une décision.
class ReclamationsScreen extends StatefulWidget {
  const ReclamationsScreen({super.key});

  @override
  State<ReclamationsScreen> createState() => _ReclamationsScreenState();
}

class _ReclamationsScreenState extends State<ReclamationsScreen> {
  final _service = ReclamationsService.instance;
  List<Map<String, dynamic>> _items = [];
  Map<String, dynamic> _meta = const {};
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final results = await Future.wait<Object>([
        _service.myReclamations(),
        _service.metadata(),
      ]);
      if (mounted) {
        setState(() {
          _items = results[0] as List<Map<String, dynamic>>;
          _meta = results[1] as Map<String, dynamic>;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = apiErrorToUserMessage(e);
          _loading = false;
        });
      }
    }
  }

  List<Map<String, dynamic>> get _categories =>
      ((_meta['categories'] as List?) ?? const [])
          .whereType<Map<String, dynamic>>()
          .toList();

  Future<void> _openCreate() async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => _CreateReclamationScreen(categories: _categories)),
    );
    if (created == true) _load();
  }

  Future<void> _openDetail(Map<String, dynamic> item) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => _ReclamationDetailScreen(id: item['id'] as int)),
    );
    if (changed == true) _load();
  }

  String _date(dynamic v) {
    final d = DateTime.tryParse('${v ?? ''}');
    if (d == null) return '';
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    final urgence = _meta['urgence_medicale']?.toString();
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Réclamations'),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _categories.isEmpty ? null : _openCreate,
        backgroundColor: AppColors.secondary,
        icon: const Icon(Icons.add, color: Colors.white),
        label: const Text('Réclamer', style: TextStyle(color: Colors.white)),
      ),
      body: _loading
          ? const MhLoadingView()
          : _error != null
              ? MhOfflineView(onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(20, 16, 20, 96),
                    children: [
                      if (urgence != null && urgence.isNotEmpty)
                        Container(
                          margin: const EdgeInsets.only(bottom: 14),
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppColors.danger.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.emergency, color: AppColors.danger, size: 18),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'Urgence médicale : utilisez le bouton SOS, pas une réclamation. $urgence',
                                  style: const TextStyle(fontSize: 12, height: 1.4),
                                ),
                              ),
                            ],
                          ),
                        ),
                      if (_items.isEmpty)
                        const Padding(
                          padding: EdgeInsets.all(24),
                          child: Text(
                            'Aucune réclamation. Chaque demande reçoit une référence '
                            'et une réponse dans les délais annoncés.',
                            textAlign: TextAlign.center,
                            style: TextStyle(color: AppColors.mutedText, height: 1.5),
                          ),
                        )
                      else
                        ..._items.map((r) {
                          final statut = r['statut']?.toString() ?? '';
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: MHSurfaceCard(
                              child: ListTile(
                                onTap: () => _openDetail(r),
                                title: Text(
                                  r['objet']?.toString() ?? '',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w600, fontSize: 14),
                                ),
                                subtitle: Text(
                                  '${r['reference'] ?? ''} • ${_date(r['created_at'])}',
                                  style: const TextStyle(fontSize: 12),
                                ),
                                trailing: Text(
                                  _statutLabels[statut] ?? statut,
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: _statutColor(statut),
                                  ),
                                ),
                              ),
                            ),
                          );
                        }),
                    ],
                  ),
                ),
    );
  }
}

class _CreateReclamationScreen extends StatefulWidget {
  const _CreateReclamationScreen({required this.categories});

  final List<Map<String, dynamic>> categories;

  @override
  State<_CreateReclamationScreen> createState() => _CreateReclamationScreenState();
}

class _CreateReclamationScreenState extends State<_CreateReclamationScreen> {
  final _objetCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  String? _categorie;
  bool _sending = false;
  String? _error;

  @override
  void dispose() {
    _objetCtrl.dispose();
    _descCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_categorie == null || _objetCtrl.text.trim().isEmpty || _descCtrl.text.trim().isEmpty) {
      setState(() => _error = 'Catégorie, objet et description sont obligatoires.');
      return;
    }
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      await ReclamationsService.instance.create(
        categorie: _categorie!,
        objet: _objetCtrl.text,
        description: _descCtrl.text,
      );
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() {
          _sending = false;
          _error = apiErrorToUserMessage(e);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Nouvelle réclamation'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        children: [
          DropdownButtonFormField<String>(
            initialValue: _categorie,
            decoration: MHSurfaceCard.input(labelText: 'Catégorie *'),
            items: widget.categories
                .map((c) => DropdownMenuItem(
                      value: c['code'].toString(),
                      child: Text(c['libelle']?.toString() ?? c['code'].toString()),
                    ))
                .toList(),
            onChanged: (v) => setState(() => _categorie = v),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _objetCtrl,
            decoration: MHSurfaceCard.input(labelText: 'Objet *'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _descCtrl,
            maxLines: 6,
            decoration: MHSurfaceCard.input(
              labelText: 'Description *',
              hintText: 'Décrivez votre demande (faits, dates, montants…)',
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            'Votre réclamation recevra une référence unique. Vous serez notifié à '
            'chaque étape et pourrez contester la décision après clôture.',
            style: TextStyle(fontSize: 12, color: AppColors.mutedText, height: 1.4),
          ),
          if (_error != null) ...[
            const SizedBox(height: 10),
            Text(_error!, style: const TextStyle(color: AppColors.danger, fontSize: 13)),
          ],
          const SizedBox(height: 16),
          MHGradientButton(label: 'Envoyer la réclamation', loading: _sending, onPressed: _submit),
        ],
      ),
    );
  }
}

class _ReclamationDetailScreen extends StatefulWidget {
  const _ReclamationDetailScreen({required this.id});

  final int id;

  @override
  State<_ReclamationDetailScreen> createState() => _ReclamationDetailScreenState();
}

class _ReclamationDetailScreenState extends State<_ReclamationDetailScreen> {
  final _service = ReclamationsService.instance;
  final _msgCtrl = TextEditingController();
  Map<String, dynamic>? _data;
  bool _loading = true;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _msgCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await _service.detail(widget.id);
      if (mounted) {
        setState(() {
          _data = d;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = apiErrorToUserMessage(e);
          _loading = false;
        });
      }
    }
  }

  Future<void> _sendMessage() async {
    final text = _msgCtrl.text.trim();
    if (text.isEmpty) return;
    setState(() => _sending = true);
    try {
      await _service.addMessage(widget.id, text);
      _msgCtrl.clear();
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(apiErrorToUserMessage(e)),
          backgroundColor: AppColors.danger,
        ));
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _contest() async {
    final ctrl = TextEditingController();
    final message = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Contester la décision'),
        content: TextField(
          controller: ctrl,
          maxLines: 4,
          decoration: const InputDecoration(
            labelText: 'Motif de la contestation *',
            hintText: 'Expliquez pourquoi vous contestez la réponse.',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
          FilledButton(
            onPressed: () {
              final v = ctrl.text.trim();
              if (v.isNotEmpty) Navigator.pop(ctx, v);
            },
            child: const Text('Contester'),
          ),
        ],
      ),
    );
    ctrl.dispose();
    if (message == null) return;
    try {
      await _service.contest(widget.id, message);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(apiErrorToUserMessage(e)),
          backgroundColor: AppColors.danger,
        ));
      }
    }
  }

  String _date(dynamic v) {
    final d = DateTime.tryParse('${v ?? ''}');
    if (d == null) return '';
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year} '
        '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final d = _data;
    final statut = d?['statut']?.toString() ?? '';
    final canContester = statut == 'traitee' || statut == 'cloturee';
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: MhAppBar(title: d?['reference']?.toString() ?? 'Réclamation'),
      body: _loading
          ? const MhLoadingView()
          : _error != null
              ? MhOfflineView(onRetry: _load)
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
                  children: [
                    MHSurfaceCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(d?['objet']?.toString() ?? '',
                                    style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        color: AppColors.secondary,
                                        fontSize: 15)),
                              ),
                              Text(
                                _statutLabels[statut] ?? statut,
                                style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: _statutColor(statut)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(d?['description']?.toString() ?? '',
                              style: const TextStyle(fontSize: 13, height: 1.45)),
                          const Divider(height: 20),
                          _row('Réponse attendue avant',
                              _date(d?['echeance_premiere_reponse'])),
                          _row('Résolution visée avant', _date(d?['echeance_resolution'])),
                          if (d?['reponse'] != null) ...[
                            const Divider(height: 20),
                            const Text('Réponse de MHC',
                                style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.secondary,
                                    fontSize: 13)),
                            const SizedBox(height: 6),
                            Text(d!['reponse'].toString(),
                                style: const TextStyle(fontSize: 13, height: 1.45)),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    const Text('Échanges',
                        style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: AppColors.secondary,
                            fontSize: 14)),
                    const SizedBox(height: 8),
                    ...(((d?['historique'] as List?) ?? const [])
                        .where((e) => e['type'] == 'message')
                        .map((e) => Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: MHSurfaceCard(
                                padding: const EdgeInsets.all(12),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '${e['auteur_est_assure'] == true ? 'Vous' : 'MHC'} • ${_date(e['date'])}',
                                      style: const TextStyle(
                                          fontSize: 11, color: AppColors.mutedText),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(e['message']?.toString() ?? '',
                                        style: const TextStyle(fontSize: 13, height: 1.4)),
                                  ],
                                ),
                              ),
                            ))),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _msgCtrl,
                            decoration: MHSurfaceCard.input(
                              hintText: 'Ajouter un message…',
                              isDense: true,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        IconButton.filled(
                          onPressed: _sending ? null : _sendMessage,
                          icon: const Icon(Icons.send, size: 18),
                          style: IconButton.styleFrom(
                              backgroundColor: AppColors.secondary),
                        ),
                      ],
                    ),
                    if (canContester) ...[
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        height: 44,
                        child: OutlinedButton.icon(
                          onPressed: _contest,
                          icon: const Icon(Icons.gavel_outlined,
                              color: AppColors.danger, size: 18),
                          label: const Text('Contester la décision',
                              style: TextStyle(
                                  color: AppColors.danger,
                                  fontWeight: FontWeight.w600)),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Color(0xFFF3C2C7)),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: AppColors.mutedText)),
          Text(value.isEmpty ? '—' : value,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
