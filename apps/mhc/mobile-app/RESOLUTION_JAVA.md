# 🔧 Résolution de l'Erreur Java

## ❌ Erreur Rencontrée

```
Dependency requires at least JVM runtime version 11. 
This build uses a Java 8 JVM.
```

## 🔍 Cause

Le projet Flutter nécessite **Java 11 ou supérieur** (configuré pour Java 17), mais Gradle utilise **Java 8**.

## ✅ Solutions

### Solution 1 : Installer Java 17 (Recommandé)

1. **Télécharger Java 17**
   - Oracle JDK : https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html
   - OpenJDK : https://adoptium.net/temurin/releases/?version=17

2. **Installer Java 17**

3. **Configurer JAVA_HOME**
   ```powershell
   # Trouver le chemin d'installation (généralement)
   # C:\Program Files\Java\jdk-17
   
   # Ajouter au PATH système
   [System.Environment]::SetEnvironmentVariable("JAVA_HOME", "C:\Program Files\Java\jdk-17", "Machine")
   [System.Environment]::SetEnvironmentVariable("PATH", "$env:PATH;C:\Program Files\Java\jdk-17\bin", "Machine")
   ```

4. **Redémarrer PowerShell** et vérifier :
   ```powershell
   java -version
   # Devrait afficher : openjdk version "17"...
   ```

### Solution 2 : Utiliser Java d'Android Studio

Si Android Studio est installé, il inclut Java :

1. **Trouver le chemin Java d'Android Studio**
   ```powershell
   # Généralement dans :
   # C:\Program Files\Android\Android Studio\jbr
   ```

2. **Configurer dans gradle.properties**
   ```properties
   org.gradle.java.home=C:\\Program Files\\Android\\Android Studio\\jbr
   ```

### Solution 3 : Vérifier la Configuration Actuelle

```powershell
# Voir toutes les versions Java installées
Get-ChildItem "C:\Program Files\Java" -ErrorAction SilentlyContinue
Get-ChildItem "C:\Program Files (x86)\Java" -ErrorAction SilentlyContinue

# Voir la version actuelle
java -version

# Voir JAVA_HOME
$env:JAVA_HOME
```

## 🚀 Après Configuration

1. **Nettoyer le projet**
   ```powershell
   cd mobile-app
   flutter clean
   ```

2. **Relancer**
   ```powershell
   flutter run
   ```

## ⚠️ Note

Si vous avez plusieurs versions de Java installées, assurez-vous que :
- `JAVA_HOME` pointe vers Java 11+
- Le PATH contient le bon Java en premier
- Gradle utilise la bonne version

