import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/locale_provider.dart';

/// Chaînes localisées de l'application (fr, en, es, pt, ar).
/// Usage : `tr(context, 'profile')` ou `AppStrings.of(context).get('profile')`.
/// Toute clé absente retombe sur le français.
class AppStrings {
  AppStrings(this.languageCode);

  final String languageCode;

  static AppStrings of(BuildContext context) =>
      AppStrings(context.watch<LocaleProvider>().locale.languageCode);

  String get(String key) =>
      _values[languageCode]?[key] ?? _values['fr']?[key] ?? key;

  static const Map<String, Map<String, String>> _values = {
    'fr': {
      'profile': 'Profil',
      'my_cards': 'Mes cartes',
      'attestations': 'Attestations',
      'payments': 'Paiements',
      'history': 'Historique',
      'mhc_network': 'Réseau MHC',
      'security': 'Sécurité',
      'settings': 'Paramètres',
      'help': 'Aide',
      'complaints': 'Réclamations',
      'children': 'Mes enfants',
      'logout': 'Déconnexion',
      'cancel': 'Annuler',
      'confirm': 'Confirmer',
      'save': 'Enregistrer',
      'delete': 'Supprimer',
      'send': 'Envoyer',
      'close': 'Fermer',
      'retry': 'Réessayer',
      'change_photo': 'Changer la photo',
      'my_profile': 'Mon profil',
      'notifications': 'Notifications',
      'new_complaint': 'Nouvelle réclamation',
    },
    'en': {
      'profile': 'Profile',
      'my_cards': 'My cards',
      'attestations': 'Certificates',
      'payments': 'Payments',
      'history': 'History',
      'mhc_network': 'MHC network',
      'security': 'Security',
      'settings': 'Settings',
      'help': 'Help',
      'complaints': 'Complaints',
      'children': 'My children',
      'logout': 'Sign out',
      'cancel': 'Cancel',
      'confirm': 'Confirm',
      'save': 'Save',
      'delete': 'Delete',
      'send': 'Send',
      'close': 'Close',
      'retry': 'Retry',
      'change_photo': 'Change photo',
      'my_profile': 'My profile',
      'notifications': 'Notifications',
      'new_complaint': 'New complaint',
    },
    'es': {
      'profile': 'Perfil',
      'my_cards': 'Mis tarjetas',
      'attestations': 'Certificados',
      'payments': 'Pagos',
      'history': 'Historial',
      'mhc_network': 'Red MHC',
      'security': 'Seguridad',
      'settings': 'Ajustes',
      'help': 'Ayuda',
      'complaints': 'Reclamaciones',
      'children': 'Mis hijos',
      'logout': 'Cerrar sesión',
      'cancel': 'Cancelar',
      'confirm': 'Confirmar',
      'save': 'Guardar',
      'delete': 'Eliminar',
      'send': 'Enviar',
      'close': 'Cerrar',
      'retry': 'Reintentar',
      'change_photo': 'Cambiar la foto',
      'my_profile': 'Mi perfil',
      'notifications': 'Notificaciones',
      'new_complaint': 'Nueva reclamación',
    },
    'pt': {
      'profile': 'Perfil',
      'my_cards': 'Meus cartões',
      'attestations': 'Certificados',
      'payments': 'Pagamentos',
      'history': 'Histórico',
      'mhc_network': 'Rede MHC',
      'security': 'Segurança',
      'settings': 'Definições',
      'help': 'Ajuda',
      'complaints': 'Reclamações',
      'children': 'Meus filhos',
      'logout': 'Terminar sessão',
      'cancel': 'Cancelar',
      'confirm': 'Confirmar',
      'save': 'Guardar',
      'delete': 'Eliminar',
      'send': 'Enviar',
      'close': 'Fechar',
      'retry': 'Tentar novamente',
      'change_photo': 'Alterar a foto',
      'my_profile': 'O meu perfil',
      'notifications': 'Notificações',
      'new_complaint': 'Nova reclamação',
    },
    'ar': {
      'profile': 'الملف الشخصي',
      'my_cards': 'بطاقاتي',
      'attestations': 'الشهادات',
      'payments': 'المدفوعات',
      'history': 'السجل',
      'mhc_network': 'شبكة MHC',
      'security': 'الأمان',
      'settings': 'الإعدادات',
      'help': 'مساعدة',
      'complaints': 'الشكاوى',
      'children': 'أطفالي',
      'logout': 'تسجيل الخروج',
      'cancel': 'إلغاء',
      'confirm': 'تأكيد',
      'save': 'حفظ',
      'delete': 'حذف',
      'send': 'إرسال',
      'close': 'إغلاق',
      'retry': 'إعادة المحاولة',
      'change_photo': 'تغيير الصورة',
      'my_profile': 'ملفي الشخصي',
      'notifications': 'الإشعارات',
      'new_complaint': 'شكوى جديدة',
    },
  };
}

/// Raccourci : `tr(context, 'profile')`.
String tr(BuildContext context, String key) => AppStrings.of(context).get(key);
