/// Parse des valeurs JSON hétérogènes (int, double, String) depuis l'API FastAPI/Pydantic.
num? parseJsonNum(dynamic value) {
  if (value == null) return null;
  if (value is num) return value;
  if (value is String) {
    final trimmed = value.trim();
    if (trimmed.isEmpty) return null;
    return num.tryParse(trimmed.replaceAll(RegExp(r'[\s\u00a0]'), '').replaceAll(',', '.'));
  }
  return null;
}

int? parseJsonInt(dynamic value) {
  final n = parseJsonNum(value);
  return n?.toInt();
}

double? parseJsonDouble(dynamic value) {
  final n = parseJsonNum(value);
  return n?.toDouble();
}

String? formatJsonCoord(dynamic value, {int fractionDigits = 4}) {
  final n = parseJsonDouble(value);
  if (n == null) return null;
  return n.toStringAsFixed(fractionDigits);
}
