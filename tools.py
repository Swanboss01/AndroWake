"""Fenêtres annexes d'AndroWake : gestionnaire d'apps et télécommande."""
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog


def in_thread(fn):
    threading.Thread(target=fn, daemon=True).start()


class AppsWindow(tk.Toplevel):
    """Liste des applications avec recherche et actions."""

    def __init__(self, master, adb, log):
        super().__init__(master)
        self.title("AndroWake - Applications")
        self.geometry("460x520")
        self.adb, self.log = adb, log
        self.all = []

        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self._filter())
        ttk.Entry(top, textvariable=self.search).pack(side="left", fill="x", expand=True)
        self.system = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Système", variable=self.system, command=self.load).pack(side="left", padx=4)
        ttk.Button(top, text="Actualiser", command=self.load).pack(side="left")

        self.lb = tk.Listbox(self, selectmode="extended")
        self.lb.pack(fill="both", expand=True, padx=6)

        bar = ttk.Frame(self, padding=6)
        bar.pack(fill="x")
        for text, fn in [("Lancer", self.launch), ("Forcer l'arrêt", self.stop),
                         ("Vider les données", self.clear), ("Extraire l'APK", self.pull_apk),
                         ("Désinstaller", self.uninstall)]:
            ttk.Button(bar, text=text, command=fn).pack(side="left", padx=1)
        self.load()

    def load(self):
        def work():
            pk = self.adb.packages(third_party=not self.system.get())
            self.after(0, lambda: (setattr(self, "all", pk), self._filter()))
        in_thread(work)

    def _filter(self):
        q = self.search.get().lower()
        self.lb.delete(0, "end")
        for p in self.all:
            if q in p.lower():
                self.lb.insert("end", p)

    def selected(self):
        sel = [self.lb.get(i) for i in self.lb.curselection()]
        if not sel:
            messagebox.showinfo("AndroWake", "Sélectionnez une application.", parent=self)
        return sel

    def _each(self, pkgs, build, after=None):
        def work():
            for p in pkgs:
                _, out = build(p)
                self.after(0, self.log, f"{p} : {out}")
            if after:
                self.after(0, after)
        in_thread(work)

    def launch(self):
        self._each(self.selected()[:1], lambda p: self.adb.shell(
            f"monkey -p {p} -c android.intent.category.LAUNCHER 1"))

    def stop(self):
        self._each(self.selected(), lambda p: self.adb.shell(f"am force-stop {p}"))

    def clear(self):
        pk = self.selected()
        if pk and messagebox.askyesno("AndroWake", f"Effacer les données de {len(pk)} app(s) ?", parent=self):
            self._each(pk, lambda p: self.adb.shell(f"pm clear {p}"))

    def uninstall(self):
        pk = self.selected()
        if pk and messagebox.askyesno("AndroWake", "Désinstaller :\n" + "\n".join(pk), parent=self):
            self._each(pk, lambda p: self.adb.run("uninstall", p), after=self.load)

    def pull_apk(self):
        pk = self.selected()[:1]
        dest = filedialog.askdirectory(parent=self) if pk else None
        if not dest:
            return

        def build(p):
            _, out = self.adb.shell(f"pm path {p}")
            paths = [l.split(":", 1)[1].strip() for l in out.splitlines() if l.startswith("package:")]
            if not paths:
                return 1, "APK introuvable"
            return self.adb.run("pull", paths[0], f"{dest}/{p}.apk")
        self._each(pk, build)


class RemoteWindow(tk.Toplevel):
    """Télécommande : touches, texte, tap/swipe, URL."""

    KEYS = [("Retour", "KEYCODE_BACK"), ("Accueil", "KEYCODE_HOME"), ("Récents", "KEYCODE_APP_SWITCH"),
            ("Vol +", "KEYCODE_VOLUME_UP"), ("Vol -", "KEYCODE_VOLUME_DOWN"), ("Muet", "KEYCODE_VOLUME_MUTE"),
            ("Alimentation", "KEYCODE_POWER"), ("Haut", "KEYCODE_DPAD_UP"), ("Bas", "KEYCODE_DPAD_DOWN"),
            ("Gauche", "KEYCODE_DPAD_LEFT"), ("Droite", "KEYCODE_DPAD_RIGHT"), ("OK", "KEYCODE_DPAD_CENTER"),
            ("Lecture/Pause", "KEYCODE_MEDIA_PLAY_PAUSE"), ("Notifications", "KEYCODE_NOTIFICATION")]

    def __init__(self, master, adb, log):
        super().__init__(master)
        self.title("AndroWake - Télécommande")
        self.adb, self.log = adb, log
        self.resizable(False, False)

        keys = ttk.LabelFrame(self, text="Touches", padding=6)
        keys.pack(fill="x", padx=6, pady=4)
        for i, (label, code) in enumerate(self.KEYS):
            ttk.Button(keys, text=label, width=13,
                       command=lambda c=code: self.send(self.adb.key, c)).grid(row=i // 3, column=i % 3, padx=1, pady=1)

        txt = ttk.LabelFrame(self, text="Saisie de texte / URL", padding=6)
        txt.pack(fill="x", padx=6, pady=4)
        self.text = ttk.Entry(txt, width=34)
        self.text.grid(row=0, column=0, columnspan=2, sticky="we")
        ttk.Button(txt, text="Envoyer le texte", command=self.send_text).grid(row=1, column=0, pady=2)
        ttk.Button(txt, text="Ouvrir l'URL", command=self.open_url).grid(row=1, column=1, pady=2)

        pos = ttk.LabelFrame(self, text="Tap / swipe (pixels)", padding=6)
        pos.pack(fill="x", padx=6, pady=4)
        self.xy = [ttk.Entry(pos, width=6) for _ in range(4)]
        for i, (e, name) in enumerate(zip(self.xy, ("x1", "y1", "x2", "y2"))):
            ttk.Label(pos, text=name).grid(row=0, column=2 * i)
            e.grid(row=0, column=2 * i + 1)
        ttk.Button(pos, text="Tap (x1,y1)", command=self.tap).grid(row=1, column=0, columnspan=4, pady=2)
        ttk.Button(pos, text="Swipe", command=self.swipe).grid(row=1, column=4, columnspan=4, pady=2)

    def send(self, fn, *args):
        if not self.adb.serial:
            messagebox.showinfo("AndroWake", "Aucun appareil sélectionné.", parent=self)
            return
        in_thread(lambda: (lambda r: r[0] and self.after(0, self.log, r[1]))(fn(*args)))

    def send_text(self):
        if self.text.get():
            self.send(self.adb.text, self.text.get())

    def open_url(self):
        url = self.text.get().strip()
        if url:
            self.send(self.adb.shell, f"am start -a android.intent.action.VIEW -d '{url}'")

    def _nums(self, n):
        try:
            return [int(e.get()) for e in self.xy[:n]]
        except ValueError:
            messagebox.showinfo("AndroWake", "Entrez des coordonnées entières.", parent=self)
            return None

    def tap(self):
        v = self._nums(2)
        if v:
            self.send(self.adb.tap, *v)

    def swipe(self):
        v = self._nums(4)
        if v:
            self.send(self.adb.swipe, *v)
