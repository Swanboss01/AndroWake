# AndroWake

Logiciel Windows pour piloter un appareil Android depuis le PC via **adb**, avec une interface simple (Python + Tkinter).

## Installation

1. Téléchargez `AndroWakeSetup.exe` dans l'onglet [Releases](https://github.com/Swanboss01/AndroWake/releases).
2. Lancez l'installeur (aucun droit administrateur requis : installation dans `%LOCALAPPDATA%\AndroWake`).
3. Au premier lancement, AndroWake propose de télécharger **adb** (platform-tools de Google) dans son dossier.

Sur le téléphone, activez le **débogage USB** (Options pour les développeurs) puis acceptez l'empreinte RSA à la première connexion.

## Fonctionnalités

| | |
|---|---|
| **Détection** | Appareils en mode Android, Recovery, Sideload et Bootloader (fastboot), actualisés automatiquement |
| **Écran** | Réveil, veille, mode « rester éveillé », capture d'écran |
| **Infos** | Marque, modèle, version d'Android, SDK, batterie |
| **Applications** | Gestionnaire (recherche, lancer, forcer l'arrêt, vider les données, extraire l'APK, désinstaller), installation d'APK |
| **Fichiers** | Envoi (push) et récupération (pull) |
| **Recovery** | Sideload de ZIP |
| **Redémarrage** | Normal, recovery, bootloader (adb ou fastboot selon le mode) |
| **Connexion** | Wi-Fi ADB en un clic, ou par adresse IP |
| **Télécommande** | Touches (Retour, Accueil, Volume…), saisie de texte, URL, tap et swipe |
| **Miroir d'écran** | Via [scrcpy](https://github.com/Genymobile/scrcpy), téléchargé à la demande |
| **Logcat** | Filtre par niveau et mot-clé, couleurs, export |
| **Shell** | Champ de commande `adb shell` |
| **Interface** | Thème clair / sombre |

## Depuis les sources

Prérequis : Python 3.10+ (Tkinter inclus).

```
python androwake.py
```

Créer l'exécutable puis l'installeur (Pillow pour l'icône, [NSIS](https://nsis.sourceforge.io) pour l'installeur) :

```
python make_icon.py        # génère icon.ico
python build_exe.py        # dist/AndroWake/AndroWake.exe (PyInstaller)
makensis installer.nsi     # AndroWakeSetup.exe
```

## Structure

- `androwake.py` : interface principale
- `tools.py` : gestionnaire d'apps et télécommande
- `adb_client.py` : enveloppe adb/fastboot, téléchargement d'adb et de scrcpy
- `installer.nsi` : script de l'installeur NSIS

## Avertissement

Les actions de redémarrage, de désinstallation, de suppression de données et de sideload sont irréversibles ou peuvent bloquer un appareil. Utilisez AndroWake à vos risques, sur vos propres appareils.
