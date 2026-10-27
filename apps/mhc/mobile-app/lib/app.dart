import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'core/theme/app_theme.dart';
import 'core/widgets/mh_background.dart';
import 'providers/auth_provider.dart';
import 'providers/locale_provider.dart';
import 'router.dart';

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  final _localeProvider = LocaleProvider()..load();

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider.value(value: _localeProvider),
      ],
      child: Consumer<LocaleProvider>(
        builder: (context, localeProvider, _) => MaterialApp.router(
          title: 'Mobility Health Care',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light,
          locale: localeProvider.locale,
          // fr, en, es, pt, ar — l'arabe est affiché de droite à gauche
          // automatiquement par GlobalWidgetsLocalizations.
          supportedLocales: const [
            Locale('fr'),
            Locale('en'),
            Locale('es'),
            Locale('pt'),
            Locale('ar'),
          ],
          localizationsDelegates: const [
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          builder: (context, child) {
            return MHBackground(child: child);
          },
          routerConfig: appRouter,
        ),
      ),
    );
  }
}
