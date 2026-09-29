import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../core/constants/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_states.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../models/destination.dart';
import '../../models/subscription.dart';
import '../../services/api_services.dart';

/// « Modifier ma destination » (kit) : changement possible uniquement dans la
/// zone souscrite ; billet et motif joints. Hors zone → nouvelle police.
class ChangeDestinationScreen extends StatefulWidget {
  const ChangeDestinationScreen({super.key});

  @override
  State<ChangeDestinationScreen> createState() =>
      _ChangeDestinationScreenState();
}

class _ChangeDestinationScreenState extends State<ChangeDestinationScreen> {
  final SubscriptionsService _subsService = SubscriptionsService();
  final DestinationsService _destinationsService = DestinationsService();
  final VoyageDocumentsService _documentsService = VoyageDocumentsService();
  final DestinationChangesService _changesService = DestinationChangesService();

  SubscriptionModel? _subscription;
  List<DestinationCountryModel> _countries = const [];
  DestinationCountryModel? _newDestination;
  final _motifController = TextEditingController();
  String? _billetPath;
  String? _pendingDestination;
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
    _motifController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final subs = await _subsService.getSubscriptions(limit: 200);
      final active = subs.where((s) => s.isActive).toList();
      final countries = await _destinationsService.getDestinationCountries();
      String? pendingDest;
      if (active.isNotEmpty) {
        try {
          final changes =
              await _changesService.getDestinationChanges(active.first.id);
          final pending = changes
              .where((c) => c['statut'] == 'en_attente')
              .toList();
          if (pending.isNotEmpty) {
            pendingDest = (pending.first['nouvelle_destination'] ??
                    pending.first['destination_country_name'] ??
                    '')
                .toString();
          }
        } catch (_) {}
      }
      if (mounted) {
        setState(() {
          _subscription = active.isNotEmpty ? active.first : null;
          _countries = countries;
          _pendingDestination = pendingDest;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _loading = false;
        });
      }
    }
  }

  Future<void> _pickBillet() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png'],
    );
    final path = result?.files.single.path;
    if (path != null) setState(() => _billetPath = path);
  }

  Future<void> _submit() async {
    final sub = _subscription;
    final dest = _newDestination;
    if (sub == null || dest == null) {
      setState(() => _error = 'Sélectionnez une nouvelle destination.');
      return;
    }
    if (_billetPath == null) {
      setState(() => _error = 'Joignez votre nouveau billet de voyage.');
      return;
    }
    final projetId = sub.projetVoyageId;
    if (projetId == null) {
      setState(() => _error = 'Aucun voyage associé à cette police.');
      return;
    }
    setState(() {
      _error = null;
      _sending = true;
    });
    try {
      final doc = await _documentsService.uploadDocument(
        projetId: projetId,
        filePath: _billetPath!,
        docType: 'billet',
      );
      final motif = _motifController.text.trim();
      await _changesService.requestDestinationChange(
        subscriptionId: sub.id,
        destinationCountryId: dest.id,
        motif: motif.isEmpty ? null : motif,
        billetDocumentId: doc['id'] as int?,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Demande envoyée. Elle sera validée par nos équipes (zone souscrite uniquement).',
          ),
          backgroundColor: AppColors.success,
        ),
      );
      Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final projet = _subscription?.projetVoyage;
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: const MhAppBar(title: 'Modifier ma destination'),
      body: _loading
          ? const MhLoadingView()
          : _subscription == null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      _error ??
                          'Aucune police active : le changement de destination '
                              'nécessite une souscription en cours de validité.',
                      textAlign: TextAlign.center,
                      style:
                          const TextStyle(color: AppColors.mutedText, height: 1.5),
                    ),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
                  children: [
                    MHSurfaceCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Police actuelle',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: AppColors.secondary,
                              fontSize: 13,
                            ),
                          ),
                          const Divider(height: 18),
                          _infoRow(
                            'Zone souscrite',
                            _subscription!.produitAssurance
                                    ?.geographicalZonesCount
                                    .toString() ??
                                'À vérifier',
                          ),
                          _infoRow(
                            'Destination actuelle',
                            projet?.destinationDisplay ??
                                projet?.destination ??
                                'À vérifier',
                          ),
                        ],
                      ),
                    ),
                    if (_pendingDestination != null) ...[
                      const SizedBox(height: 14),
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: const Color(0xFFFFF7E8),
                          borderRadius: BorderRadius.circular(12),
                          border:
                              Border.all(color: const Color(0xFFF3D9A4)),
                        ),
                        child: Text(
                          'Une demande de changement de destination '
                          '${_pendingDestination!.isEmpty ? '' : 'vers $_pendingDestination '}'
                          'est déjà en attente de validation.',
                          style: const TextStyle(
                            fontSize: 12,
                            color: AppColors.secondary,
                            height: 1.45,
                          ),
                        ),
                      ),
                    ],
                    const SizedBox(height: 14),
                    DropdownButtonFormField<DestinationCountryModel>(
                      initialValue: _newDestination,
                      decoration: MHSurfaceCard.input(
                        labelText: 'Nouvelle destination *',
                      ),
                      items: _countries
                          .map(
                            (c) => DropdownMenuItem(
                              value: c,
                              child: Text(c.nom),
                            ),
                          )
                          .toList(),
                      onChanged: (v) => setState(() => _newDestination = v),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _motifController,
                      maxLines: 3,
                      decoration: MHSurfaceCard.input(
                        labelText: 'Motif du changement',
                        hintText: 'Décrivez brièvement',
                      ),
                    ),
                    const SizedBox(height: 12),
                    InkWell(
                      onTap: _sending ? null : _pickBillet,
                      borderRadius: BorderRadius.circular(10),
                      child: InputDecorator(
                        decoration: MHSurfaceCard.input(
                          labelText: 'Nouveau billet de voyage *',
                          suffixIcon: const Icon(Icons.attach_file,
                              color: AppColors.mutedText),
                        ),
                        child: Text(
                          _billetPath == null
                              ? 'Joindre le billet'
                              : _billetPath!.split(RegExp(r'[\\/]')).last,
                          style: TextStyle(
                            color: _billetPath == null
                                ? AppColors.mutedText
                                : const Color(0xFF332542),
                            fontSize: 13,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEAFAF7),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFD7F1EC)),
                      ),
                      child: const Text(
                        'Le changement est possible uniquement dans la zone couverte '
                        'par cette police. Pour une destination hors zone, souscrivez '
                        'une nouvelle police.',
                        style: TextStyle(
                          fontSize: 12,
                          color: AppColors.mutedText,
                          height: 1.45,
                        ),
                      ),
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        _error!,
                        style: const TextStyle(
                            color: AppColors.danger, fontSize: 13),
                      ),
                    ],
                    const SizedBox(height: 16),
                    MHGradientButton(
                      label: 'Soumettre la demande',
                      loading: _sending,
                      onPressed: _submit,
                    ),
                  ],
                ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: const TextStyle(fontSize: 12, color: AppColors.mutedText)),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Color(0xFF332542),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
