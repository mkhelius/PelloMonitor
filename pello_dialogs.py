"""
pello_dialogs.py - jednolite okna dialogowe programu (zamiast standardowych okien Windows).
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Wszystkie okienka mają ten sam wygląd co okno edycji parametru: biała karta, kolorowe kółko z symbolem
typu, pogrubiony nagłówek, treść i przyciski po prawej (główny - pomarańczowy).

Moduł jest zamiennikiem tkinter.messagebox / tkinter.simpledialog: udostępnia obiekty `messagebox`
(showinfo, showwarning, showerror, askyesno, askokcancel) i `simpledialog` (askstring) o tej samej
składni, więc w pozostałych plikach wystarczy zmienić linię importu. Dodatkowo:
  inform()          - komunikat z własnym nagłówkiem (np. „Parametr zablokowany”),
  confirm_change()  - potwierdzenie zmiany parametru z wierszami „Stara” i „Nowa” wartość,
  TreeTip           - podpowiedź po najechaniu myszką na wiersz tabeli.

Przed użyciem trzeba raz wywołać init(okno_główne, funkcja_px).
"""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

from pello_config import ACCENT, ACCENT_DK, BORDER, CARD, FG, FONT_FAMILY, LABEL_FG, MUTED, RED

_ctx = {"root": None, "px": lambda n: n}

# typ -> (symbol, kolor, domyślny nagłówek)
KINDS = {
    "info": ("i", "#2563eb", "Informacja"),
    "question": ("?", ACCENT, "Potwierdzenie"),
    "warning": ("!", "#d97706", "Uwaga"),
    "error": ("✕", RED, "Błąd"),
    "input": ("✎", ACCENT, ""),
}
INSET_BG = "#f6f7f9"


def init(root, px):
    """Rejestruje okno główne (rodzic okien) i funkcję skalowania DPI."""
    _ctx["root"], _ctx["px"] = root, px


def _px(n):
    return _ctx["px"](n)


def center(win, master=None):
    """Ustawia okno na środku okna głównego (albo ekranu, gdy okno główne jest schowane)."""
    master = master or _ctx["root"]
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    try:
        if master is not None and master.winfo_viewable():
            x = master.winfo_rootx() + (master.winfo_width() - w) // 2
            y = master.winfo_rooty() + (master.winfo_height() - h) // 3
        else:
            x = (win.winfo_screenwidth() - w) // 2
            y = (win.winfo_screenheight() - h) // 3
    except tk.TclError:
        x = y = 100
    win.geometry(f"+{max(0, x)}+{max(0, y)}")


class Dialog(tk.Toplevel):
    """Okno modalne. Po zamknięciu wynik jest w .result (wartość wciśniętego przycisku albo `cancel`)."""

    def __init__(self, title, message="", kind="info", buttons=(("OK", "ok"),), default=0, cancel=None,
                 heading=None, body=None, entry=None, width=440):
        master = _ctx["root"]
        super().__init__(master)
        self._cancel = cancel
        self.result = cancel
        self.var = None
        self._buttons = []
        self._default = default
        self.title(title)
        self.configure(bg=CARD)
        self.resizable(False, False)
        try:
            if master is not None and master.winfo_viewable():
                self.transient(master)
        except tk.TclError:
            pass

        symbol, color, std_heading = KINDS.get(kind, KINDS["info"])
        outer = tk.Frame(self, bg=CARD)
        outer.pack(fill="both", expand=True, padx=_px(22), pady=(_px(18), 0))
        size = _px(44)
        icon = tk.Canvas(outer, width=size, height=size, bg=CARD, highlightthickness=0)
        icon.create_oval(2, 2, size - 2, size - 2, fill=color, outline="")
        icon.create_text(size / 2, size / 2, text=symbol, fill="white", font=(FONT_FAMILY, 18, "bold"))
        icon.pack(side="left", anchor="n", padx=(0, _px(16)))
        text = tk.Frame(outer, bg=CARD)
        text.pack(side="left", fill="both", expand=True)
        wrap = _px(width)
        head = std_heading if heading is None else heading
        if head:
            tk.Label(text, text=head, font=(FONT_FAMILY, 13, "bold"), bg=CARD, fg=FG, anchor="w",
                     justify="left", wraplength=wrap).pack(anchor="w")
        if message:
            tk.Label(text, text=message, font=(FONT_FAMILY, 11), bg=CARD, fg=LABEL_FG, anchor="w",
                     justify="left", wraplength=wrap).pack(anchor="w", pady=(_px(6), 0))
        if entry is not None:
            self.var = tk.StringVar(value=entry)
            self.entry = ttk.Entry(text, textvariable=self.var, font=(FONT_FAMILY, 11), width=42)
            self.entry.pack(fill="x", pady=(_px(10), 0))
        if body:
            body(text, wrap)

        bar = tk.Frame(self, bg=CARD)
        bar.pack(fill="x", padx=_px(22), pady=_px(16))
        for idx in reversed(range(len(buttons))):          # pakujemy od prawej: pierwszy przycisk = lewy
            label, value = buttons[idx]
            b = ttk.Button(bar, text=label, style="Accent.TButton" if idx == 0 else "Soft.TButton",
                           command=lambda v=value: self._finish(v))
            b.pack(side="right", padx=(_px(8), 0))
            self._buttons.insert(0, b)

        self.bind("<Return>", self._on_return)
        self.bind("<Escape>", lambda e: self._finish(self._cancel))
        self.protocol("WM_DELETE_WINDOW", lambda: self._finish(self._cancel))
        center(self, master)
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.lift()
        (self.entry if self.var is not None else self._buttons[default]).focus_set()
        if self.var is not None:
            self.entry.select_range(0, "end")
        self.wait_window(self)

    def _on_return(self, event=None):
        focus = self.focus_get()
        (focus if focus in self._buttons else self._buttons[self._default]).invoke()

    def _finish(self, value):
        self.result = self.var.get() if (self.var is not None and value == "ok") else value
        self.destroy()


def _run(title, message, kind, buttons, **kw):
    return Dialog(title, message, kind, buttons, **kw).result


# ---------------------------------------------------------------- zamiennik messagebox
def showinfo(title, message, **kw):
    _run(title, message, "info", (("OK", "ok"),), cancel="ok")
    return "ok"


def showwarning(title, message, **kw):
    _run(title, message, "warning", (("OK", "ok"),), cancel="ok")
    return "ok"


def showerror(title, message, **kw):
    _run(title, message, "error", (("OK", "ok"),), cancel="ok")
    return "ok"


def askyesno(title, message, icon="question", default="yes", **kw):
    kind = icon if icon in KINDS else "question"
    return bool(_run(title, message, kind, (("Tak", True), ("Nie", False)),
                     default=0 if default == "yes" else 1, cancel=False))


def askokcancel(title, message, icon="question", default="ok", **kw):
    kind = icon if icon in KINDS else "question"
    return bool(_run(title, message, kind, (("OK", True), ("Anuluj", False)),
                     default=0 if default == "ok" else 1, cancel=False))


def askstring(title, prompt, initialvalue="", **kw):
    """Pole tekstowe; zwraca wpisany tekst (może być pusty) albo None po „Anuluj” / Esc."""
    return _run(title, prompt, "input", (("OK", "ok"), ("Anuluj", None)), entry=initialvalue or "",
                heading="", cancel=None)


messagebox = SimpleNamespace(showinfo=showinfo, showwarning=showwarning, showerror=showerror,
                             askyesno=askyesno, askokcancel=askokcancel)
simpledialog = SimpleNamespace(askstring=askstring)


# ---------------------------------------------------------------- okna specjalne
def inform(title, message, heading=None, kind="info"):
    """Komunikat z własnym nagłówkiem (np. „Parametr zablokowany”)."""
    _run(title, message, kind, (("OK", "ok"),), heading=heading, cancel="ok")


def confirm_change(title, heading, desc, key, old, new, risk_label, risk_color, note, danger=False):
    """Potwierdzenie zmiany parametru: wiersze „Stara wartość” i „Nowa wartość”. Zwraca True/False."""
    def body(parent, wrap):
        tk.Label(parent, text=desc, font=(FONT_FAMILY, 11, "bold"), bg=CARD, fg=FG, anchor="w", justify="left",
                 wraplength=wrap).pack(anchor="w", pady=(_px(4), 0))
        tk.Label(parent, text=key, font=(FONT_FAMILY, 10), bg=CARD, fg=MUTED, anchor="w").pack(anchor="w")
        box = tk.Frame(parent, bg=INSET_BG, highlightthickness=1, highlightbackground=BORDER)
        box.pack(fill="x", pady=(_px(10), 0))
        for r, (label, value, color) in enumerate((("Stara wartość", old, FG), ("Nowa wartość", new, ACCENT_DK))):
            tk.Label(box, text=label, font=(FONT_FAMILY, 10), bg=INSET_BG, fg=MUTED
                     ).grid(row=r, column=0, sticky="w", padx=_px(12), pady=_px(6))
            tk.Label(box, text=value, font=(FONT_FAMILY, 14, "bold"), bg=INSET_BG, fg=color
                     ).grid(row=r, column=1, sticky="w", padx=_px(8))
        tk.Label(parent, text=f"Ryzyko: {risk_label}", font=(FONT_FAMILY, 10, "bold"), bg=CARD, fg=risk_color,
                 anchor="w").pack(anchor="w", pady=(_px(10), 0))
        if note:
            tk.Label(parent, text=note, font=(FONT_FAMILY, 10), bg=CARD, fg=LABEL_FG, anchor="w",
                     justify="left", wraplength=wrap).pack(anchor="w", pady=(_px(4), 0))

    return bool(_run(title, "", "warning" if danger else "question",
                     (("Zapisz do sterownika", True), ("Anuluj", False)), heading=heading, body=body,
                     default=1 if danger else 0, cancel=False))


# ---------------------------------------------------------------- podpowiedź przy wierszu tabeli
class TreeTip:
    """Podpowiedź po najechaniu myszką na wiersz Treeview. text_for(iid) -> tekst albo "" (bez podpowiedzi)."""

    def __init__(self, tree, text_for, delay=500, width=380):
        self.tree, self.text_for, self.delay, self.width = tree, text_for, delay, width
        self._row = None
        self._job = None
        self._tip = None
        tree.bind("<Motion>", self._move, add="+")
        tree.bind("<Leave>", lambda e: self._reset(), add="+")
        tree.bind("<ButtonPress>", lambda e: self._reset(), add="+")
        tree.bind("<MouseWheel>", lambda e: self._reset(), add="+")

    def _move(self, event):
        row = self.tree.identify_row(event.y)
        if row == self._row:
            return
        self._reset()
        self._row = row
        if row:
            self._job = self.tree.after(self.delay, lambda: self._show(row, event.x_root, event.y_root))

    def _reset(self):
        if self._job:
            self.tree.after_cancel(self._job)
            self._job = None
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None
        self._row = None

    def _show(self, row, x, y):
        self._job = None
        text = self.text_for(row)
        if not text:
            return
        tip = tk.Toplevel(self.tree)
        tip.wm_overrideredirect(True)
        tip.wm_attributes("-topmost", True)
        frame = tk.Frame(tip, bg=CARD, highlightthickness=1, highlightbackground=ACCENT)
        frame.pack()
        tk.Label(frame, text=text, font=(FONT_FAMILY, 10), bg=CARD, fg=FG, justify="left",
                 wraplength=_px(self.width), padx=_px(10), pady=_px(8)).pack()
        tip.geometry(f"+{x + _px(16)}+{y + _px(20)}")
        self._tip = tip
