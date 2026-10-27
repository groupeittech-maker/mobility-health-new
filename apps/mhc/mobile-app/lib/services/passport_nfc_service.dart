import 'package:dmrtd/dmrtd.dart';

/// Données MRZ nécessaires à l'authentification BAC de la puce.
/// Sans elles, impossible d'ouvrir le canal sécurisé — c'est ce qui rend la
/// lecture NFC résistante aux interceptions passives.
class PassportBacKeys {
  final String documentNumber;
  final DateTime birthDate;
  final DateTime expiryDate;

  const PassportBacKeys({
    required this.documentNumber,
    required this.birthDate,
    required this.expiryDate,
  });
}

/// Octets bruts lus sur la puce — envoyés tels quels au serveur Trusdy qui
/// refait toute l'authentification passive (hashes DG, signature SOD, chaîne
/// CSCA). L'app ne « déclare » jamais un succès.
class PassportChipData {
  final List<int> efCom;
  final List<int> efSod;
  final List<int>? dg1;
  final List<int>? dg2;

  const PassportChipData({
    required this.efCom,
    required this.efSod,
    this.dg1,
    this.dg2,
  });
}

class PassportNfcException implements Exception {
  final String code;
  final String message;
  const PassportNfcException(this.code, this.message);
  @override
  String toString() => message;
}

typedef NfcProgressCallback = void Function(int percent, String message);

/// Lecteur NFC eMRTD basé sur dmrtd (ICAO 9303, session BAC).
///
/// Parcours : disponibilité → connexion → session BAC → lecture des fichiers.
/// EF.COM et EF.SOD sont obligatoires pour l'authentification passive ;
/// DG1/DG2 sont lus quand la puce les annonce.
class PassportNfcService {
  /// Lit la puce du passeport. [keys] dérive du MRZ saisi/scanné par
  /// l'utilisateur. La session est refermée quoi qu'il arrive.
  Future<PassportChipData> readPassport(
    PassportBacKeys keys, {
    NfcProgressCallback? onProgress,
  }) async {
    final nfc = NfcProvider();
    try {
      onProgress?.call(5, 'Approchez le téléphone du passeport…');
      try {
        await nfc.connect(
            iosAlertMessage: 'Placez le passeport sous le téléphone');
      } catch (_) {
        throw const PassportNfcException(
          'NFC_UNAVAILABLE',
          'NFC indisponible — activez-le sur ce téléphone puis réessayez.',
        );
      }

      final passport = Passport(nfc);
      final accessKey = DBAKey(
        keys.documentNumber.toUpperCase().replaceAll(' ', ''),
        keys.birthDate,
        keys.expiryDate,
      );

      // Session BAC — la grande majorité des passeports eMRTD la supporte.
      // (PACE via EF.CardAccess : à ajouter pour les puces qui n'ont plus BAC.)
      try {
        onProgress?.call(15, 'Ouverture du canal sécurisé (BAC)…');
        await passport.startSession(accessKey);
      } catch (_) {
        throw const PassportNfcException(
          'BAC_FAILED',
          'Vérifiez le numéro de document et les dates — '
              'la puce refuse les clés de lecture.',
        );
      }

      onProgress?.call(35, 'Lecture EF.COM…');
      final efCom = await passport.readEfCOM();
      onProgress?.call(55, 'Lecture EF.SOD…');
      final efSod = await passport.readEfSOD();
      onProgress?.call(70, 'Lecture DG1…');
      final dg1 = await passport.readEfDG1();
      onProgress?.call(85, 'Lecture DG2 (portrait)…');
      EfDG2? dg2;
      try {
        dg2 = await passport.readEfDG2();
      } catch (_) {
        // Certaines puces exposent peu de DG2 ; le serveur tranchera
        // (INDETERMINATE) plutôt que l'app ne fabrique un succès.
        dg2 = null;
      }
      onProgress?.call(95, 'Lecture terminée');

      return PassportChipData(
        efCom: efCom.toBytes(),
        efSod: efSod.toBytes(),
        dg1: dg1.toBytes(),
        dg2: dg2?.toBytes(),
      );
    } on PassportNfcException {
      rethrow;
    } catch (e) {
      throw PassportNfcException(
        'READ_FAILED',
        'Lecture impossible — gardez le passeport immobile '
            'sous le téléphone pendant toute la lecture. ($e)',
      );
    } finally {
      try {
        await nfc.disconnect();
      } catch (_) {}
    }
  }
}
