# Flutter wrapper
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# ML Kit : les recognizers non latins (chinois, devanagari, japonais,
# coréen) sont des dépendances optionnelles non embarquées.
-dontwarn com.google.mlkit.vision.text.chinese.**
-dontwarn com.google.mlkit.vision.text.devanagari.**
-dontwarn com.google.mlkit.vision.text.japanese.**
-dontwarn com.google.mlkit.vision.text.korean.**

# Play Core (composants différés Play Store) : non utilisé par l'app,
# classes optionnelles référencées par le moteur Flutter.
-dontwarn com.google.android.play.core.**
