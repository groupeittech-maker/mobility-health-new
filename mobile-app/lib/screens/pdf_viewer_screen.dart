import 'dart:io';

import 'package:flutter/material.dart';
import 'package:pdfx/pdfx.dart';

import '../core/constants/app_colors.dart';

/// Affiche un PDF depuis un fichier local (téléchargé) directement dans l'app.
class PdfViewerScreen extends StatefulWidget {
  const PdfViewerScreen({
    super.key,
    required this.filePath,
    this.title = 'Attestation',
  });

  final String filePath;
  final String title;

  @override
  State<PdfViewerScreen> createState() => _PdfViewerScreenState();
}

class _PdfViewerScreenState extends State<PdfViewerScreen> {
  PdfControllerPinch? _controller;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadPdf();
  }

  void _loadPdf() {
    if (!File(widget.filePath).existsSync()) {
      setState(() {
        _error = 'Fichier introuvable';
        _loading = false;
      });
      return;
    }
    setState(() {
      _controller = PdfControllerPinch(
        document: PdfDocument.openFile(widget.filePath),
        initialPage: 1,
      );
      _loading = false;
    });
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.error_outline, size: 48, color: AppColors.danger),
                        const SizedBox(height: 16),
                        Text(
                          _error!,
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: AppColors.danger),
                        ),
                        const SizedBox(height: 24),
                        FilledButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text('Fermer'),
                        ),
                      ],
                    ),
                  ),
                )
              : _controller != null
                  ? PdfViewPinch(
                      controller: _controller!,
                      scrollDirection: Axis.vertical,
                      onDocumentLoaded: (doc) {},
                      onDocumentError: (error) {
                        setState(() => _error = error.toString());
                      },
                    )
                  : const SizedBox.shrink(),
    );
  }
}
