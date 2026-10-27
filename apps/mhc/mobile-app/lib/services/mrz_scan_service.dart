import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';

/// Extraction locale du MRZ d'un passeport pour pré-remplir les clés BAC
/// (numéro de document, naissance, expiration). Tout se fait sur l'appareil —
/// aucune image n'est envoyée à un service cloud par cette étape.
class MrzScanResult {
  final String documentNumber;
  final DateTime birthDate;
  final DateTime expiryDate;

  const MrzScanResult({
    required this.documentNumber,
    required this.birthDate,
    required this.expiryDate,
  });
}

class MrzScanException implements Exception {
  final String message;
  const MrzScanException(this.message);
  @override
  String toString() => message;
}

class MrzScanService {
  static const _mrzChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<';

  /// Photographie la zone MRZ (2 ou 3 lignes en bas de la page du passeport)
  /// et retourne les clés BAC extraites. Lance [MrzScanException] si aucune
  /// ligne MRZ valide n'est trouvée.
  Future<MrzScanResult?> scanFromCamera() async {
    final picker = ImagePicker();
    final photo = await picker.pickImage(
      source: ImageSource.camera,
      maxWidth: 1600,
      imageQuality: 85,
    );
    if (photo == null) return null; // annulé par l'utilisateur

    final recognizer = TextRecognizer();
    try {
      final recognized =
          await recognizer.processImage(InputImage.fromFilePath(photo.path));
      return parseMrz(recognized.text);
    } finally {
      await recognizer.close();
    }
  }

  /// Parse un texte brut contenant un MRZ (TD3 2×44 ou TD1 3×30).
  static MrzScanResult parseMrz(String raw) {
    final lines = raw
        .toUpperCase()
        .split(RegExp(r'\r?\n'))
        .map((line) => line.replaceAll(RegExp(r'[^A-Z0-9<]'), '<'))
        .where((line) => line.length >= 28)
        .toList();

    for (var i = 0; i + 1 < lines.length; i++) {
      final first = lines[i];
      final second = lines[i + 1];
      if (!_looksLikeMrz(first) || !_looksLikeMrz(second)) continue;

      // Ligne 1 : <type><pays><numéro document 9 chars>… (TD3/TD1) puis champs
      // Ligne 2 : <dob 6><chk><sex><expiry 6><chk>…
      if (first.length < 14 || second.length < 14) continue;
      final documentNumber = first.substring(5, 14).replaceAll('<', '');
      final birthDigits = second.substring(0, 6);
      final expiryDigits = second.substring(8, 14);
      if (documentNumber.isEmpty ||
          !_digitsOnly(birthDigits) ||
          !_digitsOnly(expiryDigits)) {
        continue;
      }
      return MrzScanResult(
        documentNumber: documentNumber,
        birthDate: _yyToDate(birthDigits),
        expiryDate: _yyToDate(expiryDigits),
      );
    }
    throw const MrzScanException(
      'Aucune ligne MRZ lisible — recadrez sur les 2-3 lignes du bas du '
      'document, sans reflets.',
    );
  }

  static bool _looksLikeMrz(String line) =>
      line.split('').every((c) => _mrzChars.contains(c)) &&
      line.contains('<'); // les MRZ contiennent toujours des séparateurs '<'

  static bool _digitsOnly(String s) =>
      s.isNotEmpty && s.split('').every((c) => c.codeUnitAt(0) >= 48 && c.codeUnitAt(0) <= 57);

  /// AAMMJJ → DateTime. Pivot : si l'année 2 chiffres dépasse l'année courante
  /// + 10 ans, elle appartient au siècle précédent.
  static DateTime _yyToDate(String yymmdd) {
    final yy = int.parse(yymmdd.substring(0, 2));
    final mm = int.parse(yymmdd.substring(2, 4));
    final dd = int.parse(yymmdd.substring(4, 6));
    final pivot = (DateTime.now().year % 100 + 10) % 100;
    final year = yy > pivot ? 1900 + yy : 2000 + yy;
    return DateTime(year, mm.clamp(1, 12), dd.clamp(1, 31));
  }
}
