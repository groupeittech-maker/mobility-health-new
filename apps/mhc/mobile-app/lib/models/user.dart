/// Modèle utilisateur (aligné sur UserResponse du backend).
class UserModel {
  final int id;
  final String email;
  final String username;
  final String? fullName;
  final String? dateNaissance;
  final String? telephone;
  final String? sexe;
  final String? paysResidence;
  final String? nationalite;
  final String? numeroPasseport;
  final String? validitePasseport;
  final String? nomContactUrgence;
  final String? contactUrgence;
  final bool isActive;
  final String role;
  final int? hospitalId;
  final String? hospitalNom;

  UserModel({
    required this.id,
    required this.email,
    required this.username,
    this.fullName,
    this.dateNaissance,
    this.telephone,
    this.sexe,
    this.paysResidence,
    this.nationalite,
    this.numeroPasseport,
    this.validitePasseport,
    this.nomContactUrgence,
    this.contactUrgence,
    required this.isActive,
    required this.role,
    this.hospitalId,
    this.hospitalNom,
  });

  String get displayName => fullName ?? username;

  /// Médecin référent MH (sinistres / validation urgences, rapports, factures médicales).
  bool get isMedecinReferentMh => role.toLowerCase() == 'medecin_referent_mh';

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      email: json['email'] as String,
      username: json['username'] as String,
      fullName: json['full_name'] as String?,
      dateNaissance: json['date_naissance']?.toString(),
      telephone: json['telephone'] as String?,
      sexe: json['sexe'] as String?,
      paysResidence: json['pays_residence'] as String?,
      nationalite: json['nationalite'] as String?,
      numeroPasseport: json['numero_passeport'] as String?,
      validitePasseport: json['validite_passeport']?.toString(),
      nomContactUrgence: json['nom_contact_urgence'] as String?,
      contactUrgence: json['contact_urgence'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      role: (json['role'] as String? ?? 'user').toLowerCase(),
      hospitalId: json['hospital_id'] as int?,
      hospitalNom: json['hospital_nom'] as String?,
    );
  }
}
