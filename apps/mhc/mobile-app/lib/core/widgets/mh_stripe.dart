import 'package:flutter/material.dart';

/// Bande graphique chevron du kit MyMHC (bas de chaque écran, ~31 px).
/// Chevrons alternés turquoise / violet alignés sur la charte.
class MhStripe extends StatelessWidget {
  const MhStripe({super.key, this.height = 26});

  final double height;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: height,
      width: double.infinity,
      child: CustomPaint(painter: _ChevronPainter()),
    );
  }
}

class _ChevronPainter extends CustomPainter {
  static const _colors = [
    Color(0xFF14AE98), // turquoise brand
    Color(0xFF4E267C), // violet brand
    Color(0xFF0E7C8C), // teal profond
    Color(0xFF2E86C8), // bleu
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;
    final chevronH = size.height;
    final halfW = chevronH * 0.9;

    var x = -halfW;
    var i = 0;
    while (x < size.width + halfW) {
      paint.color = _colors[i % _colors.length];
      final path = Path()
        ..moveTo(x, 0)
        ..lineTo(x + halfW, chevronH / 2)
        ..lineTo(x, chevronH)
        ..lineTo(x + halfW * 0.45, chevronH)
        ..lineTo(x + halfW * 1.45, chevronH / 2)
        ..lineTo(x + halfW * 0.45, 0)
        ..close();
      canvas.drawPath(path, paint);
      x += halfW * 0.55;
      i++;
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
