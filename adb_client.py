"""Fine enveloppe autour d'adb pour AndroWake."""
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

if getattr(sys, "frozen", False):  # exécutable PyInstaller : dossier de l'.exe
    HERE = os.path.dirname(sys.executable)
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def find_adb():
    """Cherche adb : dossier AndroWake/platform-tools, puis PATH."""
    exe = "adb.exe" if sys.platform == "win32" else "adb"
    local = os.path.join(HERE, "platform-tools", exe)
    if os.path.isfile(local):
        return local
    return shutil.which("adb")


def download_adb(progress=None):
    """Télécharge platform-tools (Google) dans AndroWake/platform-tools."""
    osname = {"win32": "windows", "darwin": "darwin"}.get(sys.platform, "linux")
    url = f"https://dl.google.com/android/repository/platform-tools-latest-{osname}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        zpath = os.path.join(tmp, "platform-tools.zip")

        def hook(blocks, size, total):
            if progress and total > 0:
                progress(min(100, blocks * size * 100 // total))
        urllib.request.urlretrieve(url, zpath, hook)
        with zipfile.ZipFile(zpath) as z:
            z.extractall(HERE)  # l'archive contient déjà le dossier platform-tools/
    path = find_adb()
    if path and sys.platform != "win32":
        os.chmod(path, 0o755)
    return path


def find_scrcpy():
    exe = "scrcpy.exe" if sys.platform == "win32" else "scrcpy"
    local = os.path.join(HERE, "scrcpy", exe)
    return local if os.path.isfile(local) else shutil.which("scrcpy")


def download_scrcpy(progress=None):
    """Télécharge la dernière release de scrcpy (Windows 64 bits) dans AndroWake/scrcpy."""
    import json
    if sys.platform != "win32":
        raise RuntimeError("Installez scrcpy avec votre gestionnaire de paquets.")
    api = "https://api.github.com/repos/Genymobile/scrcpy/releases/latest"
    with urllib.request.urlopen(api, timeout=30) as r:
        assets = json.load(r)["assets"]
    url = next(a["browser_download_url"] for a in assets
               if a["name"].startswith("scrcpy-win64") and a["name"].endswith(".zip"))
    with tempfile.TemporaryDirectory() as tmp:
        zpath = os.path.join(tmp, "scrcpy.zip")

        def hook(blocks, size, total):
            if progress and total > 0:
                progress(min(100, blocks * size * 100 // total))
        urllib.request.urlretrieve(url, zpath, hook)
        dest = os.path.join(HERE, "scrcpy")
        with zipfile.ZipFile(zpath) as z:
            top = z.namelist()[0].split("/")[0]
            z.extractall(tmp)
        shutil.rmtree(dest, ignore_errors=True)
        shutil.move(os.path.join(tmp, top), dest)
    return find_scrcpy()


class Adb:
    def packages(self, third_party=True):
        _, out = self.shell("pm list packages" + (" -3" if third_party else ""))
        return sorted(l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("package:"))

    def wifi_ip(self):
        """IP Wi-Fi de l'appareil (ou None)."""
        _, out = self.shell("ip -f inet addr show wlan0")
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
        return None

    def enable_wifi_adb(self, port=5555):
        """Passe l'appareil (en USB) en adb TCP puis s'y connecte. Renvoie un message."""
        ip = self.wifi_ip()
        if not ip:
            return "IP Wi-Fi introuvable : l'appareil est-il connecté au Wi-Fi ?"
        code, out = self.run("tcpip", str(port))
        if code != 0:
            return out
        import time
        time.sleep(2)
        self.serial = None
        return self.run("connect", f"{ip}:{port}")[1]

    def key(self, keycode):
        return self.shell(f"input keyevent {keycode}")

    def tap(self, x, y):
        return self.shell(f"input tap {x} {y}")

    def swipe(self, x1, y1, x2, y2, ms=300):
        return self.shell(f"input swipe {x1} {y1} {x2} {y2} {ms}")

    def text(self, s):
        # input text : espaces => %s ; on échappe d'abord les caractères spéciaux du shell
        safe = "".join(f"\\{c}" if c in "&|;<>()$`\\\"'*?[]#~=%!{}^" else c for c in s)
        return self.shell(f"input text {safe.replace(' ', '%s')}")

    def __init__(self, path=None):
        self.path = path or find_adb()
        self.serial = None

    def install(self, progress=None):
        """Télécharge adb dans le dossier d'AndroWake."""
        self.path = download_adb(progress)
        return self.available

    @property
    def available(self):
        return bool(self.path) and os.path.isfile(self.path)

    def _cmd(self, args):
        cmd = [self.path]
        if self.serial:
            cmd += ["-s", self.serial]
        return cmd + list(args)

    def run(self, *args, timeout=60, binary=False):
        """Lance adb ; renvoie (code, sortie). Cible l'appareil choisi."""
        if not self.available:
            return 1, "adb introuvable. Mettez platform-tools dans AndroWake/ ou dans le PATH."
        try:
            p = subprocess.run(self._cmd(args), capture_output=True, timeout=timeout,
                               creationflags=NO_WINDOW)
        except subprocess.TimeoutExpired:
            return 1, "Délai dépassé."
        out = p.stdout if binary else (p.stdout + p.stderr).decode("utf-8", "replace").strip()
        return p.returncode, out

    def popen(self, *args):
        return subprocess.Popen(self._cmd(args), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, creationflags=NO_WINDOW)

    @property
    def fastboot_path(self):
        exe = "fastboot.exe" if sys.platform == "win32" else "fastboot"
        local = os.path.join(os.path.dirname(self.path or ""), exe)
        return local if os.path.isfile(local) else shutil.which("fastboot")

    def fastboot(self, *args, timeout=60):
        """Lance fastboot (mode bootloader) ; renvoie (code, sortie)."""
        fb = self.fastboot_path
        if not fb:
            return 1, "fastboot introuvable."
        cmd = [fb] + (["-s", self.serial] if self.serial else []) + list(args)
        try:
            p = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
        except subprocess.TimeoutExpired:
            return 1, "Délai dépassé."
        return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace").strip()

    def devices(self):
        """Appareils adb (device, recovery, sideload, unauthorized...) + fastboot."""
        _, out = self.run("devices", "-l")
        res = []
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                res.append((parts[0], parts[1], " ".join(parts[2:])))
        if self.fastboot_path:
            _, out = self.fastboot("devices", timeout=10)
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "fastboot":
                    res.append((parts[0], "fastboot", ""))
        return res

    def shell(self, command, timeout=60):
        return self.run("shell", command, timeout=timeout)

    def prop(self, name):
        return self.shell(f"getprop {name}")[1]

    def battery(self):
        _, out = self.shell("dumpsys battery")
        keep = [l.strip() for l in out.splitlines()
                if l.strip().startswith(("level", "status", "AC powered", "USB powered", "temperature"))]
        return "\n".join(keep)

    def info(self):
        props = {
            "Marque": "ro.product.brand",
            "Modèle": "ro.product.model",
            "Android": "ro.build.version.release",
            "SDK": "ro.build.version.sdk",
            "Build": "ro.build.display.id",
            "CPU": "ro.product.cpu.abi",
        }
        lines = [f"{k} : {self.prop(v)}" for k, v in props.items()]
        lines.append(self.battery())
        return "\n".join(lines)

    def screenshot(self, dest):
        code, data = self.run("exec-out", "screencap", "-p", binary=True)
        if code != 0 or not data:
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
