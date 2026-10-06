"""AndroWake - contrôle d'appareils Android via adb (interface Tkinter)."""
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog

from adb_client import Adb, find_scrcpy, download_scrcpy, NO_WINDOW
from tools import AppsWindow, RemoteWindow

THEMES = {
    "clair": dict(bg="#f0f0f0", fg="#000000", field="#ffffff", sel="#3399ff"),
    "sombre": dict(bg="#1e1e1e", fg="#e6e6e6", field="#2b2b2b", sel="#0e639c"),
}
LEVELS = ["V", "D", "I", "W", "E"]
LEVEL_COLORS = {"W": "#d19a00", "E": "#e05555"}

APP = "AndroWake"
MODES = {
    "device": "Android",
    "recovery": "Recovery",
    "sideload": "Recovery (sideload)",
    "fastboot": "Bootloader (fastboot)",
    "unauthorized": "Non autorisé",
    "offline": "Hors ligne",
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP)
        self.geometry("920x720")
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        try:
            self.iconbitmap(os.path.join(base, "icon.ico"))
        except tk.TclError:
            pass
        self.adb = Adb()
        self.logcat_proc = None
        self.states = {}
        self.theme = "clair"
        self._build()
        self.apply_theme()
        if self.adb.available:
            self._auto_refresh()
        else:
            self.after(200, self.download_adb)

    # ---------- interface ----------
    def _build(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Label(top, text="Appareil :").pack(side="left")
        self.combo = ttk.Combobox(top, state="readonly", width=40)
        self.combo.pack(side="left", padx=4)
        self.combo.bind("<<ComboboxSelected>>", self._select)
        ttk.Button(top, text="Actualiser", command=self.refresh).pack(side="left")
        self.ip = ttk.Entry(top, width=18)
        self.ip.pack(side="right")
        ttk.Button(top, text="Connexion Wi-Fi (IP)", command=self.wifi_connect).pack(side="right", padx=4)

        body = ttk.Frame(self, padding=6)
        body.pack(fill="both", expand=True)

        side = ttk.LabelFrame(body, text="Actions", padding=6)
        side.pack(side="left", fill="y")
        actions = [
            ("Infos appareil", self.show_info),
            ("Réveiller l'écran", lambda: self.sh("input keyevent KEYCODE_WAKEUP", "Écran réveillé")),
            ("Veille", lambda: self.sh("input keyevent KEYCODE_SLEEP", "Mise en veille")),
            ("Rester éveillé : ON", lambda: self.sh("svc power stayon true", "Stay awake activé")),
            ("Rester éveillé : OFF", lambda: self.sh("svc power stayon false", "Stay awake désactivé")),
            ("Capture d'écran", self.screenshot),
            ("Installer APK", self.install_apk),
            ("Sideload ZIP (recovery)", self.sideload),
            ("Envoyer fichier (push)", self.push),
            ("Récupérer fichier (pull)", self.pull),
            ("Gestionnaire d'apps", self.open_apps),
            ("Télécommande", self.open_remote),
            ("Miroir d'écran (scrcpy)", self.mirror),
            ("Wi-Fi ADB en un clic", self.wifi_oneclick),
            ("Redémarrer", lambda: self.reboot("")),
            ("Reboot recovery", lambda: self.reboot("recovery")),
            ("Reboot bootloader", lambda: self.reboot("bootloader")),
            ("Thème clair / sombre", self.toggle_theme),
        ]
        for text, cmd in actions:
            ttk.Button(side, text=text, command=cmd, width=24).pack(pady=1)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        lc = ttk.LabelFrame(right, text="Logcat", padding=4)
        lc.pack(fill="x", pady=(0, 4))
        ttk.Label(lc, text="Niveau ≥").pack(side="left")
        self.level = ttk.Combobox(lc, values=LEVELS, state="readonly", width=3)
        self.level.set("I")
        self.level.pack(side="left", padx=4)
        ttk.Label(lc, text="Mot-clé").pack(side="left")
        self.keyword = ttk.Entry(lc, width=18)
        self.keyword.pack(side="left", padx=4)
        self.logcat_btn = ttk.Button(lc, text="Démarrer", command=self.toggle_logcat)
        self.logcat_btn.pack(side="left", padx=2)
        ttk.Button(lc, text="Effacer", command=self.clear_log).pack(side="left", padx=2)
        ttk.Button(lc, text="Exporter", command=self.export_log).pack(side="left", padx=2)

        self.out = scrolledtext.ScrolledText(right, state="disabled", font=("Consolas", 9))
        self.out.pack(fill="both", expand=True)
        for lv, color in LEVEL_COLORS.items():
            self.out.tag_configure(lv, foreground=color)
        row = ttk.Frame(right)
        row.pack(fill="x", pady=(4, 0))
        ttk.Label(row, text="adb shell >").pack(side="left")
        self.cmd = ttk.Entry(row)
        self.cmd.pack(side="left", fill="x", expand=True, padx=4)
        self.cmd.bind("<Return>", lambda e: self.custom())
        ttk.Button(row, text="Exécuter", command=self.custom).pack(side="left")

        self.status = ttk.Label(self, text="", relief="sunken", anchor="w")
        self.status.pack(fill="x")

    # ---------- utilitaires ----------
    def log(self, text, tag=None):
        self.out.configure(state="normal")
        self.out.insert("end", text + "\n", tag)
        self.out.see("end")
        self.out.configure(state="disabled")

    def clear_log(self):
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.configure(state="disabled")

    def export_log(self):
        dest = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texte", "*.txt")])
        if dest:
            with open(dest, "w", encoding="utf-8") as f:
                f.write(self.out.get("1.0", "end"))
            self.status.config(text=f"Journal exporté : {dest}")

    # ---------- thème ----------
    def toggle_theme(self):
        self.theme = "sombre" if self.theme == "clair" else "clair"
        self.apply_theme()

    def apply_theme(self):
        t = THEMES[self.theme]
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=t["bg"], foreground=t["fg"], fieldbackground=t["field"])
        st.configure("TButton", background=t["field"], foreground=t["fg"])
        st.map("TButton", background=[("active", t["sel"])])
        st.configure("TEntry", fieldbackground=t["field"], foreground=t["fg"])
        st.configure("TCombobox", fieldbackground=t["field"], foreground=t["fg"], background=t["field"])
        st.configure("TLabelframe", background=t["bg"])
        st.configure("TLabelframe.Label", background=t["bg"], foreground=t["fg"])
        self.configure(bg=t["bg"])
        self.option_add("*Listbox.background", t["field"])
        self.option_add("*Listbox.foreground", t["fg"])
        self.out.configure(bg=t["field"], fg=t["fg"], insertbackground=t["fg"])
        for w in self.winfo_children():
            if isinstance(w, tk.Toplevel):
                w.configure(bg=t["bg"])
                for c in w.winfo_children():
                    if isinstance(c, tk.Listbox):
                        c.configure(bg=t["field"], fg=t["fg"])

    # ---------- fenêtres annexes ----------
    def open_apps(self):
        if self.need_device():
            AppsWindow(self, self.adb, self.log)
            self.apply_theme()

    def open_remote(self):
        if self.need_device():
            RemoteWindow(self, self.adb, self.log)
            self.apply_theme()

    def mirror(self):
        if not self.need_device():
            return
        exe = find_scrcpy()
        if not exe:
            if not messagebox.askyesno(APP, "scrcpy est introuvable.\nLe télécharger dans le dossier d'AndroWake ?"):
                return
            self.status.config(text="Téléchargement de scrcpy...")

            def work():
                try:
                    p = download_scrcpy(lambda n: self.after(0, lambda: self.status.config(
                        text=f"Téléchargement de scrcpy... {n}%")))
                    self.after(0, lambda: (self.log("scrcpy installé."), self.mirror() if p else None))
                except Exception as e:
                    self.after(0, self.log, f"Échec du téléchargement de scrcpy : {e}")
            threading.Thread(target=work, daemon=True).start()
            return
        env = dict(__import__("os").environ, ADB=self.adb.path)
        subprocess.Popen([exe, "-s", self.adb.serial], env=env, creationflags=NO_WINDOW)
        self.status.config(text="Miroir d'écran lancé")

    def wifi_oneclick(self):
        if not self.need_device():
            return
        if self.mode != "device":
            messagebox.showinfo(APP, "Branchez l'appareil en USB, Android démarré (mode « Android »).")
            return
        self.status.config(text="Activation d'adb Wi-Fi...")

        def work():
            msg = self.adb.enable_wifi_adb()
            self.after(0, lambda: (self.log(msg), self.status.config(text="Wi-Fi ADB : " + msg),
                                   self.refresh()))
        threading.Thread(target=work, daemon=True).start()

    def run_async(self, *args, done=None):
        """Exécute adb dans un thread pour ne pas figer l'interface."""
        def work():
            code, out = self.adb.run(*args)
            self.after(0, lambda: (self.log(out or f"(code {code})"), done and done(code)))
        threading.Thread(target=work, daemon=True).start()

    def sh(self, command, msg=None):
        if self.need_device():
            self.run_async("shell", command, done=lambda c: msg and self.status.config(text=msg))

    def need_device(self):
        if not self.adb.serial:
            messagebox.showinfo(APP, "Aucun appareil sélectionné.")
            return False
        return True

    def download_adb(self):
        if not messagebox.askyesno(APP, "adb est introuvable.\n"
                                   "Le télécharger (platform-tools de Google) dans le dossier d'AndroWake ?"):
            return

        def progress(p):
            self.after(0, lambda: self.status.config(text=f"Téléchargement d'adb... {p}%"))

        def work():
            try:
                ok = self.adb.install(progress)
                msg = "adb installé." if ok else "Échec : adb introuvable après extraction."
            except Exception as e:
                msg = f"Échec du téléchargement : {e}"
            self.after(0, lambda: (self.log(msg), self._auto_refresh() if self.adb.available else None))
        threading.Thread(target=work, daemon=True).start()

    # ---------- actions ----------
    def refresh(self):
        """Détection en thread (adb + fastboot), relancée toutes les 3 s."""
        if not self.adb.available:
            return

        def work():
            devs = self.adb.devices()
            self.after(0, lambda: self._show_devices(devs))
        threading.Thread(target=work, daemon=True).start()

    def _auto_refresh(self):
        self.refresh()
        self.after(3000, self._auto_refresh)

    def _show_devices(self, devs):
        labels = [f"{s}  [{MODES.get(st, st)}] {d}".strip() for s, st, d in devs]
        self.states = {s: st for s, st, _ in devs}
        if labels != list(self.combo["values"]):
            current = self.adb.serial
            self.combo["values"] = labels
            idx = next((i for i, (s, _, _) in enumerate(devs) if s == current), 0)
            if devs:
                self.combo.current(idx)
            else:
                self.combo.set("")
            self._select()
        self.status.config(text=f"{len(devs)} appareil(s) détecté(s)")

    def _select(self, _=None):
        self.adb.serial = self.combo.get().split()[0] if self.combo.get() else None

    @property
    def mode(self):
        return self.states.get(self.adb.serial)

    def sideload(self):
        if not self.need_device():
            return
        if self.mode not in ("recovery", "sideload"):
            messagebox.showinfo(APP, "L'appareil doit être en recovery (mode « Apply update from ADB »).")
            return
        f = filedialog.askopenfilename(filetypes=[("ZIP", "*.zip")])
        if f:
            self.run_async("sideload", f)

    def wifi_connect(self):
        addr = self.ip.get().strip()
        if addr:
            if ":" not in addr:
                addr += ":5555"
            self.run_async("connect", addr, done=lambda c: self.refresh())

    def show_info(self):
        if self.need_device():
            threading.Thread(target=lambda: self.after(0, self.log, self.adb.info()),
                             daemon=True).start()

    def screenshot(self):
        if not self.need_device():
            return
        dest = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if dest:
            def work():
                ok = self.adb.screenshot(dest)
                self.after(0, lambda: self.log(f"Capture : {dest}" if ok else "Échec de la capture"))
            threading.Thread(target=work, daemon=True).start()

    def install_apk(self):
        if self.need_device():
            f = filedialog.askopenfilename(filetypes=[("APK", "*.apk")])
            if f:
                self.run_async("install", "-r", f)

    def push(self):
        if self.need_device():
            f = filedialog.askopenfilename()
            if f:
                self.run_async("push", f, "/sdcard/Download/")

    def pull(self):
        if not self.need_device():
            return
        remote = simpledialog.askstring(APP, "Chemin sur l'appareil :", initialvalue="/sdcard/")
        dest = filedialog.askdirectory() if remote else None
        if remote and dest:
            self.run_async("pull", remote, dest)

    def reboot(self, mode):
        if not self.need_device() or not messagebox.askyesno(APP, f"Redémarrer l'appareil {mode} ?"):
            return
        if self.mode == "fastboot":
            if mode == "recovery":
                messagebox.showinfo(APP, "fastboot ne peut pas rebooter en recovery directement.")
                return
            args = ["reboot-bootloader"] if mode == "bootloader" else ["reboot"]

            def work():
                code, out = self.adb.fastboot(*args)
                self.after(0, self.log, out or f"(code {code})")
            threading.Thread(target=work, daemon=True).start()
        else:
            self.run_async("reboot", *([mode] if mode else []))

    def custom(self):
        c = self.cmd.get().strip()
        if c and self.need_device():
            self.log(f"$ {c}")
            self.run_async("shell", c)
            self.cmd.delete(0, "end")

    def toggle_logcat(self):
        if self.logcat_proc:
            self.logcat_proc.terminate()
            self.logcat_proc = None
            self.logcat_btn.config(text="Démarrer")
            self.status.config(text="Logcat arrêté")
            return
        if not self.need_device():
            return
        proc = self.logcat_proc = self.adb.popen("logcat", "-v", "brief", f"*:{self.level.get()}")
        self.logcat_btn.config(text="Arrêter")
        self.status.config(text="Logcat en cours...")

        def read():
            for raw in proc.stdout:
                line = raw.decode("utf-8", "replace").rstrip()
                kw = self.keyword.get().strip().lower()  # filtre appliqué en direct
                if kw and kw not in line.lower():
                    continue
                tag = line[0] if line[:2] in ("W/", "E/", "F/") else None
                self.after(0, self.log, line, "E" if tag == "F" else tag)
        threading.Thread(target=read, daemon=True).start()

    def destroy(self):
        if self.logcat_proc:
            self.logcat_proc.terminate()
        super().destroy()


if __name__ == "__main__":
    App().mainloop()
