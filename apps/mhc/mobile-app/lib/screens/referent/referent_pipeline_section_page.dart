import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/constants/app_colors.dart';
import '../../models/referent_pipeline.dart';

/// Contenu d'une section du pipeline (Sinistre / Rapport / Facture / Résolu) avec sous-onglets à valider / validé.
class ReferentPipelineSectionPage extends StatefulWidget {
  const ReferentPipelineSectionPage({
    super.key,
    required this.section,
    this.initialSubTab,
    required this.items,
    required this.loading,
    this.error,
    required this.onRefresh,
    this.hasMore = false,
    this.loadingMore = false,
    this.onLoadMore,
  });

  final ReferentFooterSection section;
  /// Si non null : sous-onglet initial 0 = à valider, 1 = validé.
  final int? initialSubTab;
  final List<ReferentDossierItem> items;
  final bool loading;
  final String? error;
  final Future<void> Function() onRefresh;
  final bool hasMore;
  final bool loadingMore;
  final Future<void> Function()? onLoadMore;

  @override
  State<ReferentPipelineSectionPage> createState() => _ReferentPipelineSectionPageState();
}

class _ReferentPipelineSectionPageState extends State<ReferentPipelineSectionPage> {
  late int _subTab; // 0 = à valider, 1 = validé

  @override
  void initState() {
    super.initState();
    final init = widget.initialSubTab;
    _subTab = init != null ? init.clamp(0, 1) : 0;
  }

  @override
  void didUpdateWidget(covariant ReferentPipelineSectionPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.section != widget.section) {
      _subTab = 0;
    }
  }

  String get _title {
    switch (widget.section) {
      case ReferentFooterSection.sinistre:
        return 'Sinistre';
      case ReferentFooterSection.rapport:
        return 'Rapport';
      case ReferentFooterSection.facture:
        return 'Facture';
      case ReferentFooterSection.resolu:
        return 'Dossier résolu';
    }
  }

  List<ReferentDossierItem> _itemsForFooterSection() {
    switch (widget.section) {
      case ReferentFooterSection.sinistre:
        return widget.items
            .where((e) =>
                e.step == ReferentPipelineStep.sinistre ||
                e.step == ReferentPipelineStep.sinistreValide)
            .toList();
      case ReferentFooterSection.rapport:
        return widget.items
            .where((e) =>
                e.step == ReferentPipelineStep.rapport ||
                e.step == ReferentPipelineStep.rapportValide)
            .toList();
      case ReferentFooterSection.facture:
        return widget.items
            .where((e) =>
                e.step == ReferentPipelineStep.facture ||
                e.step == ReferentPipelineStep.factureValide)
            .toList();
      case ReferentFooterSection.resolu:
        return widget.items.where((e) => e.step == ReferentPipelineStep.resolu).toList();
    }
  }

  List<ReferentDossierItem> _applySubTab(List<ReferentDossierItem> base) {
    if (widget.section == ReferentFooterSection.resolu) {
      return base;
    }
    if (_subTab == 0) {
      switch (widget.section) {
        case ReferentFooterSection.sinistre:
          return base.where((e) => e.step == ReferentPipelineStep.sinistre).toList();
        case ReferentFooterSection.rapport:
          return base.where((e) => e.step == ReferentPipelineStep.rapport).toList();
        case ReferentFooterSection.facture:
          return base.where((e) => e.step == ReferentPipelineStep.facture).toList();
        case ReferentFooterSection.resolu:
          return base;
      }
    }
    switch (widget.section) {
      case ReferentFooterSection.sinistre:
        return base.where((e) => e.step == ReferentPipelineStep.sinistreValide).toList();
      case ReferentFooterSection.rapport:
        return base.where((e) => e.step == ReferentPipelineStep.rapportValide).toList();
      case ReferentFooterSection.facture:
        return base.where((e) => e.step == ReferentPipelineStep.factureValide).toList();
      case ReferentFooterSection.resolu:
        return base;
    }
  }

  (int, int) _counts(List<ReferentDossierItem> base) {
    if (widget.section == ReferentFooterSection.resolu) {
      return (base.length, 0);
    }
    switch (widget.section) {
      case ReferentFooterSection.sinistre:
        final a = base.where((e) => e.step == ReferentPipelineStep.sinistre).length;
        final b = base.where((e) => e.step == ReferentPipelineStep.sinistreValide).length;
        return (a, b);
      case ReferentFooterSection.rapport:
        final a = base.where((e) => e.step == ReferentPipelineStep.rapport).length;
        final b = base.where((e) => e.step == ReferentPipelineStep.rapportValide).length;
        return (a, b);
      case ReferentFooterSection.facture:
        final a = base.where((e) => e.step == ReferentPipelineStep.facture).length;
        final b = base.where((e) => e.step == ReferentPipelineStep.factureValide).length;
        return (a, b);
      case ReferentFooterSection.resolu:
        return (base.length, 0);
    }
  }

  Color _accentForStep(ReferentPipelineStep step) {
    switch (step) {
      case ReferentPipelineStep.sinistre:
        return AppColors.danger;
      case ReferentPipelineStep.rapport:
        return AppColors.warning;
      case ReferentPipelineStep.facture:
        return AppColors.secondary;
      case ReferentPipelineStep.resolu:
        return AppColors.success;
      default:
        return AppColors.primary;
    }
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd/MM/yyyy HH:mm');
    final base = _itemsForFooterSection();
    final (c0, c1) = _counts(base);
    final displayed = _applySubTab(base);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Text(
            _title,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppColors.primary,
                ),
          ),
        ),
        if (widget.section != ReferentFooterSection.resolu)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: SegmentedButton<int>(
              segments: [
                ButtonSegment<int>(
                  value: 0,
                  label: Text('À valider ($c0)'),
                ),
                ButtonSegment<int>(
                  value: 1,
                  label: Text('Validé ($c1)'),
                ),
              ],
              selected: {_subTab},
              onSelectionChanged: (s) => setState(() => _subTab = s.first),
            ),
          ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: widget.onRefresh,
            child: _buildList(context, displayed, df),
          ),
        ),
      ],
    );
  }

  Widget _buildList(
    BuildContext context,
    List<ReferentDossierItem> rows,
    DateFormat df,
  ) {
    if (widget.loading && widget.items.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 120),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }
    if (widget.error != null && widget.items.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          Icon(Icons.error_outline, size: 48, color: Colors.red.shade400),
          const SizedBox(height: 12),
          Text(widget.error!, textAlign: TextAlign.center),
          const SizedBox(height: 16),
          Center(
            child: FilledButton(
              onPressed: () => widget.onRefresh(),
              child: const Text('Réessayer'),
            ),
          ),
        ],
      );
    }
    if (rows.isEmpty) {
      final hintMore = widget.hasMore &&
          widget.onLoadMore != null &&
          widget.items.isNotEmpty &&
          widget.section != ReferentFooterSection.resolu;
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 24),
        children: [
          SizedBox(height: MediaQuery.sizeOf(context).height * 0.12),
          Center(
            child: Text(
              widget.section == ReferentFooterSection.resolu
                  ? 'Aucun dossier résolu.'
                  : hintMore
                      ? 'Aucun dossier dans cet onglet pour les pages déjà chargées. Chargez la suite pour afficher d\'autres dossiers.'
                      : 'Aucun dossier dans cette vue.',
              textAlign: TextAlign.center,
            ),
          ),
          if (widget.hasMore && widget.onLoadMore != null) ...[
            const SizedBox(height: 20),
            Center(
              child: widget.loadingMore
                  ? const SizedBox(
                      width: 28,
                      height: 28,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : TextButton.icon(
                      onPressed: widget.onLoadMore,
                      icon: const Icon(Icons.expand_more),
                      label: const Text('Charger la suite'),
                    ),
            ),
          ],
        ],
      );
    }
    final footer = (widget.hasMore || widget.loadingMore) ? 1 : 0;
    return NotificationListener<ScrollNotification>(
      onNotification: (ScrollNotification n) {
        if (widget.onLoadMore == null ||
            !widget.hasMore ||
            widget.loadingMore ||
            widget.loading) {
          return false;
        }
        if (n is! ScrollUpdateNotification && n is! ScrollEndNotification) {
          return false;
        }
        final m = n.metrics;
        if (!m.hasViewportDimension || m.maxScrollExtent <= 0) {
          return false;
        }
        if (m.pixels < 8) {
          return false;
        }
        if (m.extentAfter < 200) {
          widget.onLoadMore!();
        }
        return false;
      },
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        itemCount: rows.length + footer,
        itemBuilder: (context, i) {
        if (i >= rows.length) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Center(
              child: widget.loadingMore
                  ? const SizedBox(
                      width: 28,
                      height: 28,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : TextButton.icon(
                      onPressed: widget.onLoadMore,
                      icon: const Icon(Icons.expand_more),
                      label: const Text('Charger plus de dossiers'),
                    ),
            ),
          );
        }
        final item = rows[i];
        final a = item.alerte;
        final id = item.alerteId;
        final numero = a['numero_alerte']?.toString() ?? '#$id';
        final patient = a['user_full_name']?.toString() ?? 'Assuré';
        final priorite = a['priorite']?.toString() ?? '';
        final created = a['created_at'];
        String dateStr = '';
        if (created != null) {
          try {
            dateStr = df.format(DateTime.parse(created.toString()).toLocal());
          } catch (_) {}
        }
        final step = item.step;
        final label = referentStepLabel(step);
        final accent = _accentForStep(step);
        final pending = step == ReferentPipelineStep.sinistre ||
            step == ReferentPipelineStep.rapport ||
            step == ReferentPipelineStep.facture;
        final souscription = a['numero_souscription']?.toString();
        final hospital = a['assigned_hospital'];
        String? hospitalLine;
        if (hospital is Map) {
          final nom = hospital['nom']?.toString();
          final ville = hospital['ville']?.toString();
          final pays = hospital['pays']?.toString();
          final loc = [ville, pays].where((e) => e != null && e.isNotEmpty).join(', ');
          hospitalLine = [nom, if (loc.isNotEmpty) loc].whereType<String>().join(' • ');
          final dist = a['distance_to_hospital_km'];
          if (dist != null) {
            hospitalLine = '$hospitalLine (${dist.toString()} km)';
          }
        }
        final updated = a['updated_at'];
        String updatedStr = '';
        if (updated != null) {
          try {
            updatedStr = df.format(DateTime.parse(updated.toString()).toLocal());
          } catch (_) {}
        }

        return Card(
          margin: const EdgeInsets.only(bottom: 10),
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            leading: CircleAvatar(
              backgroundColor: accent.withValues(alpha: 0.15),
              child: Icon(
                step == ReferentPipelineStep.resolu
                    ? Icons.check_circle_outline
                    : Icons.folder_shared_outlined,
                color: accent,
              ),
            ),
            title: Text(numero, style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 4),
                Text(patient),
                if (souscription != null && souscription.isNotEmpty)
                  Text(
                    'Souscription : $souscription',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                  ),
                if (hospitalLine != null && hospitalLine.isNotEmpty)
                  Text(
                    hospitalLine,
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                  ),
                Text(
                  label,
                  style: TextStyle(
                    color: pending ? accent : Colors.blueGrey.shade700,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
                if (priorite.isNotEmpty)
                  Text(
                    'Priorité : $priorite',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                  ),
                if (dateStr.isNotEmpty)
                  Text(
                    'Créée le $dateStr',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
                if (updatedStr.isNotEmpty)
                  Text(
                    'Mise à jour $updatedStr',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
              ],
            ),
            isThreeLine: true,
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              context.push('/referent/dossier/$id').then((_) => widget.onRefresh());
            },
          ),
        );
        },
      ),
    );
  }
}
