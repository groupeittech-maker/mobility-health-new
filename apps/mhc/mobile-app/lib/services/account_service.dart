import '../core/network/api_client.dart';

/// Compte & sécurité (workflow MyMHC V3 §3.2) : mot de passe, sessions,
/// paramètres (langue, notifications), adresse, suppression de compte.
class AccountService {
  AccountService._();
  static final AccountService instance = AccountService._();

  final ApiClient _api = ApiClient();

  /// Retourne les nouveaux jetons (l'ancienne session est révoquée).
  Future<Map<String, dynamic>> changePassword({
    required String currentPassword,
    required String newPassword,
    required String confirmPassword,
  }) async {
    return _api.post<Map<String, dynamic>>(
      '/auth/change-password',
      body: {
        'current_password': currentPassword,
        'new_password': newPassword,
        'confirm_password': confirmPassword,
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  /// Ferme toutes les sessions (tous les appareils), y compris celle-ci.
  Future<void> revokeAllSessions() async {
    await _api.post<dynamic>('/auth/sessions/revoke-all', body: const {});
  }

  Future<Map<String, dynamic>> getSettings() async {
    return _api.get<Map<String, dynamic>>(
      '/users/me/settings',
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  /// `langue` : fr | en | es | pt | ar. Retourne les paramètres + langues disponibles.
  Future<Map<String, dynamic>> updateSettings({
    String? langue,
    bool? notificationsNonEssentielles,
  }) async {
    return _api.put<Map<String, dynamic>>(
      '/users/me/settings',
      body: {
        if (langue != null) 'langue': langue,
        if (notificationsNonEssentielles != null)
          'notifications_non_essentielles': notificationsNonEssentielles,
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> updateAddress(String adresse) async {
    return _api.put<Map<String, dynamic>>(
      '/users/me/address',
      body: {'adresse': adresse.trim()},
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  /// Suppression du compte (confirmation « SUPPRIMER » côté UI). Les assurances
  /// actives sont conservées conformément au contrat ; le corps de la réponse
  /// les compte (`assurances_actives`).
  Future<Map<String, dynamic>> deleteAccount({
    required String password,
    required String confirmation,
  }) async {
    return _api.deleteWithBody<Map<String, dynamic>>(
      '/users/me',
      body: {'password': password, 'confirmation': confirmation},
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }
}

/// Demandes de modification du profil soumises à validation MHC (§3.3, §4.3).
class ProfileChangeService {
  ProfileChangeService._();
  static final ProfileChangeService instance = ProfileChangeService._();

  final ApiClient _api = ApiClient();

  /// Champs modifiables : full_name, date_naissance (AAAA-MM-JJ), nationalite,
  /// pays_residence, numero_passeport, validite_passeport.
  Future<Map<String, dynamic>> createRequest({
    required Map<String, String> champs,
    String? pieceIdentiteNom,
    String? pieceIdentiteDataUrl,
  }) async {
    return _api.post<Map<String, dynamic>>(
      '/profile-change-requests',
      body: {
        'champs': champs,
        if (pieceIdentiteDataUrl != null) 'piece_identite_nom': pieceIdentiteNom ?? 'piece-identite',
        if (pieceIdentiteDataUrl != null) 'piece_identite_data_url': pieceIdentiteDataUrl,
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  Future<List<Map<String, dynamic>>> myRequests() async {
    final list = await _api.get<List<dynamic>>(
      '/profile-change-requests/me',
      fromJson: (d) => d as List<dynamic>,
    );
    return list.whereType<Map<String, dynamic>>().toList();
  }
}

/// Enfants bénéficiaires (§4.3) : < 18 ans, gérés par le parent.
class EnfantsService {
  EnfantsService._();
  static final EnfantsService instance = EnfantsService._();

  final ApiClient _api = ApiClient();

  Future<List<Map<String, dynamic>>> list() async {
    final data = await _api.get<List<dynamic>>(
      '/users/me/enfants',
      fromJson: (d) => d as List<dynamic>,
    );
    return data.whereType<Map<String, dynamic>>().toList();
  }

  Map<String, dynamic> _body({
    required String nom,
    required String dateNaissance,
    String? prenom,
    String? nationalite,
    String? paysResidence,
    String? numeroPiece,
    String? validitePiece,
    String? lienParente,
    String? photoDataUrl,
    String? copiePieceDataUrl,
  }) =>
      {
        'nom': nom.trim(),
        'date_naissance': dateNaissance,
        if (prenom != null && prenom.trim().isNotEmpty) 'prenom': prenom.trim(),
        if (nationalite != null && nationalite.trim().isNotEmpty) 'nationalite': nationalite.trim(),
        if (paysResidence != null && paysResidence.trim().isNotEmpty) 'pays_residence': paysResidence.trim(),
        if (numeroPiece != null && numeroPiece.trim().isNotEmpty) 'numero_piece': numeroPiece.trim(),
        if (validitePiece != null && validitePiece.trim().isNotEmpty) 'validite_piece': validitePiece,
        if (lienParente != null && lienParente.trim().isNotEmpty) 'lien_parente': lienParente.trim(),
        if (photoDataUrl != null) 'photo_data_url': photoDataUrl,
        if (copiePieceDataUrl != null) 'copie_piece_data_url': copiePieceDataUrl,
      };

  Future<Map<String, dynamic>> create({
    required String nom,
    required String dateNaissance,
    String? prenom,
    String? nationalite,
    String? paysResidence,
    String? numeroPiece,
    String? validitePiece,
    String? lienParente,
    String? photoDataUrl,
    String? copiePieceDataUrl,
  }) async {
    return _api.post<Map<String, dynamic>>(
      '/users/me/enfants',
      body: _body(
        nom: nom, dateNaissance: dateNaissance, prenom: prenom, nationalite: nationalite,
        paysResidence: paysResidence,
        numeroPiece: numeroPiece, validitePiece: validitePiece, lienParente: lienParente,
        photoDataUrl: photoDataUrl, copiePieceDataUrl: copiePieceDataUrl,
      ),
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> update(
    int enfantId, {
    required String nom,
    required String dateNaissance,
    String? prenom,
    String? nationalite,
    String? paysResidence,
    String? numeroPiece,
    String? validitePiece,
    String? lienParente,
    String? photoDataUrl,
    String? copiePieceDataUrl,
  }) async {
    return _api.put<Map<String, dynamic>>(
      '/users/me/enfants/$enfantId',
      body: _body(
        nom: nom, dateNaissance: dateNaissance, prenom: prenom, nationalite: nationalite,
        paysResidence: paysResidence,
        numeroPiece: numeroPiece, validitePiece: validitePiece, lienParente: lienParente,
        photoDataUrl: photoDataUrl, copiePieceDataUrl: copiePieceDataUrl,
      ),
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  Future<void> delete(int enfantId) async {
    await _api.delete('/users/me/enfants/$enfantId');
  }
}

/// Réclamations (§8.1) : dépôt, suivi, échanges, contestation.
class ReclamationsService {
  ReclamationsService._();
  static final ReclamationsService instance = ReclamationsService._();

  final ApiClient _api = ApiClient();

  /// Catégories, délais et contacts d'urgence médicale.
  Future<Map<String, dynamic>> metadata() async {
    return _api.get<Map<String, dynamic>>(
      '/reclamations/categories',
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  Future<List<Map<String, dynamic>>> myReclamations() async {
    final list = await _api.get<List<dynamic>>(
      '/reclamations',
      fromJson: (d) => d as List<dynamic>,
    );
    return list.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> detail(int id) async {
    return _api.get<Map<String, dynamic>>(
      '/reclamations/$id',
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> create({
    required String categorie,
    required String objet,
    required String description,
    int? souscriptionId,
    List<Map<String, dynamic>>? piecesJointes,
  }) async {
    return _api.post<Map<String, dynamic>>(
      '/reclamations',
      body: {
        'categorie': categorie,
        'objet': objet.trim(),
        'description': description.trim(),
        if (souscriptionId != null) 'souscription_id': souscriptionId,
        if (piecesJointes != null && piecesJointes.isNotEmpty)
          'pieces_jointes': piecesJointes,
      },
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  Future<Map<String, dynamic>> addMessage(int id, String message) async {
    return _api.post<Map<String, dynamic>>(
      '/reclamations/$id/messages',
      body: {'message': message.trim()},
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }

  /// Contestation d'une réclamation clôturée : crée une réclamation liée.
  Future<Map<String, dynamic>> contest(int id, String message) async {
    return _api.post<Map<String, dynamic>>(
      '/reclamations/$id/contestation',
      body: {'message': message.trim()},
      fromJson: (d) => d as Map<String, dynamic>,
    );
  }
}
