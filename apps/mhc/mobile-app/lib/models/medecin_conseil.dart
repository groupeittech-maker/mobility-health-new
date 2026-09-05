/// Coordonnées d'un médecin-conseil (snapshot affichable hors ligne).
class MedecinConseilContact {
  const MedecinConseilContact({
    required this.id,
    this.nom,
    this.telephone,
    this.email,
  });

  final int id;
  final String? nom;
  final String? telephone;
  final String? email;

  bool get hasAnyContact =>
      (nom != null && nom!.trim().isNotEmpty) ||
      (telephone != null && telephone!.trim().isNotEmpty) ||
      (email != null && email!.trim().isNotEmpty);

  factory MedecinConseilContact.fromJson(Map<String, dynamic> json) {
    return MedecinConseilContact(
      id: json['id'] is int ? json['id'] as int : int.tryParse('${json['id']}') ?? 0,
      nom: (json['nom'] as String?)?.trim(),
      telephone: (json['telephone'] as String?)?.trim(),
      email: (json['email'] as String?)?.trim(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'nom': nom,
        'telephone': telephone,
        'email': email,
      };
}

/// Association souscription / destination / médecin-conseil.
class MedecinConseilAssignment {
  const MedecinConseilAssignment({
    required this.souscriptionId,
    this.numeroSouscription,
    this.statutSouscription,
    this.destination,
    this.destinationCountryId,
    this.destinationCountryName,
    this.medecinConseil,
  });

  final int souscriptionId;
  final String? numeroSouscription;
  final String? statutSouscription;
  final String? destination;
  final int? destinationCountryId;
  final String? destinationCountryName;
  final MedecinConseilContact? medecinConseil;

  bool get hasContact => medecinConseil?.hasAnyContact == true;

  String get destinationLabel {
    final display = destination?.trim();
    if (display != null && display.isNotEmpty) return display;
    return destinationCountryName?.trim().isNotEmpty == true
        ? destinationCountryName!.trim()
        : 'Destination non renseignée';
  }

  factory MedecinConseilAssignment.fromJson(Map<String, dynamic> json) {
    final raw = json['medecin_conseil'];
    return MedecinConseilAssignment(
      souscriptionId: json['souscription_id'] is int
          ? json['souscription_id'] as int
          : int.tryParse('${json['souscription_id']}') ?? 0,
      numeroSouscription: json['numero_souscription'] as String?,
      statutSouscription: json['statut_souscription'] as String?,
      destination: json['destination'] as String?,
      destinationCountryId: json['destination_country_id'] is int
          ? json['destination_country_id'] as int
          : int.tryParse('${json['destination_country_id'] ?? ''}'),
      destinationCountryName: json['destination_country_name'] as String?,
      medecinConseil: raw is Map<String, dynamic> ? MedecinConseilContact.fromJson(raw) : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'souscription_id': souscriptionId,
        'numero_souscription': numeroSouscription,
        'statut_souscription': statutSouscription,
        'destination': destination,
        'destination_country_id': destinationCountryId,
        'destination_country_name': destinationCountryName,
        'medecin_conseil': medecinConseil?.toJson(),
      };
}
