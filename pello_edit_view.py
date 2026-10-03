"""
pello_edit_view.py - edycja pojedynczych parametrów i dziennik zmian (okna i przebieg zapisu).
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Przebieg zmiany (dwuklik na wartości w zakładce „Parametry”, tylko gdy edycja odblokowana w Ustawieniach):
  1. okno z nową wartością (lista wyboru albo liczba; sprawdzana poprawność),
  2. potwierdzenie „stara → nowa wartość”; przy czerwonych parametrach dodatkowe, drugie potwierdzenie,
  3. w tle: świeży odczyt ze sterownika (wartość nie może się zmienić od otwarcia okna),
     automatyczna kopia ustawień (bez niej nic nie jest zapisywane), zapis i potwierdzenie odczytem,
  4. wpis do dziennika. Zmianę potwierdzoną odczytem można cofnąć przyciskiem „Cofnij”
     (cofnięcie przechodzi ten sam przebieg: potwierdzenia, kopia, zapis, odczyt, wpis).
"""
import datetime
import threading
import tkinter as tk
from tkinter import ttk

import pello_backup as B
import pello_edit as E
import pello_dialogs as D
import pello_journal as J
from pello_dialogs import messagebox
from pello_client import PelloWriteError
from pello_config import APP_TITLE, CARD, FG, FONT_FAMILY, MUTED, RED
from pello_params import describe, format_param, with_unit

RESULT_TEXT = {"ok": "potwierdzona odczytem", "niepotwierdzona": "NIE potwierdzona",
               "odmowa": "odrzucona przez sterownik", "błąd": "błąd połączenia"}


def _fmt(key, raw):
    if raw is None:
        return "—"
    try:
        return with_unit(key, format_param(key, raw))
    except Exception:
        return str(raw)


def _when(iso):
    try:
        return datetime.datetime.strptime(iso, J.ISO).strftime("%d-%m-%Y %H:%M:%S")
    except (ValueError, TypeError):
        return str(iso)


# ---------------------------------------------------------------- okno wpisania wartości
class ValueDialog(tk.Toplevel):
    """Okno modalne: pokazuje parametr, jego ryzyko i aktualną wartość; zwraca w .result nową wartość."""

    def __init__(self, master, key, raw, px):
        super().__init__(master)
        self.result = None
        self.key, self.raw = key, raw
        self.title("Edycja parametru")
        self.configure(bg=CARD)
        self.resizable(False, False)
        self.transient(master)
        label, what, color = E.RISK_INFO[E.risk_of(key)]
        wrap = px(460)
        pad = dict(padx=20, anchor="w")

        tk.Label(self, text=describe(key), font=(FONT_FAMILY, 13, "bold"), bg=CARD, fg=FG,
                 wraplength=wrap, justify="left").pack(pady=(16, 0), **pad)
        tk.Label(self, text=key, font=(FONT_FAMILY, 10), bg=CARD, fg=MUTED).pack(**pad)
        tk.Label(self, text=f"Ryzyko: {label} – {what}", font=(FONT_FAMILY, 10, "bold"), bg=CARD, fg=color,
                 wraplength=wrap, justify="left").pack(pady=(8, 0), **pad)
        tk.Label(self, text=f"Aktualna wartość:  {_fmt(key, raw)}", font=(FONT_FAMILY, 11), bg=CARD, fg=FG
                 ).pack(pady=(10, 4), **pad)

        row = tk.Frame(self, bg=CARD)
        row.pack(pady=(4, 0), **pad)
        tk.Label(row, text="Nowa wartość:", font=(FONT_FAMILY, 11), bg=CARD, fg=FG).pack(side="left")
        self._choices = E.choices(key)
        if self._choices is not None:
            self._labels = {f"{r} – {t}": r for r, t in self._choices}
            self.var = tk.StringVar()
            for text, r in self._labels.items():                 # zaznacz bieżącą wartość
                if E.same(r, raw):
                    self.var.set(text)
            self.widget = ttk.Combobox(row, textvariable=self.var, values=list(self._labels), state="readonly",
                                       width=26, font=(FONT_FAMILY, 11))
        else:
            self.var = tk.StringVar(value="" if raw is None else str(raw))
            self.widget = ttk.Entry(row, textvariable=self.var, width=18, font=(FONT_FAMILY, 11))
        self.widget.pack(side="left", padx=8)
        if self._choices is None:                                 # separator dziesiętny: zawsze kropka
            self.widget.bind("<KeyPress>", self._on_key)
            self.var.trace_add("write", self._fix_comma)
        unit = E.info(key)[1] if self._choices is None else ""
        if unit:
            tk.Label(row, text=unit, font=(FONT_FAMILY, 11), bg=CARD, fg=MUTED).pack(side="left")
        hint = ("Liczba z kropką dziesiętną (np. 45.5). Wpisany przecinek zamienia się na kropkę."
                if self._choices is None else "Wybierz wartość z listy.")
        tk.Label(self, text=hint, font=(FONT_FAMILY, 9), bg=CARD, fg=MUTED, wraplength=wrap, justify="left"
                 ).pack(pady=(4, 0), **pad)
        self.err = tk.Label(self, text="", font=(FONT_FAMILY, 10, "bold"), bg=CARD, fg=RED, wraplength=wrap,
                            justify="left")
        self.err.pack(pady=(6, 0), **pad)

        bar = tk.Frame(self, bg=CARD)
        bar.pack(fill="x", padx=20, pady=(10, 16))
        ttk.Button(bar, text="Anuluj", style="Soft.TButton", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Dalej…", style="Accent.TButton", command=self._ok).pack(side="right", padx=8)
        self.bind("<Return>", self._ok)
        self.bind("<Escape>", lambda e: self.destroy())

        D.center(self, master)
        self.wait_visibility()
        self.grab_set()
        self.widget.focus_set()
        self.wait_window(self)

    def _on_key(self, event):
        """Przecinek wpisany z klawiatury (też z klawiatury numerycznej) wstawia kropkę."""
        if event.char == ",":
            if self.widget.selection_present():
                self.widget.delete("sel.first", "sel.last")
            self.widget.insert("insert", ".")
            return "break"

    def _fix_comma(self, *_):
        text = self.var.get()                                     # np. po wklejeniu tekstu z przecinkiem
        if "," in text:
            self.var.set(text.replace(",", "."))

    def _ok(self, event=None):
        text = self.var.get()
        if self._choices is not None:
            text = self._labels.get(text, "")
        value, error = E.parse_new(self.key, self.raw, text)
        if error:
            self.err.config(text=error)
            return
        self.result = value
        self.destroy()


# ---------------------------------------------------------------- kontroler edycji + dziennik
class ParamEditor:
    def __init__(self, root, parent, card, px, get_client, get_data, get_host, is_unlocked, post,
                 set_status, on_data, program):
        """card(parent, tytuł) -> (ramka, wnętrze); get_client()/get_data() zwracają None bez połączenia;
        post(fn, *args) wykonuje fn w wątku okna (wołane z wątku roboczego); on_data(dane) odświeża widoki."""
        self.root, self.px = root, px
        self.get_client, self.get_data, self.get_host = get_client, get_data, get_host
        self.is_unlocked, self.post = is_unlocked, post
        self.set_status, self.on_data, self.program = set_status, on_data, program
        self._busy = False

        outer, body = card(parent, "Dziennik zmian parametrów")
        outer.pack(fill="x", pady=(0, 10))
        bar = tk.Frame(body, bg=CARD)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="Cofnij zaznaczoną zmianę", style="Soft.TButton", command=self.undo_selected
                   ).pack(side="left")
        ttk.Label(bar, style="Muted.TLabel", text="Przed każdą zmianą powstaje automatyczna kopia "
                  "(zakładka „Kopie”). Cofnąć można zmianę potwierdzoną odczytem.").pack(side="left", padx=12)

        cols = (("lp", "Nr", 45, "e"), ("czas", "Czas", 140, "w"), ("opis", "Parametr", 260, "w"),
                ("zmiana", "Zmiana (stara → nowa)", 220, "w"), ("wynik", "Wynik", 170, "w"),
                ("kopia", "Kopia przed zmianą", 200, "w"))
        wrap = tk.Frame(body, bg=CARD)
        wrap.pack(fill="x")
        self.tree = ttk.Treeview(wrap, columns=[c[0] for c in cols], show="headings", height=5,
                                 selectmode="browse", style="Params.Treeview")
        for key, title, width, anchor in cols:
            self.tree.heading(key, text=title, anchor="w")
            self.tree.column(key, width=px(width), anchor=anchor)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="x", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.tag_configure("bad", foreground=RED)
        self.tree.tag_configure("undone", foreground=MUTED)
        self.refresh_list()

    # ------------------------------------------------------------- lista dziennika
    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for e in reversed(J.load()):
            key = e.get("key", "")
            result = RESULT_TEXT.get(e.get("result"), e.get("result", ""))
            tags = ()
            if e.get("result") != "ok":
                tags = ("bad",)
            elif e.get("undone_by"):
                result += f" (cofnięta w #{e['undone_by']})"
                tags = ("undone",)
            if e.get("undo_of"):
                result += f" – cofnięcie #{e['undo_of']}"
            self.tree.insert("", "end", iid=str(e["id"]), tags=tags, values=(
                e["id"], _when(e.get("time")), e.get("desc") or key,
                f"{_fmt(key, e.get('old'))} → {_fmt(key, e.get('new'))}", result, e.get("backup", "")))

    @staticmethod
    def _explain_locked(key, reason):
        hard = reason.startswith("Zablokowane")
        D.inform(APP_TITLE, f"{describe(key)}\n({key})\n\n{reason}",
                 heading="Parametr zablokowany" if hard else "Parametr tylko do odczytu",
                 kind="warning" if hard else "info")

    # ------------------------------------------------------------- wejście: edycja wartości
    def _ready(self):
        """Wspólne warunki wstępne zapisu. Zwraca (klient, dane) albo None po pokazaniu komunikatu."""
        if not self.is_unlocked():
            messagebox.showinfo(APP_TITLE, "Edycja parametrów jest wyłączona (tryb tylko do odczytu).\n\n"
                                           "Odblokujesz ją w zakładce Ustawienia → „Edycja parametrów”.")
            return None
        client, data = self.get_client(), self.get_data()
        if not client or not data:
            messagebox.showinfo(APP_TITLE, "Połącz się ze sterownikiem, aby zmieniać parametry.")
            return None
        if self._busy:
            messagebox.showinfo(APP_TITLE, "Poprzednia zmiana jest jeszcze zapisywana – poczekaj chwilę.")
            return None
        return client, data

    def edit_value(self, key):
        reason = E.why_not_editable(key)                     # powód blokady ma pierwszeństwo przed resztą
        if reason:
            self._explain_locked(key, reason)
            return
        ready = self._ready()
        if not ready:
            return
        _, data = ready
        if key not in data:
            messagebox.showinfo(APP_TITLE, "Nie ma bieżącej wartości tego parametru – poczekaj na odczyt.")
            return
        dlg = ValueDialog(self.root, key, data[key], self.px)
        if dlg.result is None:
            return
        self._confirm_and_apply(key, data[key], dlg.result)

    # ------------------------------------------------------------- wejście: cofnięcie
    def undo_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Zaznacz w dzienniku zmianę, którą chcesz cofnąć.")
            return
        entry = J.get(int(sel[0]))
        if not J.undoable(entry):
            messagebox.showinfo(APP_TITLE, "Tej zmiany nie można cofnąć: cofnąć można tylko zmianę "
                                           "potwierdzoną odczytem, która nie została jeszcze cofnięta.")
            return
        key = entry["key"]
        reason = E.why_not_editable(key)
        if reason:
            self._explain_locked(key, reason)
            return
        ready = self._ready()
        if not ready:
            return
        _, data = ready
        current = data.get(key)
        if not E.same(current, entry.get("new")):
            if not messagebox.askyesno(
                    APP_TITLE, f"Od tej zmiany wartość parametru została zmieniona jeszcze raz.\n\n"
                               f"Wartość ustawiona przez zmianę #{entry['id']}:  {_fmt(key, entry.get('new'))}\n"
                               f"Wartość obecna:  {_fmt(key, current)}\n\n"
                               f"Cofnięcie ustawi:  {_fmt(key, entry.get('old'))}\n\nKontynuować?",
                    icon="warning", default="no"):
                return
        self._confirm_and_apply(key, current, str(entry.get("old", "")), undo_of=entry["id"])

    # ------------------------------------------------------------- potwierdzenia i start zapisu
    def _confirm_and_apply(self, key, old, new, undo_of=None):
        if E.same(old, new):
            messagebox.showinfo(APP_TITLE, "Nowa wartość jest taka sama jak obecna – nic nie zmieniam.")
            return
        risk = E.risk_of(key)
        label, what_risk, color = E.RISK_INFO[risk]
        note = ("Przed zapisem program zrobi automatyczną kopię ustawień sterownika, a po zapisie sprawdzi "
                "wartość odczytem.")
        if not D.confirm_change(APP_TITLE, "Cofnięcie zmiany" if undo_of else "Zmiana parametru", describe(key),
                                key, _fmt(key, old), _fmt(key, new), f"{label} – {what_risk}", color, note,
                                danger=risk == E.RED):
            return
        if risk == E.RED:
            if not messagebox.askyesno(
                    APP_TITLE, f"UWAGA – parametr o wysokim ryzyku\n\n{describe(key)} ({key}):  "
                               f"{_fmt(key, old)} → {_fmt(key, new)}\n\nTo ustawienie dotyczy spalania, sieci "
                               "albo serwisu. Błędna wartość może rozregulować kocioł, zatrzymać go albo "
                               "odciąć zdalny dostęp do sterownika.\n\nCzy na pewno chcesz je zmienić?",
                    icon="warning", default="no"):
                return
        client = self.get_client()
        if not client:
            return
        self._busy = True
        self.set_status(f"Zapisuję do sterownika: {describe(key)}…")
        args = (client, self.get_host(), key, old, str(new), describe(key), risk, undo_of)
        threading.Thread(target=lambda: self.post(self._finished, self._run_change(*args)),
                         daemon=True).start()

    # ------------------------------------------------------------- zapis w wątku roboczym (bez okien!)
    def _run_change(self, client, host, key, expected_old, new, desc, risk, undo_of):
        """Świeży odczyt -> sprawdzenie -> kopia -> zapis z potwierdzeniem -> wpis do dziennika.
        Zwraca słownik {entry, data, problem, journal_error}; nie dotyka okien."""
        res = {"entry": None, "data": None, "problem": "", "journal_error": ""}
        try:
            fresh = client.read_all()
        except Exception as e:
            res["problem"] = f"Nie udało się odczytać sterownika przed zmianą – nic nie zapisano.\n{e}"
            return res
        res["data"] = fresh
        if not E.same(fresh.get(key), expected_old):
            res["problem"] = (f"Wartość parametru zmieniła się od chwili otwarcia okna "
                              f"(teraz: {_fmt(key, fresh.get(key))}). Nic nie zapisano – spróbuj ponownie.")
            return res
        if len([k for k in fresh if not B.is_secret(k)]) < B.MIN_KEYS:
            res["problem"] = "Odpowiedź sterownika jest niepełna – nie można zrobić kopii, więc nic nie zapisano."
            return res
        note = f"Przed zmianą: {key} {expected_old} → {new}"
        try:
            backup_path = B.save_backup(B.make_backup(fresh, host, "auto", note, self.program))
        except OSError as e:
            res["problem"] = f"Nie udało się zapisać kopii przed zmianą – nic nie zapisano.\n{e}"
            return res

        entry = {"time": datetime.datetime.now().strftime(J.ISO), "host": str(host or ""),
                 "device": fresh.get("device_id", ""), "key": key, "desc": desc, "risk": risk,
                 "old": "" if expected_old is None else str(expected_old), "new": new, "actual": None,
                 "result": "", "error": "", "backup": backup_path.name, "undo_of": undo_of,
                 "undone_by": None}
        try:
            ok, actual, data = client.set_and_verify(key, new)
            entry["actual"], entry["result"] = actual, "ok" if ok else "niepotwierdzona"
            res["data"] = data or fresh
        except PelloWriteError as e:                     # sterownik odmówił (np. access_denied)
            entry["result"], entry["error"] = "odmowa", str(e)
        except Exception as e:                           # błąd sieci - nie wiadomo, czy zapis doszedł
            entry["result"], entry["error"] = "błąd", str(e)
        try:
            entry = J.add(entry)
            if undo_of and entry["result"] == "ok":
                J.mark_undone(undo_of, entry["id"])
        except OSError as e:
            res["journal_error"] = str(e)
        res["entry"] = entry
        return res

    # ------------------------------------------------------------- koniec zapisu (wątek okna)
    def _finished(self, res):
        self._busy = False
        self.refresh_list()
        if res.get("data"):
            self.on_data(res["data"])
        entry = res.get("entry")
        if res.get("problem") or not entry:
            self.set_status("NIE zapisano zmiany parametru")
            messagebox.showerror(APP_TITLE, res.get("problem") or "Nie zapisano zmiany.")
            return
        key, result = entry["key"], entry["result"]
        change = f"{_fmt(key, entry['old'])} → {_fmt(key, entry['new'])}"
        if result == "ok":
            self.set_status(f"Zmieniono {entry['desc']}: {change} – potwierdzone odczytem (wpis #{entry['id']})")
        elif result == "niepotwierdzona":
            self.set_status(f"Sterownik nie potwierdził zmiany: {entry['desc']}")
            messagebox.showwarning(
                APP_TITLE, f"Sterownik nie potwierdził zmiany „{key}”.\n\nOczekiwano: {_fmt(key, entry['new'])}\n"
                           f"Odczytano: {_fmt(key, entry['actual'])}\n\nMożliwe przyczyny: brak uprawnień do "
                           "zapisu, wartość poza dozwolonym zakresem albo sterownik jeszcze jej nie zastosował.\n"
                           f"Kopia sprzed zmiany: {entry['backup']}")
        elif result == "odmowa":
            self.set_status(f"Sterownik odrzucił zmianę: {entry['desc']}")
            messagebox.showerror(APP_TITLE, f"{entry['error']}\n\nKopia sprzed próby: {entry['backup']}")
        else:
            self.set_status(f"Błąd podczas zapisu: {entry['desc']}")
            messagebox.showerror(
                APP_TITLE, f"Nie udało się wysłać zmiany: {entry['error']}\n\nNie wiadomo, czy sterownik ją "
                           f"zastosował – sprawdź wartość odczytem.\nKopia sprzed próby: {entry['backup']}")
        if res.get("journal_error"):
            messagebox.showwarning(APP_TITLE, "Zmiana została wykonana, ale nie udało się zapisać wpisu "
                                              f"w dzienniku:\n{res['journal_error']}")
