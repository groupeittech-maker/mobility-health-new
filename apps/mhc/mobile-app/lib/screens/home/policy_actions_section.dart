import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/constants/app_colors.dart';
import '../../core/utils/api_error_helper.dart';
import '../../models/destination.dart';
import '../../models/subscription.dart';
import '../../services/api_services.dart';
import '../../services/avenant_service.dart';
import '../pdf_viewer_screen.dart';

/// Actions sur une police (workflow MyMHC V3) : annuler, changer de
/// destination (même zone tarifaire), prolonger. Une seule demande en cours
/// par attestation : tant qu'un complément de prime est attendu, les autres
/// actions sont désactivées.
class PolicyActionsSection extends StatefulWidget {
  const PolicyActionsSection({
    super.key,
    required this.subscription,
    required this.onChanged,
  });

  final SubscriptionModel subscription;

  /// Appelé après une action (rechargement de la souscription).
  final Future<void> Function() onChanged;

  @override
  State<PolicyActionsSection> createState() => _PolicyActionsSectionState();
}

const _typeLabels = {
  'annulation': "Avenant d'annulation",
  'modification': 'Avenant de modification',
  'prorogation': 'Avenant de prorogation',
};
const _paymentTypes = {
  'mobile_money_mtn': 'Mobile Money MTN',
  'mobile_money_airtel': 'Airtel Money',
  'carte_bancaire': 'Carte bancaire',
};

class _PolicyActionsSectionState extends State<PolicyActionsSection> {
  final _service = AvenantService.instance;
  Map<String, dynamic>? _info;
  bool _loading = true;
  String? _opening;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant PolicyActionsSection oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.subscription.statut != widget.subscription.statut ||
        oldWidget.subscription.dateFin != widget.subscription.dateFin) {
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final info = await _service.fetchActions(widget.subscription.id);
      if (mounted) setState(() => _info = info);
    } catch (_) {
      // Section masquée si l'API est indisponible.
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _refreshAll() async {
    await widget.onChanged();
    await _load();
  }

  void _snack(String message, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(message),
      backgroundColor: error ? AppColors.danger : AppColors.success,
    ));
  }

  String _money(dynamic v, [String devise = 'XAF']) {
    final n = num.tryParse('${v ?? 0}') ?? 0;
    final s = n.round().toString().replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ' ');
    return '$s $devise';
  }

  String _date(dynamic v) {
    final d = v is DateTime ? v : DateTime.tryParse('${v ?? ''}');
    if (d == null) return '–';
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  }

  Map<String, dynamic> _action(String key) =>
      Map<String, dynamic>.from((_info?['actions'] as Map?)?[key] as Map? ?? const {});

  // ---------------------------------------------------------------------------
  // Demandes
  // ---------------------------------------------------------------------------
  Future<void> _openActionSheet(String action) async {
    final s = widget.subscription;
    final maxDays = (_info?['duree_max_jours'] as num?)?.toInt() ?? 92;
    DateTime start = DateUtils.dateOnly(s.dateDebut);
    DateTime end = DateUtils.dateOnly(s.dateFin ?? s.dateDebut);
    if (action == 'prorogation') end = end.add(const Duration(days: 1));
    final voyagePasCommence =
        DateUtils.dateOnly(DateTime.now()).isBefore(DateUtils.dateOnly(s.dateDebut));
    final motifCtrl = TextEditingController();
    final villeCtrl = TextEditingController();
    List<DestinationCountryModel> countries = const [];
    DestinationCountryModel? destination;
    Map<String, dynamic>? simulation;
    String? error;
    var busy = false;
    var confirmed = false;

    if (action == 'modification') {
      try {
        countries = await DestinationsService().getDestinationCountries();
      } catch (_) {
        if (mounted) {
          _snack('Liste des destinations indisponible.', error: true);
        }
        return;
      }
    }

    final titles = {
      'annulation': 'Annuler la police',
      'modification': 'Modifier le voyage',
      'prorogation': 'Prolonger la police',
    };
    final hints = {
      'annulation': "L'annulation est définitive et n'est possible qu'avant la date d'effet.",
      'modification': "Destination (même zone tarifaire) et, avant le début du voyage, "
          "dates : la prime est recalculée (supplément à payer ou remboursement).",
      'prorogation': "Jusqu'à la date de fin initiale. Durée totale maximale : $maxDays jours. Prime complémentaire au prorata.",
    };

    Future<void> simulate(StateSetter setSheet) async {
      setSheet(() {
        busy = true;
        error = null;
      });
      try {
        final res = await _service.submitAction(
          s.id, action,
          confirm: false,
          destinationCountryId: action == 'modification' ? destination?.id : null,
          destinationVille: action == 'modification' ? villeCtrl.text : null,
          nouvelleDateDebut: action == 'modification' ? start : null,
          nouvelleDateFin: action == 'annulation' ? null : end,
        );
        setSheet(() => simulation = res);
      } catch (e) {
        setSheet(() {
          simulation = null;
          error = apiErrorToUserMessage(e);
        });
      } finally {
        setSheet(() => busy = false);
      }
    }

    Future<void> confirm(BuildContext sheetCtx, StateSetter setSheet) async {
      setSheet(() => busy = true);
      try {
        final res = await _service.submitAction(
          s.id, action,
          confirm: true,
          destinationCountryId: action == 'modification' ? destination?.id : null,
          destinationVille: action == 'modification' ? villeCtrl.text : null,
          nouvelleDateDebut: action == 'modification' ? start : null,
          nouvelleDateFin: action == 'annulation' ? null : end,
          motif: motifCtrl.text,
        );
        if (sheetCtx.mounted) Navigator.pop(sheetCtx);
        final avenant = res['avenant'] as Map?;
        if (avenant != null && avenant['statut'] == 'attente_paiement') {
          await _refreshAll();
          await _openPaymentSheet((avenant['id'] as num).toInt(), avenant['montant_ajustement']);
          return;
        }
        _snack(action == 'annulation' ? 'Votre police est annulée.' : 'Avenant émis.');
        await _refreshAll();
      } catch (e) {
        setSheet(() {
          busy = false;
          error = apiErrorToUserMessage(e);
        });
      }
    }

    String summary(Map<String, dynamic> sim) {
      final m = Map<String, dynamic>.from(sim['montants'] as Map? ?? const {});
      final total = num.tryParse('${m['total'] ?? 0}') ?? 0;
      if (action == 'annulation') {
        return total > 0
            ? 'Montant remboursable : ${_money(total)}. Le remboursement est traité séparément par Mobility Health Care.'
            : "Aucun paiement n'a été effectué : aucun remboursement n'est dû.";
      }
      switch (sim['nature_ajustement']) {
        case 'complement':
          return "Complément de prime à régler : ${_money(total)}. L'avenant sera émis après paiement.";
        case 'remboursement':
          return "Remboursement partiel : ${_money(total)}. L'avenant est émis immédiatement.";
        default:
          return "Aucun ajustement de prime : l'avenant est émis immédiatement.";
      }
    }

    Future<DateTime?> pick(BuildContext ctx, DateTime initial, DateTime first, DateTime last) {
      return showDatePicker(
        context: ctx,
        initialDate: initial.isBefore(first) ? first : (initial.isAfter(last) ? last : initial),
        firstDate: first,
        lastDate: last,
      );
    }

    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSheet) {
        if (action == 'annulation' && simulation == null && error == null && !busy) {
          WidgetsBinding.instance.addPostFrameCallback((_) => simulate(setSheet));
        }
        return Padding(
          padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.viewInsetsOf(ctx).bottom),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(titles[action]!,
                    style: Theme.of(ctx).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text(hints[action]!, style: const TextStyle(fontSize: 13, color: AppColors.mutedText)),
                const SizedBox(height: 12),
                if (action == 'modification') ...[
                  DropdownButtonFormField<DestinationCountryModel>(
                    initialValue: destination,
                    decoration: const InputDecoration(
                      labelText: 'Nouvelle destination *',
                      border: OutlineInputBorder(),
                    ),
                    items: countries
                        .map((c) => DropdownMenuItem(value: c, child: Text(c.nom)))
                        .toList(),
                    onChanged: (v) => setSheet(() {
                      destination = v;
                      simulation = null;
                    }),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: villeCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Ville (optionnel)',
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (_) => setSheet(() => simulation = null),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Destination actuelle : ${s.projetVoyage?.destinationDisplay ?? s.projetVoyage?.destination ?? '—'}',
                    style: const TextStyle(fontSize: 12, color: AppColors.mutedText),
                  ),
                  if (voyagePasCommence) ...[
                    const SizedBox(height: 10),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.flight_takeoff),
                      title: const Text('Nouvelle date de début'),
                      subtitle: Text(_date(start)),
                      onTap: () async {
                        final first = DateUtils.dateOnly(DateTime.now())
                            .add(const Duration(days: 1));
                        final last =
                            end.subtract(const Duration(days: 1));
                        final d = await pick(
                            ctx, start.isAfter(first) ? start : first, first, last);
                        if (d != null) {
                          setSheet(() {
                            start = d;
                            if (!end.isAfter(start)) {
                              end = start.add(const Duration(days: 1));
                            }
                            simulation = null;
                          });
                        }
                      },
                    ),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.flight_land),
                      title: const Text('Nouvelle date de fin'),
                      subtitle: Text(_date(end)),
                      onTap: () async {
                        final first = start.add(const Duration(days: 1));
                        final last =
                            start.add(Duration(days: maxDays));
                        final d = await pick(ctx, end, first, last);
                        if (d != null) {
                          setSheet(() {
                            end = d;
                            simulation = null;
                          });
                        }
                      },
                    ),
                  ],
                ],
                if (action == 'prorogation')
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.flight_land),
                    title: const Text('Nouvelle date de fin de couverture'),
                    subtitle: Text(_date(end)),
                    onTap: () async {
                      final first = DateUtils.dateOnly(s.dateFin ?? s.dateDebut).add(const Duration(days: 1));
                      final last = DateUtils.dateOnly(s.dateDebut).add(Duration(days: maxDays));
                      if (last.isBefore(first)) return;
                      final d = await pick(ctx, end, first, last);
                      if (d != null) {
                        setSheet(() {
                          end = d;
                          simulation = null;
                        });
                      }
                    },
                  ),
                TextField(
                  controller: motifCtrl,
                  maxLines: 2,
                  decoration: const InputDecoration(labelText: 'Motif (optionnel)', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                if (error != null)
                  Text(error!, style: const TextStyle(color: AppColors.danger, fontSize: 13)),
                if (simulation != null)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(summary(simulation!), style: const TextStyle(fontSize: 13)),
                  ),
                if (simulation != null && action == 'annulation')
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    value: confirmed,
                    onChanged: (v) => setSheet(() => confirmed = v == true),
                    title: const Text('Je confirme vouloir annuler définitivement cette police.',
                        style: TextStyle(fontSize: 13)),
                  ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: simulation == null
                      ? OutlinedButton(
                          onPressed: busy ? null : () => simulate(setSheet),
                          child: Text(busy ? 'Calcul…' : 'Calculer'),
                        )
                      : FilledButton(
                          style: FilledButton.styleFrom(
                            backgroundColor: action == 'annulation' ? AppColors.danger : AppColors.secondary,
                          ),
                          onPressed: busy || (action == 'annulation' && !confirmed)
                              ? null
                              : () => confirm(ctx, setSheet),
                          child: Text(busy ? 'Envoi…' : 'Confirmer'),
                        ),
                ),
              ],
            ),
          ),
        );
      }),
    );
    motifCtrl.dispose();
    villeCtrl.dispose();
  }

  Future<void> _openPaymentSheet(int avenantId, dynamic montant) async {
    var paymentType = _paymentTypes.keys.first;
    var busy = false;
    await showModalBottomSheet<void>(
      context: context,
      useSafeArea: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Payer le complément de prime',
                  style: Theme.of(ctx).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              const Text(
                "L'avenant est émis dès confirmation du paiement. En cas d'échec, aucune modification n'est appliquée.",
                style: TextStyle(fontSize: 13, color: AppColors.mutedText),
              ),
              const SizedBox(height: 12),
              Text('Montant : ${_money(montant)}', style: const TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: _paymentTypes.entries
                    .map((e) => ChoiceChip(
                          label: Text(e.value),
                          selected: paymentType == e.key,
                          onSelected: (_) => setSheet(() => paymentType = e.key),
                        ))
                    .toList(),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: busy
                      ? null
                      : () async {
                          setSheet(() => busy = true);
                          try {
                            final res = await _service.payAvenant(avenantId, paymentType: paymentType);
                            if (ctx.mounted) Navigator.pop(ctx);
                            final url = res['payment_url']?.toString();
                            if (url != null && url.isNotEmpty) {
                              final uri = Uri.tryParse(url);
                              if (uri != null) await launchUrl(uri, mode: LaunchMode.inAppBrowserView);
                              _snack('Paiement en cours : la police sera mise à jour après confirmation.');
                            } else if ((res['avenant'] as Map?)?['statut'] == 'emis') {
                              _snack('Paiement confirmé : avenant émis.');
                            } else {
                              _snack('Paiement en cours de traitement.');
                            }
                            await _refreshAll();
                          } catch (e) {
                            setSheet(() => busy = false);
                            _snack(apiErrorToUserMessage(e), error: true);
                          }
                        },
                  child: Text(busy ? 'Paiement…' : 'Payer'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _abandon(int avenantId) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Renoncer à la demande ?'),
        content: const Text('Les autres actions seront de nouveau disponibles.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Non')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Renoncer')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await _service.abandonAvenant(avenantId);
      _snack('Demande abandonnée.');
      await _load();
    } catch (e) {
      _snack(apiErrorToUserMessage(e), error: true);
    }
  }

  Future<void> _openPdf(String key, Future<String> Function() download, String title) async {
    setState(() => _opening = key);
    try {
      final path = await download();
      if (!mounted) return;
      await Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => PdfViewerScreen(filePath: path, title: title),
      ));
    } catch (e) {
      _snack(apiErrorToUserMessage(e), error: true);
    } finally {
      if (mounted) setState(() => _opening = null);
    }
  }

  // ---------------------------------------------------------------------------
  // Rendu
  // ---------------------------------------------------------------------------
  @override
  Widget build(BuildContext context) {
    if (_loading || _info == null) return const SizedBox.shrink();
    final statut = widget.subscription.statut;
    final pending = _info!['action_en_cours'] as Map?;
    final avenants = ((_info!['avenants'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .where((a) => a['statut'] == 'emis')
        .toList();
    final ristournes = ((_info!['ristournes'] as List?) ?? const [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final showButtons = !['resiliee', 'refusee', 'expiree', 'en_attente', 'pending'].contains(statut);

    Widget actionButton(String key, String label, IconData icon, {bool danger = false}) {
      final state = _action(key);
      // Pendant une demande en cours, les autres actions sont grisées (§6).
      final enabled = state['disponible'] == true && pending == null;
      final motif = state['motif']?.toString();
      return Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: enabled ? () => _openActionSheet(key) : null,
                icon: Icon(icon, size: 20),
                label: Text(label),
                style: OutlinedButton.styleFrom(
                  foregroundColor: danger ? AppColors.danger : AppColors.secondary,
                ),
              ),
            ),
            if (!enabled && pending == null && motif != null)
              Padding(
                padding: const EdgeInsets.only(top: 2, left: 4),
                child: Text(motif, style: const TextStyle(fontSize: 11, color: AppColors.mutedText)),
              ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (pending != null)
          Container(
            margin: const EdgeInsets.only(top: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.orange.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Demande en cours : ${_typeLabels[pending['type_avenant']] ?? pending['type_avenant']}',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text('Du ${_date(pending['nouvelle_date_debut'])} au ${_date(pending['nouvelle_date_fin'])}',
                    style: const TextStyle(fontSize: 13)),
                Text('Complément à régler : ${_money(pending['montant_ajustement'])}',
                    style: const TextStyle(fontSize: 13)),
                const Text(
                  "Les autres actions sur cette attestation sont désactivées jusqu'à la clôture de la demande.",
                  style: TextStyle(fontSize: 12, color: AppColors.mutedText),
                ),
                const SizedBox(height: 8),
                Row(children: [
                  FilledButton(
                    onPressed: () => _openPaymentSheet(
                        (pending['id'] as num).toInt(), pending['montant_ajustement']),
                    child: const Text('Payer'),
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () => _abandon((pending['id'] as num).toInt()),
                    child: const Text('Renoncer'),
                  ),
                ]),
              ],
            ),
          ),
        if (showButtons) ...[
          if (statut == 'active') ...[
            actionButton('modification', 'Modifier le voyage', Icons.flight_takeoff_outlined),
            actionButton('prorogation', 'Prolonger', Icons.update),
          ],
          actionButton('annulation', 'Annuler la police', Icons.cancel_outlined, danger: true),
        ],
        if (avenants.isNotEmpty || ristournes.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text('Avenants et remboursements',
              style: TextStyle(fontWeight: FontWeight.w600, color: Color(0xFF1E293B))),
          ...avenants.map((a) {
            final id = (a['id'] as num).toInt();
            return ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.description_outlined, color: AppColors.secondary),
              title: Text(_typeLabels[a['type_avenant']] ?? '${a['type_avenant']}'),
              subtitle: Text('N° ${a['numero']}'),
              trailing: _opening == 'av-$id'
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.picture_as_pdf_outlined),
              onTap: () => _openPdf(
                'av-$id',
                () => _service.downloadAvenantPdf(id, numero: a['numero']?.toString()),
                _typeLabels[a['type_avenant']] ?? 'Avenant',
              ),
            );
          }),
          ...ristournes.map((r) {
            final id = (r['id'] as num).toInt();
            final done = r['statut'] == 'rembourse';
            return ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(done ? Icons.check_circle_outline : Icons.schedule,
                  color: done ? AppColors.success : AppColors.warning),
              title: Text('Remboursement de ${_money(r['montant_total'], '${r['devise'] ?? 'XAF'}')}'),
              subtitle: Text(done ? 'Remboursé • Quittance N° ${r['numero']}' : 'Remboursement en cours'),
              trailing: done
                  ? (_opening == 'ri-$id'
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.picture_as_pdf_outlined))
                  : null,
              onTap: done
                  ? () => _openPdf(
                        'ri-$id',
                        () => _service.downloadRistournePdf(id, numero: r['numero']?.toString()),
                        'Quittance de ristourne',
                      )
                  : null,
            );
          }),
        ],
      ],
    );
  }
}
