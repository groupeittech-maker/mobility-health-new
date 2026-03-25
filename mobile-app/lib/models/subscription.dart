import 'product.dart';

/// Souscription (SouscriptionResponse simplifié pour la liste).
class SubscriptionModel {
  final int id;
  final String numeroSouscription;
  final double prixApplique;
  final DateTime dateDebut;
  final DateTime? dateFin;
  final String statut;
  final String? notes;
  final int userId;
  final int produitAssuranceId;
  final int? projetVoyageId;
  final ProductModel? produitAssurance;
  final ProjetVoyageModel? projetVoyage;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? demandeResiliation;
  final DateTime? demandeResiliationDate;
  final String? demandeResiliationNotes;

  SubscriptionModel({
    required this.id,
    required this.numeroSouscription,
    required this.prixApplique,
    required this.dateDebut,
    this.dateFin,
    required this.statut,
    this.notes,
    required this.userId,
    required this.produitAssuranceId,
    this.projetVoyageId,
    this.produitAssurance,
    this.projetVoyage,
    required this.createdAt,
    required this.updatedAt,
    this.demandeResiliation,
    this.demandeResiliationDate,
    this.demandeResiliationNotes,
  });

  bool get isActive => statut == 'active';
  bool get hasPendingResiliation => demandeResiliation == 'pending';
  bool get canRequestResiliation => isActive && demandeResiliation != 'pending' && demandeResiliation != 'approved';
  bool get isPending => statut == 'en_attente' || statut == 'pending';
  bool get isExpired => statut == 'expiree' || statut == 'expired';

  factory SubscriptionModel.fromJson(Map<String, dynamic> json) {
    return SubscriptionModel(
      id: json['id'] as int,
      numeroSouscription: json['numero_souscription'] as String? ?? '',
      prixApplique: (json['prix_applique'] is num)
          ? (json['prix_applique'] as num).toDouble()
          : double.tryParse(json['prix_applique']?.toString() ?? '0') ?? 0,
      dateDebut: DateTime.tryParse(json['date_debut']?.toString() ?? '') ?? DateTime.now(),
      dateFin: json['date_fin'] != null ? DateTime.tryParse(json['date_fin'].toString()) : null,
      statut: (json['statut'] as String? ?? 'en_attente').toString().toLowerCase(),
      notes: json['notes'] as String?,
      userId: json['user_id'] as int,
      produitAssuranceId: json['produit_assurance_id'] as int,
      projetVoyageId: json['projet_voyage_id'] as int?,
      produitAssurance: json['produit_assurance'] != null
          ? ProductModel.fromJson(json['produit_assurance'] as Map<String, dynamic>)
          : null,
      projetVoyage: json['projet_voyage'] != null
          ? ProjetVoyageModel.fromJson(json['projet_voyage'] as Map<String, dynamic>)
          : null,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? '') ?? DateTime.now(),
      demandeResiliation: json['demande_resiliation'] as String?,
      demandeResiliationDate: json['demande_resiliation_date'] != null
          ? DateTime.tryParse(json['demande_resiliation_date'].toString())
          : null,
      demandeResiliationNotes: json['demande_resiliation_notes'] as String?,
    );
  }
}

/// Projet de voyage (pour souscription).
class ProjetVoyageModel {
  final int id;
  final int userId;
  final String titre;
  final String? description;
  final String destination;
  final int? destinationCountryId;
  final String? destinationCountryName;
  final String? destinationDisplay;
  final DateTime dateDepart;
  final DateTime? dateRetour;
  final int nombreParticipants;
  final String statut;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  ProjetVoyageModel({
    required this.id,
    required this.userId,
    required this.titre,
    this.description,
    required this.destination,
    this.destinationCountryId,
    this.destinationCountryName,
    this.destinationDisplay,
    required this.dateDepart,
    this.dateRetour,
    this.nombreParticipants = 1,
    required this.statut,
    this.notes,
    required this.createdAt,
    required this.updatedAt,
  });

  factory ProjetVoyageModel.fromJson(Map<String, dynamic> json) {
    return ProjetVoyageModel(
      id: json['id'] as int,
      userId: json['user_id'] as int,
      titre: json['titre'] as String? ?? '',
      description: json['description'] as String?,
      destination: json['destination'] as String? ?? '',
      destinationCountryId: json['destination_country_id'] as int?,
      destinationCountryName: json['destination_country_name'] as String?,
      destinationDisplay: json['destination_display'] as String?,
      dateDepart: DateTime.tryParse(json['date_depart']?.toString() ?? '') ?? DateTime.now(),
      dateRetour: json['date_retour'] != null ? DateTime.tryParse(json['date_retour'].toString()) : null,
      nombreParticipants: json['nombre_participants'] as int? ?? 1,
      statut: json['statut'] as String? ?? 'en_planification',
      notes: json['notes'] as String?,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? '') ?? DateTime.now(),
    );
  }
}
