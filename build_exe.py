"""Crée AndroWake.exe avec PyInstaller : python build_exe.py

Résultat : dist/AndroWake/AndroWake.exe. adb et scrcpy sont téléchargés
au premier lancement dans le dossier de l'exécutable.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed",
        "--name", "AndroWake",
        "--icon", os.path.join(HERE, "icon.ico"),
        "--add-data", os.path.join(HERE, "icon.ico") + os.pathsep + ".",
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", os.path.join(HERE, "build"),
        "--specpath", os.path.join(HERE, "build"),
        os.path.join(HERE, "androwake.py"),
    ], cwd=HERE)
    print("OK :", os.path.join(HERE, "dist", "AndroWake", "AndroWake.exe"))


if __name__ == "__main__":
    main()
