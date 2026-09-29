import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/constants/app_colors.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/mh_app_bar.dart';
import '../../core/widgets/mh_surface_card.dart';
import '../../services/api_services.dart';
import '../../services/auth_service.dart';

/// Écrans de modification du profil (kit « Compte et états ») :
/// adresse e-mail, téléphone, personne à contacter.

class _EditScaffold extends StatelessWidget {
  const _EditScaffold({
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: MhAppBar(title: title),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        child: child,
      ),
    );
  }
}

class _InfoBox extends StatelessWidget {
  const _InfoBox(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFEAFAF7),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFD7F1EC)),
      ),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 12,
          color: AppColors.mutedText,
          height: 1.45,
        ),
      ),
    );
  }
}

class _ErrorText extends StatelessWidget {
  const _ErrorText(this.message);
  final String? message;
  @override
  Widget build(BuildContext context) {
    if (message == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Text(
        message!,
        style: const TextStyle(color: AppColors.danger, fontSize: 13),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Modifier l'adresse e-mail — la nouvelle adresse est vérifiée avant d'être
// enregistrée : on met à jour puis on envoie le code sur la nouvelle adresse.
// ---------------------------------------------------------------------------
class EditEmailScreen extends StatefulWidget {
  const EditEmailScreen({super.key});

  @override
  State<EditEmailScreen> createState() => _EditEmailScreenState();
}

class _EditEmailScreenState extends State<EditEmailScreen> {
  final _controller = TextEditingController();
  final _codeController = TextEditingController();
  bool _loading = false;
  bool _codeSent = false;
  String? _error;
  String _currentEmail = '';

  @override
  void initState() {
    super.initState();
    AuthService.instance.getMe().then((u) {
      if (mounted) setState(() => _currentEmail = u.email);
    }).catchError((_) {});
  }

  String _maskEmail(String email) {
    final parts = email.split('@');
    if (parts.length != 2 || parts[0].length < 2) return email;
    return '${parts[0][0]}•••@${parts[1]}';
  }

  Future<void> _submit() async {
    final users = UsersService();
    if (!_codeSent) {
      final email = _controller.text.trim();
      if (!RegExp(r'^[\w\-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(email)) {
        setState(() => _error = 'Adresse e-mail invalide.');
        return;
      }
      setState(() {
        _error = null;
        _loading = true;
      });
      try {
        await users.requestEmailChange(email);
        if (!mounted) return;
        setState(() {
          _codeSent = true;
          _loading = false;
        });
      } catch (e) {
        if (mounted) {
          setState(() {
            _error = e.toString().replaceFirst('Exception: ', '');
            _loading = false;
          });
        }
      }
      return;
    }

    final code = _codeController.text.trim();
    if (code.length != 6) {
      setState(() => _error = 'Le code doit contenir 6 chiffres.');
      return;
    }
    setState(() {
      _error = null;
      _loading = true;
    });
    try {
      await users.confirmEmailChange(code);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Adresse e-mail mise à jour.'),
          backgroundColor: AppColors.success,
        ),
      );
      context.pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _loading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _codeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _EditScaffold(
      title: 'Modifier mon adresse e-mail',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          MHSurfaceCard(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Adresse actuelle',
                    style: TextStyle(fontSize: 12, color: AppColors.mutedText)),
                Text(
                  _maskEmail(_currentEmail),
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF332542),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _controller,
            keyboardType: TextInputType.emailAddress,
            enabled: !_codeSent,
            decoration: MHSurfaceCard.input(
              labelText: 'Nouvelle adresse e-mail *',
              hintText: 'nom@exemple.com',
            ),
          ),
          if (_codeSent) ...[
            const SizedBox(height: 14),
            MHSurfaceCard(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Confirmer l’adresse',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: AppColors.secondary,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Entrez le code reçu sur la nouvelle adresse e-mail.',
                    style:
                        TextStyle(fontSize: 12, color: AppColors.mutedText),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _codeController,
                    keyboardType: TextInputType.number,
                    textAlign: TextAlign.center,
                    decoration: MHSurfaceCard.input(hintText: '••••••'),
                  ),
                ],
              ),
            ),
          ] else ...[
            const SizedBox(height: 14),
            const _InfoBox(
              'Un code sera envoyé à la nouvelle adresse. '
              'Elle sera mise à jour après confirmation.',
            ),
          ],
          const SizedBox(height: 16),
          _ErrorText(_error),
          MHGradientButton(
            label: _codeSent ? 'Confirmer' : 'Envoyer le code',
            loading: _loading,
            onPressed: _submit,
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Modifier le téléphone — code envoyé au nouveau numéro.
// ---------------------------------------------------------------------------
class EditPhoneScreen extends StatefulWidget {
  const EditPhoneScreen({super.key});

  @override
  State<EditPhoneScreen> createState() => _EditPhoneScreenState();
}

class _EditPhoneScreenState extends State<EditPhoneScreen> {
  final _phoneController = TextEditingController();
  final _codeController = TextEditingController();
  bool _loading = false;
  bool _codeSent = false;
  String _channel = 'sms';
  String? _error;

  @override
  void dispose() {
    _phoneController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final users = UsersService();
    if (!_codeSent) {
      final phone = _phoneController.text.trim();
      if (phone.length < 8) {
        setState(() => _error = 'Numéro de téléphone invalide.');
        return;
      }
      setState(() {
        _error = null;
        _loading = true;
      });
      try {
        await users.requestPhoneChange(phone, channel: _channel);
        if (!mounted) return;
        setState(() {
          _codeSent = true;
          _loading = false;
        });
      } catch (e) {
        if (mounted) {
          setState(() {
            _error = e.toString().replaceFirst('Exception: ', '');
            _loading = false;
          });
        }
      }
      return;
    }

    final code = _codeController.text.trim();
    if (code.length != 6) {
      setState(() => _error = 'Le code doit contenir 6 chiffres.');
      return;
    }
    setState(() {
      _error = null;
      _loading = true;
    });
    try {
      await users.confirmPhoneChange(code);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Numéro de téléphone mis à jour.'),
          backgroundColor: AppColors.success,
        ),
      );
      context.pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _loading = false;
        });
      }
    }
  }

  Widget _channelChip(String value, IconData icon, String label) {
    final selected = _channel == value;
    return Expanded(
      child: InkWell(
        onTap: _codeSent ? null : () => setState(() => _channel = value),
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: selected ? const Color(0xFFE9F9F6) : Colors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: selected ? AppColors.brandTeal : const Color(0xFFE8E2F0),
              width: selected ? 1.6 : 1,
            ),
          ),
          child: Column(
            children: [
              Icon(
                icon,
                size: 18,
                color: selected ? const Color(0xFF087F72) : AppColors.secondary,
              ),
              const SizedBox(height: 2),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color:
                      selected ? const Color(0xFF087F72) : AppColors.secondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return _EditScaffold(
      title: 'Modifier mon téléphone',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            enabled: !_codeSent,
            decoration: MHSurfaceCard.input(
              labelText: 'Nouveau numéro *',
              hintText: '+242 •• •• •• ••',
              prefixIcon: const Icon(Icons.phone_outlined, size: 20),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _channelChip('sms', Icons.sms_outlined, 'SMS'),
              const SizedBox(width: 8),
              _channelChip('whatsapp', Icons.chat_outlined, 'WhatsApp'),
              const SizedBox(width: 8),
              _channelChip('email', Icons.mail_outline, 'E-mail'),
            ],
          ),
          if (_codeSent) ...[
            const SizedBox(height: 14),
            MHSurfaceCard(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Confirmer le numéro',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: AppColors.secondary,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    switch (_channel) {
                      'sms' => 'Entrez le code reçu par SMS sur le nouveau numéro.',
                      'whatsapp' =>
                        'Entrez le code reçu par WhatsApp sur le nouveau numéro.',
                      _ => 'Entrez le code reçu par e-mail.',
                    },
                    style: const TextStyle(
                        fontSize: 12, color: AppColors.mutedText),
                  ),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _codeController,
                    keyboardType: TextInputType.number,
                    textAlign: TextAlign.center,
                    decoration: MHSurfaceCard.input(hintText: '••••••'),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 16),
          _ErrorText(_error),
          MHGradientButton(
            label: _codeSent ? 'Confirmer' : 'Envoyer le code',
            loading: _loading,
            onPressed: _submit,
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Personne à contacter — nom + téléphone modifiables.
// ---------------------------------------------------------------------------
class EditContactScreen extends StatefulWidget {
  const EditContactScreen({super.key});

  @override
  State<EditContactScreen> createState() => _EditContactScreenState();
}

class _EditContactScreenState extends State<EditContactScreen> {
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    AuthService.instance.getMe().then((u) {
      if (mounted) {
        setState(() {
          _nameController.text = u.nomContactUrgence ?? '';
          _phoneController.text = u.contactUrgence ?? '';
        });
      }
    }).catchError((_) {});
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_nameController.text.trim().isEmpty) {
      setState(() => _error = 'Le nom est requis.');
      return;
    }
    setState(() {
      _error = null;
      _loading = true;
    });
    try {
      final me = await AuthService.instance.getMe();
      await UsersService().updateUser(me.id, {
        'nom_contact_urgence': _nameController.text.trim(),
        'contact_urgence': _phoneController.text.trim(),
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Personne à contacter mise à jour.'),
          backgroundColor: AppColors.success,
        ),
      );
      context.pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString().replaceFirst('Exception: ', '');
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return _EditScaffold(
      title: 'Personne à contacter',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _nameController,
            decoration: MHSurfaceCard.input(
              labelText: 'Nom et prénom *',
              hintText: 'Saisir le nom',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _phoneController,
            keyboardType: TextInputType.phone,
            decoration: MHSurfaceCard.input(
              labelText: 'Numéro de téléphone *',
              hintText: '+242 •• •• •• ••',
            ),
          ),
          const SizedBox(height: 16),
          _ErrorText(_error),
          MHGradientButton(
            label: 'Enregistrer les modifications',
            loading: _loading,
            onPressed: _submit,
          ),
        ],
      ),
    );
  }
}
