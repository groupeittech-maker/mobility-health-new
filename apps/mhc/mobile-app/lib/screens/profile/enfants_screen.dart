import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/api_error_helper.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/destination.dart';
import '../../services/account_service.dart';
import '../../services/api_services.dart';

/// Enfants bénéficiaires (< 18 ans) enregistrés sur le compte (workflow V3 §4.3).
/// Le questionnaire médical de la souscription distingue chaque enfant.
class EnfantsScreen extends StatefulWidget {
  const EnfantsScreen({super.key});

  @override
  State<EnfantsScreen> createState() => _EnfantsScreenState();
}

class _EnfantsScreenState extends State<EnfantsScreen> {
  final _service = EnfantsService.instance;
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final list = await _service.list();
      if (mounted) {
        setState(() {
          _items = list;
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

  void _snack(String message, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: error ? AppColors.danger : AppColors.success,
    ));
  }

  Future<void> _openForm([Map<String, dynamic>? enfant]) async {
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (ctx) => _EnfantForm(enfant: enfant),
    );
    if (saved == true) {
      _snack(enfant == null ? 'Enfant enregistré.' : 'Enfant mis à jour.');
      _load();
    }
  }

  Future<void> _delete(Map<String, dynamic> e) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Retirer cet enfant ?'),
        content: Text(
          '${e['prenom'] ?? ''} ${e['nom'] ?? ''} sera retiré de vos bénéficiaires. '
              'Les polices existantes ne sont pas modifiées.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Retirer'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _service.delete(e['id'] as int);
      _snack('Enfant retiré.');
      _load();
    } catch (err) {
      _snack(apiErrorToUserMessage(err), error: true);
    }
  }

  String _age(String? iso) {
    final born = DateTime.tryParse(iso ?? '');
    if (born == null) return '';
    final now = DateTime.now();
    var age = now.year - born.year;
    if (now.month < born.month || (now.month == born.month && now.day < born.day)) age--;
    return '$age an${age > 1 ? 's' : ''}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Mes enfants'),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openForm(),
        backgroundColor: AppColors.secondary,
        icon: const Icon(Icons.add, color: Colors.white),
        label: const Text('Ajouter', style: TextStyle(color: Colors.white)),
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
                      const Text(
                        'Enregistrez vos enfants mineurs pour les ajouter rapidement '
                        'à vos polices.',
                        style: TextStyle(fontSize: 12, color: AppColors.mutedText, height: 1.45),
                      ),
                      const SizedBox(height: 14),
                      if (_items.isEmpty)
                        const Padding(
                          padding: EdgeInsets.all(24),
                          child: Text('Aucun enfant enregistré.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: AppColors.mutedText)),
                        )
                      else
                        ..._items.map((e) => Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: MHSurfaceCard(
                                child: ListTile(
                                  leading: CircleAvatar(
                                    backgroundColor: const Color(0xFFEDE9FE),
                                    child: Text(
                                      (e['prenom']?.toString().isNotEmpty == true
                                              ? e['prenom'].toString()[0]
                                              : e['nom'].toString()[0])
                                          .toUpperCase(),
                                      style: const TextStyle(
                                          color: AppColors.secondary,
                                          fontWeight: FontWeight.bold),
                                    ),
                                  ),
                                  title: Text(
                                    '${e['prenom'] ?? ''} ${e['nom'] ?? ''}'.trim(),
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w600, fontSize: 14),
                                  ),
                                  subtitle: Text(
                                    '${_age(e['date_naissance']?.toString())}'
                                    '${e['numero_piece_masque'] != null ? ' • Pièce ${e['numero_piece_masque']}' : ''}'
                                    '${e['lien_parente'] != null ? ' • ${e['lien_parente']}' : ''}',
                                    style: const TextStyle(fontSize: 12),
                                  ),
                                  trailing: PopupMenuButton<String>(
                                    onSelected: (v) {
                                      if (v == 'edit') _openForm(e);
                                      if (v == 'delete') _delete(e);
                                    },
                                    itemBuilder: (_) => const [
                                      PopupMenuItem(value: 'edit', child: Text('Modifier')),
                                      PopupMenuItem(value: 'delete', child: Text('Retirer')),
                                    ],
                                  ),
                                ),
                              ),
                            )),
                    ],
                  ),
                ),
    );
  }
}

class _EnfantForm extends StatefulWidget {
  const _EnfantForm({this.enfant});

  final Map<String, dynamic>? enfant;

  @override
  State<_EnfantForm> createState() => _EnfantFormState();
}

class _EnfantFormState extends State<_EnfantForm> {
  late final TextEditingController _nomCtrl =
      TextEditingController(text: widget.enfant?['nom']?.toString() ?? '');
  late final TextEditingController _prenomCtrl =
      TextEditingController(text: widget.enfant?['prenom']?.toString() ?? '');
  late final TextEditingController _pieceCtrl =
      TextEditingController(text: widget.enfant?['numero_piece']?.toString() ?? '');
  late final TextEditingController _lienCtrl =
      TextEditingController(text: widget.enfant?['lien_parente']?.toString() ?? '');
  DateTime? _naissance;
  DateTime? _validite;
  bool _saving = false;
  String? _error;
  String? _nationalite;
  String? _paysResidence;
  List<ReferenceCountryModel> _countries = [];

  @override
  void initState() {
    super.initState();
    _naissance = DateTime.tryParse(widget.enfant?['date_naissance']?.toString() ?? '');
    _validite = DateTime.tryParse(widget.enfant?['validite_piece']?.toString() ?? '');
    _nationalite = widget.enfant?['nationalite']?.toString();
    _paysResidence = widget.enfant?['pays_residence']?.toString();
    DestinationsService().getReferenceCountries().then((list) {
      if (mounted) setState(() => _countries = list);
    }).ignore();
  }

  @override
  void dispose() {
    _nomCtrl.dispose();
    _prenomCtrl.dispose();
    _pieceCtrl.dispose();
    _lienCtrl.dispose();
    super.dispose();
  }

  String _day(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  String _fmt(DateTime? d) => d == null
      ? 'Sélectionner'
      : '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';

  Future<DateTime?> _pick(DateTime? initial, {required bool past}) {
    final now = DateTime.now();
    return showDatePicker(
      context: context,
      initialDate: initial ?? (past ? DateTime(now.year - 8) : now.add(const Duration(days: 365))),
      firstDate: past ? DateTime(now.year - 18, now.month, now.day + 1) : now,
      lastDate: past ? now.subtract(const Duration(days: 1)) : DateTime(now.year + 20),
    );
  }

  Future<void> _submit() async {
    if (_nomCtrl.text.trim().isEmpty || _naissance == null) {
      setState(() => _error = 'Nom et date de naissance sont obligatoires.');
      return;
    }
    if (_lienCtrl.text.trim().isEmpty) {
      setState(() => _error = 'Le lien de parenté est obligatoire.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final args = <String, dynamic>{
        'nom': _nomCtrl.text,
        'dateNaissance': _day(_naissance!),
        'prenom': _prenomCtrl.text,
        'nationalite': _nationalite,
        'paysResidence': _paysResidence,
        'numeroPiece': _pieceCtrl.text,
        'lienParente': _lienCtrl.text,
        if (_validite != null) 'validitePiece': _day(_validite!),
      };
      final id = widget.enfant?['id'];
      if (id is int) {
        await EnfantsService.instance.update(
          id,
          nom: args['nom'] as String,
          dateNaissance: args['dateNaissance'] as String,
          prenom: args['prenom'] as String?,
          nationalite: args['nationalite'] as String?,
          paysResidence: args['paysResidence'] as String?,
          numeroPiece: args['numeroPiece'] as String?,
          validitePiece: args['validitePiece'] as String?,
          lienParente: args['lienParente'] as String?,
        );
      } else {
        await EnfantsService.instance.create(
          nom: args['nom'] as String,
          dateNaissance: args['dateNaissance'] as String,
          prenom: args['prenom'] as String?,
          nationalite: args['nationalite'] as String?,
          paysResidence: args['paysResidence'] as String?,
          numeroPiece: args['numeroPiece'] as String?,
          validitePiece: args['validitePiece'] as String?,
          lienParente: args['lienParente'] as String?,
        );
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() {
          _saving = false;
          _error = apiErrorToUserMessage(e);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.enfant == null ? 'Ajouter un enfant' : 'Modifier l’enfant',
              style: Theme.of(context)
                  .textTheme
                  .titleLarge
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _nomCtrl,
              decoration: MHSurfaceCard.input(labelText: 'Nom *'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _prenomCtrl,
              decoration: MHSurfaceCard.input(labelText: 'Prénom'),
            ),
            const SizedBox(height: 10),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.cake_outlined, color: AppColors.secondary),
              title: const Text('Date de naissance *', style: TextStyle(fontSize: 14)),
              subtitle: Text(_fmt(_naissance)),
              onTap: () async {
                final d = await _pick(_naissance, past: true);
                if (d != null) setState(() => _naissance = d);
              },
            ),
            DropdownButtonFormField<String>(
              value: _countries.any((c) => c.nom == _nationalite) ? _nationalite : null,
              decoration: MHSurfaceCard.input(labelText: 'Nationalité'),
              items: _countries
                  .map((c) => DropdownMenuItem(value: c.nom, child: Text(c.nom)))
                  .toList(),
              onChanged: (v) => setState(() => _nationalite = v),
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              value: _countries.any((c) => c.nom == _paysResidence) ? _paysResidence : null,
              decoration: MHSurfaceCard.input(labelText: 'Pays de résidence'),
              items: _countries
                  .map((c) => DropdownMenuItem(value: c.nom, child: Text(c.nom)))
                  .toList(),
              onChanged: (v) => setState(() => _paysResidence = v),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _pieceCtrl,
              decoration: MHSurfaceCard.input(
                labelText: 'N° de pièce d’identité / passeport',
              ),
            ),
            const SizedBox(height: 10),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.event_outlined, color: AppColors.secondary),
              title: const Text('Validité de la pièce', style: TextStyle(fontSize: 14)),
              subtitle: Text(_fmt(_validite)),
              onTap: () async {
                final d = await _pick(_validite, past: false);
                if (d != null) setState(() => _validite = d);
              },
            ),
            TextField(
              controller: _lienCtrl,
              decoration: MHSurfaceCard.input(
                labelText: 'Lien de parenté *',
                hintText: 'Ex. : fils, fille, pupille',
              ),
            ),
            const SizedBox(height: 10),
            const Text(
              'Un enfant bénéficiaire doit avoir moins de 18 ans.',
              style: TextStyle(fontSize: 12, color: AppColors.mutedText),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: const TextStyle(color: AppColors.danger, fontSize: 13)),
            ],
            const SizedBox(height: 14),
            MHGradientButton(
              label: widget.enfant == null ? 'Enregistrer' : 'Mettre à jour',
              loading: _saving,
              onPressed: _submit,
            ),
          ],
        ),
      ),
    );
  }
}
