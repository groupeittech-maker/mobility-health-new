import 'package:flutter/material.dart';

/// Dialogue avec champ texte — le [TextEditingController] est géré par le State (pas de dispose prématuré).
class PromptTextDialog extends StatefulWidget {
  const PromptTextDialog({
    super.key,
    required this.title,
    required this.hint,
    this.maxLines = 3,
    this.confirmLabel = 'Confirmer',
  });

  final String title;
  final String hint;
  final int maxLines;
  final String confirmLabel;

  @override
  State<PromptTextDialog> createState() => _PromptTextDialogState();
}

class _PromptTextDialogState extends State<PromptTextDialog> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: TextField(
        controller: _controller,
        decoration: InputDecoration(hintText: widget.hint),
        maxLines: widget.maxLines,
        autofocus: true,
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Annuler'),
        ),
        FilledButton(
          onPressed: () => Navigator.pop(context, _controller.text.trim()),
          child: Text(widget.confirmLabel),
        ),
      ],
    );
  }
}

Future<String?> showPromptTextDialog(
  BuildContext context, {
  required String title,
  required String hint,
  int maxLines = 3,
  String confirmLabel = 'Confirmer',
}) {
  return showDialog<String?>(
    context: context,
    builder: (_) => PromptTextDialog(
      title: title,
      hint: hint,
      maxLines: maxLines,
      confirmLabel: confirmLabel,
    ),
  );
}
