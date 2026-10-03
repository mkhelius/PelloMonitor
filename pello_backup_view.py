"""
pello_backup_view.py - zakładka „Kopie”: lista kopii zapasowych, tworzenie i porównywanie.
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Etap 1: program wyłącznie CZYTA ze sterownika i zapisuje pliki na dysku komputera.
Niczego nie wysyła do sterownika (przywracanie ustawień dojdzie w późniejszym etapie).
"""
import datetime
import os
import tkinter as tk
from tkinter import ttk

import pello_backup as B
from pello_dialogs import messagebox, simpledialog
from pello_config import ACCENT_DK, APP_TITLE, CARD, FG, FONT_FAMILY, MUTED
from pello_params import describe, format_param

TAGS = {"zmieniony": "#fef3c7", "nowy": "#dcfce7", "usunięty": "#fee2e2"}


def _when(iso):
    try:
        return datetime.datetime.strptime(iso, B.ISO).strftime("%d-%m-%Y %H:%M")
    except (ValueError, TypeError):
        return str(iso)


class BackupView:
    def __init__(self, parent, card, px, get_data, get_host, program, set_status, notify):
        """card(parent, tytuł) -> (ramka, wnętrze); get_data() -> aktualne parametry albo None."""
        self.parent, self.px = parent, px
        self.get_data, self.get_host, self.program = get_data, get_host, program
        self.set_status, self.notify = set_status, notify
        self._records = {}
        self._ctx = None                      # (opis porównania, stare, nowe) - do odświeżenia widoku
        self.live_var = tk.BooleanVar(value=False)
        self.summary = tk.StringVar(value="Zaznacz kopię na liście i kliknij „Porównaj”.")

        # --- lista kopii
        outer, body = card(parent, "Kopie zapasowe ustawień")
        outer.pack(fill="x", pady=(10, 8))
        ttk.Label(body, style="Muted.TLabel", justify="left", wraplength=px(900),
                  text="Kopia zawiera wszystkie parametry odczytane ze sterownika (bez haseł i numeru seryjnego) "
                       "i jest zapisywana w pliku na tym komputerze. Kopia „Pierwotna” powstaje automatycznie przy "
                       "pierwszym połączeniu i nigdy nie jest nadpisywana. Ten etap tylko czyta ze sterownika – "
                       "niczego do niego nie wysyła."
                  ).pack(anchor="w", pady=(0, 8))
        bar = tk.Frame(body, bg=CARD)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(bar, text="Zrób kopię teraz", style="Accent.TButton", command=self.make_backup
                   ).pack(side="left")
        ttk.Button(bar, text="Porównaj", style="Soft.TButton", command=self.compare).pack(side="left", padx=8)
        ttk.Button(bar, text="Pokaż folder", style="Soft.TButton", command=self.open_folder).pack(side="right")
        ttk.Button(bar, text="Usuń kopię", style="Soft.TButton", command=self.delete).pack(side="right", padx=8)

        cols = (("data", "Data", 140, "w"), ("rodzaj", "Rodzaj", 90, "w"), ("sterownik", "Sterownik", 130, "w"),
                ("wersja", "Typ / wersja", 160, "w"), ("liczba", "Parametrów", 90, "e"),
                ("opis", "Opis", 300, "w"))
        self.tree = ttk.Treeview(body, columns=[c[0] for c in cols], show="headings", height=6,
                                 selectmode="extended", style="Params.Treeview")
        for key, title, width, anchor in cols:
            self.tree.heading(key, text=title, anchor="w")
            self.tree.column(key, width=px(width), anchor=anchor)
        vsb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="x", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.tag_configure("orig", foreground=ACCENT_DK)
        self.tree.bind("<Double-1>", lambda e: self.compare())

        # --- różnice
        outer2, body2 = card(parent, "Porównanie")
        outer2.pack(fill="both", expand=True, pady=(0, 10))
        top = tk.Frame(body2, bg=CARD)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, textvariable=self.summary, style="Card.TLabel", wraplength=px(640), justify="left"
                  ).pack(side="left")
        ttk.Checkbutton(top, text="Pokaż też odczyty na żywo", variable=self.live_var,
                        style="Card.TCheckbutton", command=self._render).pack(side="right")

        dcols = (("opis", "Opis", 270, "w"), ("klucz", "Parametr", 170, "w"), ("stara", "W kopii", 140, "e"),
                 ("nowa", "Teraz / nowsza", 140, "e"), ("zmiana", "Zmiana", 90, "w"))
        wrap = tk.Frame(body2, bg=CARD)
        wrap.pack(fill="both", expand=True)
        self.dtree = ttk.Treeview(wrap, columns=[c[0] for c in dcols], show="headings", selectmode="browse",
                                  style="Params.Treeview")
        for key, title, width, anchor in dcols:
            self.dtree.heading(key, text=title, anchor="w")
            self.dtree.column(key, width=px(width), anchor=anchor)
        dsb = ttk.Scrollbar(wrap, orient="vertical", command=self.dtree.yview)
        self.dtree.configure(yscrollcommand=dsb.set)
        self.dtree.pack(side="left", fill="both", expand=True)
        dsb.pack(side="right", fill="y")
        for status, color in TAGS.items():
            self.dtree.tag_configure(status, background=color)

        self.refresh_list()

    # ------------------------------------------------------------- lista
    def refresh_list(self, select=None):
        self.tree.delete(*self.tree.get_children())
        self._records = {}
        for rec in B.list_backups():
            iid = str(rec["path"])
            dev = rec["device"]
            self._records[iid] = rec
            self.tree.insert("", "end", iid=iid, tags=("orig",) if rec["kind"] == "original" else (), values=(
                _when(rec["created"]), B.KIND_TEXT.get(rec["kind"], rec["kind"]),
                dev.get("name") or dev.get("id") or "—",
                " ".join(x for x in (dev.get("type"), ("v" + dev["soft"]) if dev.get("soft") else "") if x) or "—",
                rec["count"], rec["note"]))
        if select and select in self._records:
            self.tree.selection_set(select)

    # ------------------------------------------------------------- automatyczna kopia pierwotna
    def ensure_original(self, data):
        """Wywoływane po połączeniu. Tworzy kopię pierwotną, jeśli jeszcze nie istnieje."""
        try:
            path = B.ensure_original(data, self.get_host(), self.program)
        except Exception as e:                # problem z kopią nie może zatrzymać pracy programu
            self.set_status(f"Nie udało się zapisać kopii pierwotnej: {e}")
            return None
        if path:
            self.refresh_list()
            self.set_status("Zapisano kopię pierwotną ustawień sterownika")
            self.notify("Pello: kopia pierwotna", "Zapisano kopię ustawień sterownika z pierwszego połączenia.")
        return path

    # ------------------------------------------------------------- akcje
    def make_backup(self):
        data = self.get_data()
        if not data:
            messagebox.showinfo(APP_TITLE, "Połącz się ze sterownikiem, aby zrobić kopię ustawień.")
            return
        note = simpledialog.askstring("Kopia ustawień", "Opis kopii (opcjonalnie), np. „przed zmianą krzywej”:",
                                      parent=self.parent)
        if note is None:                                      # Anuluj
            return
        try:
            path = B.save_backup(B.make_backup(data, self.get_host(), "manual", note.strip(), self.program))
        except OSError as e:
            messagebox.showerror(APP_TITLE, f"Nie udało się zapisać kopii: {e}")
            return
        self.set_status(f"Zapisano kopię ustawień: {path.name}")
        self.refresh_list(select=str(path))

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Zaznacz na liście kopię do usunięcia.")
            return
        if any(self._records[i]["kind"] == "original" for i in sel):
            messagebox.showinfo(APP_TITLE, "Kopii pierwotnej nie można usunąć z programu – to Twój punkt odniesienia.")
            return
        if not messagebox.askyesno(APP_TITLE, f"Usunąć zaznaczone kopie ({len(sel)}) z dysku?"):
            return
        for iid in sel:
            try:
                B.delete_backup(iid)
            except (OSError, ValueError) as e:
                messagebox.showerror(APP_TITLE, str(e))
        self.refresh_list()
        self.set_status("Usunięto zaznaczone kopie")

    def open_folder(self):
        try:
            B.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(B.BACKUP_DIR)                        # Windows
        except Exception:
            messagebox.showinfo(APP_TITLE, f"Kopie są zapisywane w folderze:\n{B.BACKUP_DIR}")

    # ------------------------------------------------------------- porównanie
    def _context(self, sel):
        """Zwraca (opis, stare, nowe) albo None (po pokazaniu komunikatu)."""
        if not sel:
            messagebox.showinfo(APP_TITLE, "Zaznacz na liście jedną kopię (porównanie ze stanem bieżącym "
                                           "sterownika) albo dwie kopie (porównanie ich ze sobą).")
            return None
        if len(sel) > 2:
            messagebox.showinfo(APP_TITLE, "Zaznacz jedną albo dwie kopie.")
            return None
        try:
            backups = sorted((B.load_backup(i) for i in sel),
                             key=lambda b: (b["created"], b.get("kind") != "original"))   # pierwotna = najstarsza
        except ValueError as e:
            messagebox.showerror(APP_TITLE, str(e))
            return None
        if len(backups) == 2:
            a, b = backups
            return (f"Kopia z {_when(a['created'])} → kopia z {_when(b['created'])}", a["params"], b["params"])
        current = self.get_data()
        if not current:
            messagebox.showinfo(APP_TITLE, "Aby porównać kopię ze stanem bieżącym, połącz się ze sterownikiem.")
            return None
        a = backups[0]
        return (f"Kopia z {_when(a['created'])} → stan bieżący sterownika", a["params"], dict(current))

    def compare(self):
        ctx = self._context(self.tree.selection())
        if ctx:
            self._ctx = ctx
            self._render()

    @staticmethod
    def _fmt(key, raw):
        if raw is None:
            return "—"
        try:
            text = format_param(key, raw)
        except Exception:
            text = str(raw)
        return text if len(text) <= 44 else text[:43] + "…"

    def rows(self):
        """Wiersze porównania do wyświetlenia: (opis, klucz, stara, nowa, zmiana, tag)."""
        if not self._ctx:
            return [], 0
        _, old, new = self._ctx
        changes, hidden = B.diff(old, new, include_live=self.live_var.get())
        rows = [(describe(k), k, self._fmt(k, o), self._fmt(k, n),
                 status + (" (odczyt)" if kind == "live" else ""), status)
                for k, status, o, n, kind in changes]
        return rows, hidden

    def _render(self):
        self.dtree.delete(*self.dtree.get_children())
        if not self._ctx:
            return
        rows, hidden = self.rows()
        for r in rows:
            self.dtree.insert("", "end", values=r[:5], tags=(r[5],))
        counts = {s: sum(1 for r in rows if r[5] == s) for s in TAGS}
        text = self._ctx[0] + ":  "
        if rows:
            text += (f"zmienione {counts['zmieniony']}, nowe {counts['nowy']}, usunięte {counts['usunięty']}")
        else:
            text += "brak różnic w ustawieniach."
        if hidden:
            text += f"   (ukryto {hidden} odczytów na żywo)"
        self.summary.set(text)
