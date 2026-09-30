"""
Pello 3.5 Monitor - wersja FREE
Autor: Mariusz <mk.helius@gmail.com>

Odczyt i sterowanie sterownikiem Pello 3.5 (esterownik.pl).

Pliki programu:
  pello_monitor.py  - okno programu (ten plik, uruchamiać właśnie ten)
  pello_config.py   - stałe, kolory, teksty, funkcje pomocnicze
  pello_client.py   - komunikacja ze sterownikiem i historia CSV (parser modułów BT4/termostaty)
  pello_tray.py     - ikona płomienia, zasobnik systemowy, powiadomienia
  pello_schema.py   - zakładka „Schemat instalacji” (rysunek hydrauliczny z odczytami)

Zależności: pystray, Pillow (tylko zasobnik i powiadomienia).
Parametr uruchomienia:  --tray  (start zminimalizowany do zasobnika)
"""
import datetime
import json
import math
import os
import sys
import threading
import tkinter as tk
import tkinter.font as tkfont
import urllib.parse
import webbrowser
from collections import deque
from tkinter import ttk, messagebox

from pello_config import *          # stałe, kolory, GROUPS, helpery
from pello_client import PelloClient, load_history, write_csv
from pello_tray import TRAY_OK, Tray, icon_png_base64
from pello_schema import SchemaView


class ScrollFrame(tk.Frame):
    """Przewijana ramka (kółko myszy działa tylko, gdy kursor jest nad nią)."""

    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")

    def _on_wheel(self, e):
        try:
            w = self.winfo_containing(e.x_root, e.y_root)
        except Exception:
            return
        if w is None or not str(w).startswith(str(self)):
            return
        if self.inner.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-e.delta / 120), "units")


# ---------------------------------------------------------------- aplikacja
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.sc = max(1.0, self.winfo_fpixels("1i") / 96.0)   # skala DPI
        self.title(f"{APP_TITLE} – wersja {APP_EDITION}")
        self._set_window_icon()
        w = min(self.px(1040), self.winfo_screenwidth() - 40)
        h = min(self.px(840), self.winfo_screenheight() - 80)
        self.geometry(f"{w}x{h}")
        self.minsize(min(self.px(900), w), min(self.px(640), h))
        self.configure(bg=BG)

        self.client = None
        self.running = False
        self.gen = 0
        self.after_id = None
        self.units = {k: u for g in GROUPS.values() for k, _, u in g}
        self.value_labels = {}

        self.history = deque(maxlen=20000)   # (datetime, {klucz: float})
        self.prev_alarms = {}
        self.alarm_active = False
        self.fuel_notified = False
        self.fail_count = 0
        self.offline_notified = False
        self.csv_error = ""
        self.hint_shown = False
        self.tray = Tray(APP_TITLE, lambda: self.after(0, self.show_window),
                         lambda: self.after(0, self.quit_app))

        self._setup_style()
        self.f_legend = tkfont.Font(family=FONT_FAMILY, size=10, weight="bold")
        self._build_ui()
        self._load_config()
        self.history.extend(load_history())
        self._start_tray()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(200, self.draw_chart)

        if not self.host_var.get().strip():
            self.nb.select(self.tab_set)          # pierwsze uruchomienie -> Ustawienia
        if "--tray" in sys.argv and self.tray.ok:
            self.after(100, self.withdraw)
        if self.auto_var.get() and self.host_var.get().strip():
            self.after(500, self.toggle)

    def _set_window_icon(self):
        try:
            data = icon_png_base64(64)
            if data:
                self._win_icon = tk.PhotoImage(data=data)
                self.iconphoto(True, self._win_icon)
        except Exception:
            pass

    def px(self, n):
        return int(round(n * getattr(self, "sc", 1.0)))

    # ------------------------------------------------------------- styl
    def _setup_style(self):
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            try:
                tkfont.nametofont(name).configure(family=FONT_FAMILY, size=10)
            except tk.TclError:
                pass
        self.option_add("*TCombobox*Listbox.font", (FONT_FAMILY, 11))
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=FG, font=(FONT_FAMILY, 10))
        st.configure("TFrame", background=BG)
        st.configure("Card.TLabel", background=CARD, foreground=LABEL_FG, font=(FONT_FAMILY, 11))
        st.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=(FONT_FAMILY, 9))
        st.configure("Warn.TLabel", background=CARD, foreground=RED, font=(FONT_FAMILY, 10))
        st.configure("Card.TCheckbutton", background=CARD, foreground=FG, font=(FONT_FAMILY, 11))
        st.map("Card.TCheckbutton", background=[("active", CARD)])

        st.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 4, 0, 0))
        st.configure("TNotebook.Tab", padding=(24, 10), font=(FONT_FAMILY, 11, "bold"),
                     background="#dde2e8", foreground=MUTED, borderwidth=0)
        st.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", ACCENT_DK)])

        st.configure("Accent.TButton", background=ACCENT, foreground="white", borderwidth=0,
                     focusthickness=0, padding=(18, 7), font=(FONT_FAMILY, 11, "bold"))
        st.map("Accent.TButton", background=[("active", ACCENT_DK), ("pressed", ACCENT_DK)])
        st.configure("Dark.TButton", background="#374151", foreground="white", borderwidth=0,
                     focusthickness=0, padding=(18, 7), font=(FONT_FAMILY, 11, "bold"))
        st.map("Dark.TButton", background=[("active", "#4b5563"), ("pressed", "#4b5563")])
        st.configure("Soft.TButton", background="#e5e7eb", foreground=FG, borderwidth=0,
                     focusthickness=0, padding=(14, 6), font=(FONT_FAMILY, 10))
        st.map("Soft.TButton", background=[("active", "#d1d5db"), ("pressed", "#d1d5db")])

        for wdg in ("TEntry", "TSpinbox", "TCombobox"):
            st.configure(wdg, fieldbackground="white", bordercolor=BORDER, lightcolor=BORDER,
                         darkcolor=BORDER, padding=5)
        st.configure("Vertical.TScrollbar", troughcolor=BG, background="#c7ccd4", bordercolor=BG,
                     arrowcolor=MUTED, relief="flat")

    def _card(self, parent, title):
        """Nowoczesne 'okno' (karta) z pogrubionym nagłówkiem sekcji."""
        outer = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        head = tk.Frame(outer, bg=CARD)
        head.pack(fill="x")
        tk.Frame(head, bg=ACCENT, width=self.px(5)).pack(side="left", fill="y")
        tk.Label(head, text=title, font=FONT_SECTION, bg=CARD, fg=FG, anchor="w"
                 ).pack(side="left", padx=12, pady=10)
        tk.Frame(outer, bg=BORDER, height=1).pack(fill="x")
        body = tk.Frame(outer, bg=CARD)
        body.pack(fill="both", expand=True, padx=16, pady=(6, 10))
        return outer, body

    def _set_conn(self, state, text):
        colors = {"ok": "#22c55e", "wait": "#eab308", "err": "#ef4444", "off": "#9ca3af"}
        self.conn_dot.itemconfigure(self.conn_oval, fill=colors.get(state, "#9ca3af"))
        self.conn_var.set(text)

    # ------------------------------------------------------------- UI
    def _build_ui(self):
        self.host_var = tk.StringVar()
        self.user_var = tk.StringVar(value="root")
        self.pass_var = tk.StringVar()
        self.int_var = tk.IntVar(value=30)
        self.save_pass = tk.BooleanVar(value=False)
        self.cwu_var = tk.IntVar(value=45)
        self.kot_var = tk.IntVar(value=60)
        self.mode_var = tk.StringVar(value="Zima")
        self.csv_var = tk.BooleanVar(value=True)
        self.notify_var = tk.BooleanVar(value=True)
        self.fuel_thr_var = tk.IntVar(value=20)
        self.tray_close_var = tk.BooleanVar(value=True)
        self.auto_var = tk.BooleanVar(value=False)
        self.range_var = tk.StringVar(value="6 godzin")
        self.status = tk.StringVar(value="Rozłączony")
        self.conn_var = tk.StringVar(value="Rozłączony")
        self.dev_var = tk.StringVar(value="")

        # ---------- pasek nagłówka
        hdr = tk.Frame(self, bg=DARK)
        hdr.pack(fill="x")
        s34 = self.px(38)
        logo = tk.Canvas(hdr, width=s34, height=s34, bg=DARK, highlightthickness=0)
        logo.pack(side="left", padx=(18, 10), pady=12)
        logo.create_oval(1, 1, s34 - 1, s34 - 1, fill=ACCENT, outline="")
        k = s34 / 34.0
        flame = [(17, 5), (25, 17), (24, 26), (17, 31), (10, 26), (9, 17), (14, 14)]
        logo.create_polygon([c * k for p in flame for c in p], fill="#fff7ed", outline="")
        tk.Label(hdr, text="Pello 3.5", font=(FONT_FAMILY, 17, "bold"), bg=DARK, fg="white"
                 ).pack(side="left")
        tk.Label(hdr, text="monitor pieca", font=(FONT_FAMILY, 10), bg=DARK, fg="#9ca3af"
                 ).pack(side="left", padx=(10, 0), pady=(6, 0))
        tk.Label(hdr, text=APP_EDITION, font=(FONT_FAMILY, 9, "bold"), bg=ACCENT, fg="white",
                 padx=9, pady=1).pack(side="left", padx=(12, 0), pady=(6, 0))
        # info o sterowniku (device_name | IP | wersja softu) - po połaczeniu
        tk.Label(hdr, textvariable=self.dev_var, font=(FONT_FAMILY, 10), bg=DARK, fg="#9ca3af"
                 ).pack(side="left", padx=(16, 0), pady=(6, 0))

        self.btn = ttk.Button(hdr, text="Połącz", style="Accent.TButton", command=self.toggle)
        self.btn.pack(side="right", padx=18)
        tk.Label(hdr, textvariable=self.conn_var, font=(FONT_FAMILY, 11), bg=DARK, fg="#e5e7eb"
                 ).pack(side="right", padx=(0, 6))
        d = self.px(14)
        self.conn_dot = tk.Canvas(hdr, width=d, height=d, bg=DARK, highlightthickness=0)
        self.conn_dot.pack(side="right", padx=(0, 4))
        self.conn_oval = self.conn_dot.create_oval(1, 1, d - 1, d - 1, fill="#9ca3af", outline="")

        # ---------- pasek stanu (na dole)
        bar = tk.Frame(self, bg="#e5e7eb")
        bar.pack(side="bottom", fill="x")
        author = tk.Label(bar, text=f"Autor: {AUTHOR}  ·  {AUTHOR_EMAIL}", bg="#e5e7eb", fg=ACCENT_DK,
                          font=(FONT_FAMILY, 9, "bold"), cursor="hand2")
        author.pack(side="right", padx=14, pady=5)
        author.bind("<Button-1>", lambda e: self.mail_author())
        tk.Label(bar, textvariable=self.status, anchor="w", bg="#e5e7eb", fg=LABEL_FG,
                 font=(FONT_FAMILY, 9)).pack(side="left", fill="x", padx=14, pady=5)

        # ---------- zakładki
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=14, pady=(8, 6))
        tab_read = ScrollFrame(self.nb, BG)
        tab_ctl = tk.Frame(self.nb, bg=BG)
        tab_chart = tk.Frame(self.nb, bg=BG)
        self.tab_set = ScrollFrame(self.nb, BG)
        tab_schema = tk.Frame(self.nb, bg=BG)
        self.nb.add(tab_read, text="Odczyty")
        self.nb.add(tab_schema, text="Schemat instalacji")
        self.nb.add(tab_ctl, text="Sterowanie")
        self.nb.add(tab_chart, text="Wykres")
        self.nb.add(self.tab_set, text="Ustawienia")
        tab_info = ScrollFrame(self.nb, BG)
        self.nb.add(tab_info, text="Info")
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.schema = SchemaView(tab_schema)
        self._build_readings(tab_read.inner)
        self._build_controls(tab_ctl)
        self._build_chart(tab_chart)
        self._build_settings(self.tab_set.inner)
        self._build_info(tab_info.inner)

    def _build_readings(self, parent):
        parent.grid_columnconfigure(0, weight=1, uniform="col")
        parent.grid_columnconfigure(1, weight=1, uniform="col")
        cols = [tk.Frame(parent, bg=BG), tk.Frame(parent, bg=BG)]
        cols[0].grid(row=0, column=0, sticky="new", padx=(0, 7), pady=(10, 4))
        cols[1].grid(row=0, column=1, sticky="new", padx=(7, 0), pady=(10, 4))
        layout = {"Temperatury i moc": 0, "Paliwo": 0, "Podajnik i kalibracja": 0,
                  "Czujnik pokojowy BT4": 0, "Info o sterowniku": 0,
                  "Stan urządzeń": 1, "Ciśnienie i wentylator": 1,
                  "Serwis wymiennika": 1, "Moduł CQ i energia": 1,
                  "Alarmy": 1}
        for gname, items in GROUPS.items():
            card, body = self._card(cols[layout[gname]], gname)
            card.pack(fill="x", pady=(0, 14))
            for i, (key, name, _) in enumerate(items):
                row = tk.Frame(body, bg=CARD)
                row.pack(fill="x")
                tk.Label(row, text=name, font=FONT_LABEL, bg=CARD, fg=LABEL_FG, anchor="w"
                         ).pack(side="left", pady=6)
                lbl = tk.Label(row, text="—", font=FONT_VALUE, bg=CARD, fg=FG, anchor="e")
                lbl.pack(side="right", padx=(12, 0))
                self.value_labels[key] = lbl
                if i < len(items) - 1:
                    tk.Frame(body, bg=ROWSEP, height=1).pack(fill="x")

    def _build_controls(self, parent):
        card, body = self._card(parent, "Nastawy pieca")
        card.pack(fill="x", pady=10)
        spin = dict(width=6, font=(FONT_FAMILY, 14, "bold"))

        def row(r, text, hint):
            ttk.Label(body, text=text, style="Card.TLabel", font=FONT_LABEL
                      ).grid(row=r, column=0, sticky="w", pady=10)
            ttk.Label(body, text=hint, style="Muted.TLabel").grid(row=r, column=1, sticky="w", padx=14)

        row(0, "Zadana temperatura CWU", "10 – 60 °C")
        ttk.Spinbox(body, from_=10, to=60, textvariable=self.cwu_var, **spin).grid(row=0, column=2, padx=8)
        ttk.Button(body, text="Ustaw", style="Accent.TButton",
                   command=lambda: self.set_value("cwu_tzad", self.cwu_var.get(), 10, 60)
                   ).grid(row=0, column=3, padx=(8, 0))

        row(1, "Zadana temperatura kotła", "30 – 80 °C")
        ttk.Spinbox(body, from_=30, to=80, textvariable=self.kot_var, **spin).grid(row=1, column=2, padx=8)
        ttk.Button(body, text="Ustaw", style="Accent.TButton",
                   command=lambda: self.set_value("kot_tzad", self.kot_var.get(), 30, 80)
                   ).grid(row=1, column=3, padx=(8, 0))

        row(2, "Tryb pracy", "Zima / Lato")
        ttk.Combobox(body, textvariable=self.mode_var, values=["Zima", "Lato"], state="readonly",
                     width=7, font=(FONT_FAMILY, 13, "bold")).grid(row=2, column=2, padx=8)
        ttk.Button(body, text="Ustaw", style="Accent.TButton", command=self.set_mode
                   ).grid(row=2, column=3, padx=(8, 0))

    def _build_chart(self, parent):
        card, body = self._card(parent, "Temperatury w czasie")
        card.pack(fill="both", expand=True, pady=10)
        top = tk.Frame(body, bg=CARD)
        top.pack(fill="x")
        ttk.Label(top, text="Zakres:", style="Card.TLabel").pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.range_var, values=list(RANGES), state="readonly",
                          width=11, font=(FONT_FAMILY, 10))
        cb.pack(side="left", padx=(6, 16))
        cb.bind("<<ComboboxSelected>>", lambda e: self.draw_chart())
        self.series_vars = {}
        for key, name, color, default in CHART_SERIES:
            v = tk.BooleanVar(value=default)
            self.series_vars[key] = v
            tk.Checkbutton(top, text=name, variable=v, fg=color, activeforeground=color, bg=CARD,
                           activebackground=CARD, font=(FONT_FAMILY, 10, "bold"),
                           command=self.draw_chart).pack(side="left", padx=4)
        self.canvas = tk.Canvas(body, bg=CARD, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=(8, 0))
        self.canvas.bind("<Configure>", lambda e: self.draw_chart())

    def _on_tab_changed(self, event=None):
        self.after(50, self.draw_chart)
        self.after(60, self.schema.redraw)

    def _wrap_label(self, parent, text, **kw):
        """Etykieta z zawijaniem tekstu dopasowanym do szerokości karty."""
        lbl = tk.Label(parent, text=text, bg=CARD, fg=kw.pop("fg", LABEL_FG), justify="left", anchor="w",
                       font=kw.pop("font", (FONT_FAMILY, 11)), **kw)
        parent.bind("<Configure>", lambda e: lbl.config(wraplength=max(200, e.width - 8)), add="+")
        return lbl

    def _build_info(self, parent):
        # --- o programie
        card, body = self._card(parent, "O programie")
        card.pack(fill="x", pady=(10, 12))
        top = tk.Frame(body, bg=CARD)
        top.pack(fill="x", pady=(4, 8))
        s = self.px(56)
        logo = tk.Canvas(top, width=s, height=s, bg=CARD, highlightthickness=0)
        logo.pack(side="left", padx=(0, 14))
        logo.create_oval(1, 1, s - 1, s - 1, fill=DARK, outline=ACCENT, width=3)
        k = s / 64.0
        flame = [(32, 10), (46, 32), (44, 48), (32, 54), (20, 48), (18, 32), (26, 26)]
        logo.create_polygon([c * k for p in flame for c in p], fill=ACCENT, outline="")
        core = [(32, 30), (39, 42), (32, 50), (25, 42)]
        logo.create_polygon([c * k for p in core for c in p], fill="#ffeb82", outline="")
        txt = tk.Frame(top, bg=CARD)
        txt.pack(side="left")
        line = tk.Frame(txt, bg=CARD)
        line.pack(anchor="w")
        tk.Label(line, text=APP_TITLE, font=(FONT_FAMILY, 18, "bold"), bg=CARD, fg=FG).pack(side="left")
        tk.Label(line, text=APP_EDITION, font=(FONT_FAMILY, 10, "bold"), bg=ACCENT, fg="white",
                 padx=9, pady=1).pack(side="left", padx=(12, 0), pady=(4, 0))
        tk.Label(txt, text=f"Wersja {APP_VERSION}   ·   {COPYRIGHT}", font=(FONT_FAMILY, 10),
                 bg=CARD, fg=MUTED).pack(anchor="w")
        self._wrap_label(body, "Program do odczytu i sterowania palnikiem Pello 3.5 (sterownik esterownik.pl) "
                               "z poziomu komputera z Windows. Możliwości:").pack(fill="x", pady=(4, 4))
        for f in FEATURES:
            self._wrap_label(body, "•  " + f).pack(fill="x", padx=(10, 0), pady=1)

        # --- autor
        card, body = self._card(parent, "Autor i kontakt")
        card.pack(fill="x", pady=(0, 12))
        g = tk.Frame(body, bg=CARD)
        g.pack(fill="x", pady=4)
        tk.Label(g, text="Autor", font=FONT_LABEL, bg=CARD, fg=LABEL_FG).grid(row=0, column=0, sticky="w", pady=5)
        tk.Label(g, text=AUTHOR, font=FONT_VALUE, bg=CARD, fg=FG).grid(row=0, column=1, sticky="w", padx=20)
        tk.Label(g, text="E-mail", font=FONT_LABEL, bg=CARD, fg=LABEL_FG).grid(row=1, column=0, sticky="w", pady=5)
        mail = tk.Label(g, text=AUTHOR_EMAIL, font=(FONT_FAMILY, VALUE_PT, "bold", "underline"),
                        bg=CARD, fg=ACCENT_DK, cursor="hand2")
        mail.grid(row=1, column=1, sticky="w", padx=20)
        mail.bind("<Button-1>", lambda e: self.mail_author())
        btns = tk.Frame(body, bg=CARD)
        btns.pack(anchor="w", pady=(6, 2))
        ttk.Button(btns, text="Napisz e-mail", style="Accent.TButton", command=self.mail_author
                   ).pack(side="left")
        ttk.Button(btns, text="Kopiuj adres", style="Soft.TButton", command=self.copy_email
                   ).pack(side="left", padx=10)
        self._wrap_label(body, "Uwagi, błędy i pomysły na nowe funkcje mile widziane – napisz.",
                         fg=MUTED, font=(FONT_FAMILY, 10)).pack(fill="x", pady=(6, 0))

        # --- licencja FREE
        card, body = self._card(parent, f"Wersja {APP_EDITION} – warunki użytkowania")
        card.pack(fill="x", pady=(0, 12))
        for para in LICENSE_TEXT:
            self._wrap_label(body, para).pack(fill="x", pady=5)
        self._wrap_label(body, COPYRIGHT + ". Wszelkie prawa zastrzeżone.", fg=MUTED,
                         font=(FONT_FAMILY, 10)).pack(fill="x", pady=(4, 0))

        # --- pliki programu
        card, body = self._card(parent, "Pliki programu")
        card.pack(fill="x", pady=(0, 12))
        self._wrap_label(body, f"Ustawienia:  {CONFIG_FILE}", fg=MUTED, font=(FONT_FAMILY, 10)).pack(fill="x", pady=2)
        self._wrap_label(body, f"Historia (CSV):  {CSV_DIR}", fg=MUTED, font=(FONT_FAMILY, 10)).pack(fill="x", pady=2)
        ttk.Button(body, text="Otwórz folder z historią", style="Soft.TButton", command=self.open_csv_dir
                   ).pack(anchor="w", pady=(8, 2))

    def _build_settings(self, parent):
        pad = dict(sticky="w", pady=4)

        # --- połączenie
        card, body = self._card(parent, "Połączenie ze sterownikiem")
        card.pack(fill="x", pady=(10, 12))
        for r, (label, var, show) in enumerate([
            ("Adres IP sterownika", self.host_var, None),
            ("Użytkownik", self.user_var, None),
            ("Hasło", self.pass_var, "*"),
        ]):
            ttk.Label(body, text=label, style="Card.TLabel").grid(row=r, column=0, padx=(0, 16), **pad)
            ttk.Entry(body, textvariable=var, show=show, width=28, font=(FONT_FAMILY, 11)
                      ).grid(row=r, column=1, **pad)
        ttk.Label(body, text="Odświeżanie (sekundy)", style="Card.TLabel").grid(row=3, column=0, padx=(0, 16), **pad)
        ttk.Spinbox(body, from_=5, to=3600, textvariable=self.int_var, width=8, font=(FONT_FAMILY, 11)
                    ).grid(row=3, column=1, **pad)
        ttk.Checkbutton(body, text="Zapamiętaj hasło", variable=self.save_pass, style="Card.TCheckbutton"
                        ).grid(row=4, column=0, columnspan=2, **pad)
        ttk.Checkbutton(body, text="Łącz automatycznie po uruchomieniu programu", variable=self.auto_var,
                        style="Card.TCheckbutton").grid(row=5, column=0, columnspan=2, **pad)

        # --- historia CSV
        card, body = self._card(parent, "Historia pracy (CSV)")
        card.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(body, text="Zapisuj odczyty do plików CSV", variable=self.csv_var,
                        style="Card.TCheckbutton").pack(anchor="w", pady=4)
        ttk.Label(body, text=f"Folder: {CSV_DIR}", style="Muted.TLabel").pack(anchor="w")
        ttk.Button(body, text="Otwórz folder z historią", style="Soft.TButton", command=self.open_csv_dir
                   ).pack(anchor="w", pady=(8, 2))

        # --- powiadomienia i zasobnik
        card, body = self._card(parent, "Powiadomienia i zasobnik")
        card.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(body, text="Powiadomienia Windows (alarmy, paliwo, brak połączenia)",
                        variable=self.notify_var, style="Card.TCheckbutton").pack(anchor="w", pady=4)
        f = tk.Frame(body, bg=CARD)
        f.pack(anchor="w", pady=4)
        ttk.Label(f, text="Ostrzegaj, gdy paliwo spadnie poniżej (%):", style="Card.TLabel").pack(side="left")
        ttk.Spinbox(f, from_=1, to=90, textvariable=self.fuel_thr_var, width=5, font=(FONT_FAMILY, 11)
                    ).pack(side="left", padx=8)
        ttk.Button(body, text="Wyślij testowe powiadomienie", style="Soft.TButton",
                   command=lambda: self.notify("Pello Monitor", "Testowe powiadomienie – działa!", force=True)
                   ).pack(anchor="w", pady=(4, 10))
        ttk.Checkbutton(body, text="Zamknięcie okna (X) chowa program do zasobnika",
                        variable=self.tray_close_var, style="Card.TCheckbutton").pack(anchor="w", pady=4)
        if not TRAY_OK:
            ttk.Label(body, style="Warn.TLabel", wraplength=self.px(560),
                      text="Brak bibliotek pystray / Pillow – zasobnik i powiadomienia są wyłączone. "
                           "Zainstaluj: pip install pystray pillow").pack(anchor="w", pady=8)

    # ------------------------------------------------------------- konfiguracja
    def _load_config(self):
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return
        self.host_var.set(cfg.get("host", ""))
        self.user_var.set(cfg.get("user", "root"))
        self.pass_var.set(cfg.get("password", ""))
        self.save_pass.set(bool(cfg.get("password")))
        self.int_var.set(cfg.get("interval", 30))
        self.csv_var.set(cfg.get("csv", True))
        self.notify_var.set(cfg.get("notify", True))
        self.fuel_thr_var.set(cfg.get("fuel_threshold", 20))
        self.tray_close_var.set(cfg.get("close_to_tray", True))
        self.auto_var.set(cfg.get("auto_connect", False))
        self.range_var.set(cfg.get("range", "6 godzin"))

    def _save_config(self):
        cfg = {
            "host": self.host_var.get(),
            "user": self.user_var.get(),
            "interval": safe_int(self.int_var, 30),
            "csv": self.csv_var.get(),
            "notify": self.notify_var.get(),
            "fuel_threshold": safe_int(self.fuel_thr_var, 20),
            "close_to_tray": self.tray_close_var.get(),
            "auto_connect": self.auto_var.get(),
            "range": self.range_var.get(),
        }
        if self.save_pass.get():
            cfg["password"] = self.pass_var.get()
        try:
            CONFIG_FILE.write_text(json.dumps(cfg), encoding="utf-8")
        except Exception:
            pass

    # ------------------------------------------------------------- zasobnik / powiadomienia
    def _start_tray(self):
        self.tray.start()

    def _set_tray(self, state, tooltip=None):
        self.tray.set_state(state, tooltip)

    def notify(self, title, msg, force=False):
        if force or self.notify_var.get():
            self.tray.notify(title, msg)

    def mail_author(self):
        webbrowser.open(f"mailto:{AUTHOR_EMAIL}?subject=" + urllib.parse.quote(f"{APP_TITLE} {APP_VERSION}"))

    def copy_email(self):
        self.clipboard_clear()
        self.clipboard_append(AUTHOR_EMAIL)
        self.status.set(f"Skopiowano adres: {AUTHOR_EMAIL}")

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_close(self):
        if self.tray.ok and self.tray_close_var.get():
            self.withdraw()
            if not self.hint_shown:
                self.hint_shown = True
                self.notify("Pello Monitor działa w tle",
                            "Kliknij ikonę w zasobniku, aby otworzyć okno.", force=True)
        else:
            self.quit_app()

    def quit_app(self):
        self._save_config()
        self.running = False
        self.gen += 1
        self.tray.stop()
        self.destroy()

    # ------------------------------------------------------------- połączenie / odczyt
    def toggle(self):
        if self.running:
            self.running = False
            self.gen += 1
            if self.after_id:
                self.after_cancel(self.after_id)
            self.btn.config(text="Połącz", style="Accent.TButton")
            self.status.set("Rozłączony")
            self._set_conn("off", "Rozłączony")
            self.schema.update(None)
            self._set_tray("off", "Pello: rozłączony")
            return
        if not self.host_var.get().strip():
            self.nb.select(self.tab_set)
            messagebox.showwarning(APP_TITLE, "Podaj adres IP sterownika w zakładce Ustawienia.")
            return
        self.client = PelloClient(self.host_var.get(), self.user_var.get(), self.pass_var.get())
        self._save_config()
        self.running = True
        self.gen += 1
        self.fail_count = 0
        self.btn.config(text="Rozłącz", style="Dark.TButton")
        self.status.set("Łączenie…")
        self._set_conn("wait", "Łączenie…")
        self.poll()

    def poll(self):
        if not self.running:
            return
        threading.Thread(target=self._fetch, args=(self.gen,), daemon=True).start()

    def _fetch(self, gen):
        try:
            data = self.client.read_all()
            self.after(0, self._update, gen, data, None)
        except Exception as e:
            self.after(0, self._update, gen, None, e)

    def _update(self, gen, data, err):
        if not self.running or gen != self.gen:
            return
        if err:
            self._on_error(err)
        else:
            self._on_data(data)
        self.after_id = self.after(max(5, safe_int(self.int_var, 30)) * 1000, self.poll)

    def _on_error(self, err):
        self.fail_count += 1
        self.status.set(f"Błąd: {err}")
        self._set_conn("err", "Brak połączenia")
        self.schema.set_offline(True)
        self._set_tray("off", "Pello: brak połączenia")
        if self.fail_count >= 3 and not self.offline_notified:
            self.offline_notified = True
            self.notify("Pello: brak połączenia", f"Sterownik {self.host_var.get()} nie odpowiada.")

    def _on_data(self, data):
        now = datetime.datetime.now()
        self.fail_count = 0
        if self.offline_notified:
            self.offline_notified = False
            self.notify("Pello: połączenie przywrócone", "Sterownik znowu odpowiada.")

        self._set_conn("ok", "Połączono")

        # info o sterowniku w nagłówku (device_name | IP | wersja softu)
        name, ip, soft = data.get("device_name", ""), data.get("eth_ip", ""), data.get("device_soft_version", "")
        if name or ip:
            self.dev_var.set(f"{name}  ·  {ip}" + (f"  ·  soft {soft}" if soft else ""))

        self._apply_only(data)
        self.schema.update(data, safe_int(self.fuel_thr_var, 20))
        self._sync_controls(data)
        self.history.append((now, {k: tofloat(data.get(k)) for k, _, _, _ in CHART_SERIES}))
        self.csv_error = write_csv(now, data) if self.csv_var.get() else ""
        self._check_notifications(data)

        tip = (f"Pello: kocioł {format_value('tkot_value', data.get('tkot_value'))} °C | "
               f"CO 2 {format_value('tcwu_value', data.get('tcwu_value'))} °C | "
               f"{format_value('pl_status', data.get('pl_status'))}")
        if self.alarm_active:
            tip += " | ALARM!"
        self._set_tray("alarm" if self.alarm_active else "ok", tip)
        self.draw_chart()

        msg = f"Ostatni odczyt: {now:%H:%M:%S}"
        if self.csv_error:
            msg += f"   |   {self.csv_error}"
        self.status.set(msg)

    def _apply_only(self, data):
        thr = safe_int(self.fuel_thr_var, 20)
        for key, unit in self.units.items():
            if key in data:
                txt = format_value(key, data[key])
                if unit and txt != "—":
                    txt += f" {unit}"
                self.value_labels[key].config(text=txt, fg=value_color(key, data[key], thr))

    def _sync_controls(self, data):
        try:
            focus = self.focus_get()
        except Exception:
            focus = None
        if not isinstance(focus, ttk.Spinbox):
            try:
                if "cwu_tzad" in data:
                    self.cwu_var.set(int(float(data["cwu_tzad"])))
                if "kot_tzad" in data:
                    self.kot_var.set(int(float(data["kot_tzad"])))
            except ValueError:
                pass
        if "zima_lato" in data:
            self.mode_var.set("Lato" if str(data["zima_lato"]) == "1" else "Zima")

    # ------------------------------------------------------------- powiadomienia o zdarzeniach
    def _check_notifications(self, data):
        active = []
        for key, name, _ in GROUPS["Alarmy"]:
            v = str(data.get(key, "0"))
            if v == "1":
                active.append(name)
                if self.prev_alarms.get(key, "0") != "1":
                    self.notify("⚠ ALARM pieca Pello", name)
            self.prev_alarms[key] = v
        self.alarm_active = bool(active)

        level = tofloat(data.get("fuel_level"))
        thr = safe_int(self.fuel_thr_var, 20)
        if level is not None:
            if level <= thr and not self.fuel_notified:
                self.fuel_notified = True
                self.notify("Pello: mało paliwa", f"Poziom paliwa: {level:.0f}% (próg {thr}%). Czas uzupełnić zasobnik.")
            elif level > thr + 2:
                self.fuel_notified = False

    # ------------------------------------------------------------- CSV
    def open_csv_dir(self):
        try:
            CSV_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(CSV_DIR)  # Windows
        except Exception:
            messagebox.showinfo(APP_TITLE, f"Historia jest zapisywana w:\n{CSV_DIR}")

    # ------------------------------------------------------------- wykres
    def draw_chart(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 150 or h < 120:
            return
        L, R, T, B = self.px(54), self.px(18), self.px(52), self.px(34)
        pw, ph = w - L - R, h - T - B
        hours = RANGES.get(self.range_var.get(), 6)
        now = datetime.datetime.now()
        t0 = now - datetime.timedelta(hours=hours)
        span = (now - t0).total_seconds()
        pts = [(t, d) for t, d in self.history if t >= t0]
        active = [s for s in CHART_SERIES if self.series_vars[s[0]].get()]
        vals = [d[s[0]] for _, d in pts for s in active if d.get(s[0]) is not None]

        c.create_rectangle(L, T, L + pw, T + ph, fill="#fbfbfc", outline=BORDER)
        if not vals:
            c.create_text(L + pw / 2, T + ph / 2, fill=MUTED, font=(FONT_FAMILY, 12),
                          text="Brak danych – połącz się ze sterownikiem")
            return

        lo, hi = min(vals), max(vals)
        if hi - lo < 10:
            mid = (hi + lo) / 2
            lo, hi = mid - 5, mid + 5
        raw = (hi - lo) / 5
        step = next((s for s in (1, 2, 5, 10, 20, 25, 50, 100) if s >= raw), 100)
        y0, y1 = math.floor(lo / step) * step, math.ceil(hi / step) * step

        def X(t):
            return L + (t - t0).total_seconds() / span * pw

        def Y(v):
            return T + (y1 - v) / (y1 - y0) * ph

        font = (FONT_FAMILY, 9)
        v = y0
        while v <= y1 + 1e-9:
            y = Y(v)
            c.create_line(L, y, L + pw, y, fill="#eceff3")
            c.create_text(L - 8, y, text=f"{v:g}°", anchor="e", fill=MUTED, font=font)
            v += step

        step_min = {1: 10, 6: 60, 24: 240}.get(hours, 60)
        base = datetime.datetime.combine(t0.date(), datetime.time.min)
        k = math.ceil((t0 - base).total_seconds() / (step_min * 60))
        tick = base + datetime.timedelta(minutes=k * step_min)
        while tick <= now:
            x = X(tick)
            c.create_line(x, T, x, T + ph, fill="#eceff3")
            c.create_text(x, T + ph + self.px(14), text=tick.strftime("%H:%M"), fill=MUTED, font=font)
            tick += datetime.timedelta(minutes=step_min)

        stride = max(1, len(pts) // max(1, pw))
        sample = pts[::stride]
        if pts and sample[-1] is not pts[-1]:
            sample.append(pts[-1])
        gap = max(180, 3 * safe_int(self.int_var, 30)) * stride

        def flush(seg, color):
            if len(seg) >= 4:
                c.create_line(*seg, fill=color, width=2.5, capstyle="round", joinstyle="round")
            elif len(seg) == 2:
                c.create_oval(seg[0] - 2, seg[1] - 2, seg[0] + 2, seg[1] + 2, fill=color, outline=color)

        lx = L + 6
        ly = self.px(16)
        for key, name, color, _ in active:
            seg, last_t, last_v = [], None, None
            for t, d in sample:
                val = d.get(key)
                if val is None:
                    flush(seg, color)
                    seg, last_t = [], None
                    continue
                if last_t is not None and (t - last_t).total_seconds() > gap:
                    flush(seg, color)
                    seg = []
                seg += [X(t), Y(val)]
                last_t, last_v = t, val
            flush(seg, color)

            label = name if last_v is None else f"{name} {last_v:.1f}°"
            item_w = self.px(26) + self.f_legend.measure(label)
            if lx + item_w > w - R and lx > L + 6:      # zawiń legendę do drugiego wiersza
                lx, ly = L + 6, ly + self.px(18)
            c.create_line(lx, ly, lx + self.px(14), ly, fill=color, width=3, capstyle="round")
            c.create_text(lx + self.px(20), ly, text=label, anchor="w", fill=FG, font=self.f_legend)
            lx += item_w + self.px(10)

    # ------------------------------------------------------------- zapis nastaw
    def _write(self, key, value, label):
        if not self.client:
            messagebox.showwarning(APP_TITLE, "Najpierw połącz się ze sterownikiem.")
            return

        def work():
            try:
                self.client.set_register(key, value)
                self.after(0, lambda: self.status.set(f"Ustawiono {label}"))
                self.after(500, lambda: threading.Thread(target=self._fetch_once, daemon=True).start())
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(APP_TITLE, f"Nie udało się ustawić: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _fetch_once(self):
        try:
            data = self.client.read_all()
            self.after(0, self._apply_only, data)
        except Exception:
            pass

    def set_value(self, key, value, lo, hi):
        try:
            value = int(value)
        except (ValueError, tk.TclError):
            messagebox.showwarning(APP_TITLE, "Nieprawidłowa wartość.")
            return
        if not lo <= value <= hi:
            messagebox.showwarning(APP_TITLE, f"Wartość musi być w zakresie {lo}-{hi}.")
            return
        self._write(key, value, f"{key} = {value} °C")

    def set_mode(self):
        val = "1" if self.mode_var.get() == "Lato" else "0"
        self._write("zima_lato", val, f"tryb: {self.mode_var.get()}")


if __name__ == "__main__":
    try:                                    # ostry tekst na ekranach HiDPI (Windows)
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App().mainloop()