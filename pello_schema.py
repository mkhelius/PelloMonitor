"""
pello_schema.py - zakładka „Schemat instalacji”: rysunek hydrauliczny z odczytami na żywo.
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Schemat: komin i kocioł -> (pompa kotła na powrocie) -> rozdzielacz -> 3 obwody:
    1. woda użytkowa (bojler CWU),
    2. grzejniki            = obwód CO 2 sterownika Pello D (pompa out_pomp2, termostat pokojowy RF),
    3. ogrzewanie podłogowe = obwód CO 1 sterownika (pompa out_pomp1, zawór 4D, czujnik T1).
"Pompa kotła" nie ma osobnego wyjścia w sterowniku - pokazujemy ją jako włączoną, gdy pracuje
którakolwiek pompa (CO 1, CO 2 lub CWU).
Rysunek skaluje się do wielkości okna. Kolor rur pokazuje, czy obwód pracuje
(czerwone = zasilanie, niebieskie = powrót, szare = pompa wyłączona).

Chcesz zmienić, jakie odczyty pokazują się przy danym elemencie? Edytuj słownik READINGS poniżej
(klucze parametrów są takie same jak w zakładce „Odczyty”).
"""
import tkinter as tk

from pello_config import (ACCENT, BORDER, CARD, FG, FONT_FAMILY, GREEN, LABEL_FG, MUTED, RED,
                          format_value, tofloat, value_color, with_unit)

# ---------------------------------------------------------------- odczyty przy elementach
# "element": (tytuł karty, [(klucz parametru, opis), ...])
READINGS = {
    "komin": ("Komin", [
        ("tsp_value", "Temp. spalin"),
        ("out_dm", "Dmuchawa"),
        ("act_dm_speed", "Prędkość dmuchawy"),
        ("mpl_dm_rpm", "Obroty dmuchawy"),
    ]),
    "kociol": ("Kocioł", [
        ("tkot_value", "Temp. kotła"),
        ("kot_tzad", "Zadana kotła"),
        ("pl_status", "Status"),
        ("pl_power_kw", "Moc palnika"),
        ("pl_flame", "Płomień"),
        ("fuel_level", "Paliwo"),
    ]),
    "zewn": ("Czujnik zewnętrzny", [
        ("tzew_value", "Temp. zewnętrzna"),
        ("zima_lato", "Tryb pracy"),
    ]),
    "rozdz": ("Rozdzielacz", [
        ("tpow_value", "Powrót do kotła"),
        ("_pompa_kotla", "Pompa kotła"),
    ]),
    "cwu": ("Woda użytkowa (CWU)", [
        ("tcwu_value", "Temp. CWU"),
        ("cwu_tzad", "Zadana CWU"),
        ("out_cwu", "Pompa CWU"),
    ]),
    "grz": ("Grzejniki (CO 2)", [
        ("t2_value", "Temp. CO 2"),
        ("ob2_pok_tact", "Temp. pokoju"),
        ("ob2_pok_tzad", "Zadana pokoju"),
        ("out_pomp2", "Pompa CO 2"),
    ]),
    "podl": ("Podłogówka (CO 1)", [
        ("t1_value", "Temp. obiegu"),
        ("ob1_pok_tact", "Temp. pokoju"),
        ("out_zaw4d", "Zawór"),
        ("out_pomp1", "Pompa CO 1"),
    ]),
}

# pozycja karty na rysunku: (x, y, szerokość) we współrzędnych logicznych 1100 x 700
CARD_POS = {
    "komin": (105, 30, 275),
    "kociol": (20, 424, 250),
    "zewn": (20, 610, 250),
    "rozdz": (290, 418, 200),
    "cwu": (870, 60, 215),
    "grz": (860, 320, 225),
    "podl": (860, 505, 225),
}

W, H = 1100, 700          # rozmiar logiczny rysunku (skalowany do okna)
HEAD, ROW = 34, 22        # wysokość nagłówka karty i wiersza

PIPE_RED = "#dc2626"
PIPE_BLUE = "#2563eb"
PIPE_OFF = "#b6bcc6"
STEEL = "#4b5563"



class SchemaView:
    def __init__(self, parent, pady=10):
        self.c = tk.Canvas(parent, bg="#f8fafc", highlightthickness=1, highlightbackground=BORDER)
        self.c.pack(fill="both", expand=True, pady=pady)
        self.c.bind("<Configure>", lambda e: self.redraw())
        self.c.bind("<Map>", lambda e: self.redraw(force=True))
        self.data = None
        self.offline = False
        self.fuel_thr = 20
        self.s, self.ox, self.oy = 1.0, 0.0, 0.0

    # ------------------------------------------------------------- API
    def update(self, data, fuel_thr=20):
        if data is not None:
            data = dict(data)
            running = any(str(data.get(k)) == "1" for k in ("out_pomp1", "out_pomp2", "out_cwu"))
            data["_pompa_kotla"] = "1" if running else "0"
        self.data = data
        self.offline = False
        self.fuel_thr = fuel_thr
        self.redraw()

    def set_offline(self, offline=True):
        self.offline = offline
        self.redraw()

    # ------------------------------------------------------------- odczyt danych
    def _raw(self, key):
        return None if self.data is None else self.data.get(key)

    def _on(self, key):
        return str(self._raw(key)) == "1"

    def _val(self, key):
        raw = self._raw(key)
        if raw is None:
            return "—"
        return with_unit(key, format_value(key, raw))

    def _temp(self, key):
        raw = self._raw(key)
        return "—" if raw is None else format_value(key, raw) + "°C"

    # ------------------------------------------------------------- narzędzia rysowania
    def _x(self, v):
        return self.ox + v * self.s

    def _y(self, v):
        return self.oy + v * self.s

    def _flat(self, pts):
        out = []
        for x, y in pts:
            out += [self._x(x), self._y(y)]
        return out

    def _font(self, size, bold=False):
        return (FONT_FAMILY, -max(8, int(round(size * self.s))), "bold" if bold else "normal")

    def _kw(self, kw):
        kw["width"] = max(1, kw.get("width", 1) * self.s)
        return kw

    def _text(self, x, y, text, size=14, bold=False, fill=FG, anchor="w", angle=0):
        self.c.create_text(self._x(x), self._y(y), text=text, font=self._font(size, bold),
                           fill=fill, anchor=anchor, angle=angle)

    def _line(self, pts, color, width=6, arrow=False, dash=None):
        w = max(1, width * self.s)
        kw = dict(width=w, fill=color, joinstyle="round", capstyle="butt")
        if arrow:
            kw.update(arrow="last", arrowshape=(w * 2.2, w * 2.6, w * 1.2))
        if dash:
            kw["dash"] = dash
        self.c.create_line(*self._flat(pts), **kw)

    def _rect(self, x1, y1, x2, y2, **kw):
        self.c.create_rectangle(self._x(x1), self._y(y1), self._x(x2), self._y(y2), **self._kw(kw))

    def _oval(self, x1, y1, x2, y2, **kw):
        self.c.create_oval(self._x(x1), self._y(y1), self._x(x2), self._y(y2), **self._kw(kw))

    def _poly(self, pts, **kw):
        self.c.create_polygon(*self._flat(pts), **self._kw(kw))

    def _rrect(self, x1, y1, x2, y2, r=10, **kw):
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        pts = [(x1 + r, y1), (x2 - r, y1), (x2, y1), (x2, y1 + r), (x2, y2 - r), (x2, y2),
               (x2 - r, y2), (x1 + r, y2), (x1, y2), (x1, y2 - r), (x1, y1 + r), (x1, y1)]
        self.c.create_polygon(*self._flat(pts), smooth=True, **self._kw(kw))

    def _link(self, x1, y1, x2, y2):
        self._line([(x1, y1), (x2, y2)], "#9ca3af", 2, dash=(3, 3))

    # ------------------------------------------------------------- główne rysowanie
    def redraw(self, force=False):
        c = self.c
        if not force and not c.winfo_viewable():
            return
        w, h = c.winfo_width(), c.winfo_height()
        if w < 300 or h < 220:
            return
        c.delete("all")
        self.s = min(w / W, h / H)
        self.ox = (w - W * self.s) / 2
        self.oy = (h - H * self.s) / 2

        pco1, pco2, pcwu = self._on("out_pomp1"), self._on("out_pomp2"), self._on("out_cwu")
        main_on = pco1 or pco2 or pcwu
        valve = str(self._raw("out_zaw4d"))

        self._draw_title()
        self._draw_elements(pcwu, pco2, pco1)
        self._draw_pipes(pco1, pco2, pcwu)
        self._draw_chimney()
        self._draw_boiler()
        self._draw_valve(valve)
        self._pump(335, 365, main_on, "Pompa kotła", PIPE_BLUE, -1)   # na powrocie (niebieska rura)
        self._pump(625, 115, pcwu, "Pompa CWU", PIPE_RED, 1)
        self._draw_labels()
        for key in READINGS:
            self._card(key)
        self._link(80, 100, 105, 100)          # czujnik spalin -> karta komina
        self._draw_legend()
        self._draw_status_badge()

    # ------------------------------------------------------------- elementy instalacji
    def _draw_title(self):
        self._text(560, 22, "Schemat instalacji", 20, True, FG)
        self._text(560, 46, "odczyty na żywo ze sterownika", 13, False, MUTED)

    def _draw_elements(self, pcwu, pco2, pco1):
        # rozdzielacz
        self._rrect(500, 90, 550, 630, 14, fill="#374151", outline="#111827", width=2)
        self._text(525, 360, "ROZDZIELACZ", 16, True, "#e5e7eb", "center", angle=90)

        # bojler CWU
        self._rrect(700, 70, 790, 230, 16, fill="#dbeafe", outline="#93c5fd", width=2)
        self._text(745, 90, self._temp("tcwu_value"), 19, True, FG, "center")
        self._text(745, 216, "BOJLER", 12, True, MUTED, "center")

        # grzejnik
        self._rrect(720, 308, 840, 422, 10, fill="#fee2e2" if pco2 else "#f3f4f6",
                    outline="#9ca3af", width=2)
        for i in range(7):
            x = 736 + i * 16
            self._line([(x, 320), (x, 410)], "#d1d5db" if not pco2 else "#f87171", 6)

        # podłogówka
        self._rrect(690, 505, 845, 620, 12, fill="#fff7ed", outline="#fed7aa", width=2)

    def _draw_pipes(self, pco1, pco2, pcwu):
        main_on = pco1 or pco2 or pcwu
        red = lambda on: PIPE_RED if on else PIPE_OFF
        blue = lambda on: PIPE_BLUE if on else PIPE_OFF

        # kocioł <-> rozdzielacz
        self._line([(250, 285), (500, 285)], red(main_on), 6, arrow=True)
        self._line([(500, 365), (250, 365)], blue(main_on), 6, arrow=True)

        # 1. woda użytkowa
        self._line([(550, 115), (710, 115)], red(pcwu), 6, arrow=True)
        self._line([(710, 190), (550, 190)], blue(pcwu), 6, arrow=True)
        coil = [(710, 115), (780, 115), (780, 140), (720, 140), (720, 165), (780, 165), (780, 190), (710, 190)]
        self._line(coil, PIPE_RED if pcwu else PIPE_OFF, 4)
        self._line([(790, 95), (846, 95)], PIPE_RED, 5, arrow=True)       # ciepła woda
        self._line([(846, 205), (790, 205)], PIPE_BLUE, 5, arrow=True)    # zimna woda

        # 2. grzejniki
        self._line([(550, 330), (720, 330)], red(pco2), 6, arrow=True)
        self._line([(720, 400), (550, 400)], blue(pco2), 6, arrow=True)

        # 3. ogrzewanie podłogowe (zawór 3-drożny w punkcie 620,520)
        self._line([(550, 520), (602, 520)], red(pco1), 6, arrow=True)
        self._line([(638, 520), (700, 520)], red(pco1), 6, arrow=True)
        self._line([(700, 605), (550, 605)], blue(pco1), 6, arrow=True)
        self._line([(620, 605), (620, 556)], blue(pco1), 3, arrow=True, dash=(6, 4))   # mieszanie z powrotu
        floor = [(700, 520), (830, 520), (830, 538), (710, 538), (710, 556), (830, 556), (830, 574),
                 (710, 574), (710, 590), (830, 590), (830, 605), (700, 605)]
        self._line(floor, "#f97316" if pco1 else PIPE_OFF, 4)

    def _draw_valve(self, valve):
        col = {"0": "#9ca3af", "1": GREEN, "2": "#f59e0b"}.get(valve, "#d1d5db")
        for tri in ([(602, 506), (602, 534), (620, 520)],
                    [(638, 506), (638, 534), (620, 520)],
                    [(606, 556), (634, 556), (620, 520)]):
            self._poly(tri, fill=col, outline="#111827", width=1.5)

    def _pump(self, x, y, on, label, color=PIPE_RED, direction=1):
        """Pompa obiegowa; trójkąt wskazuje kierunek przepływu (1 = w prawo, -1 = w lewo)."""
        r = 19
        self._oval(x - r, y - r, x + r, y + r, fill="#ffffff", outline=color if on else PIPE_OFF, width=3)
        d = direction
        self._poly([(x - 8 * d, y - 10), (x - 8 * d, y + 10), (x + 12 * d, y)],
                   fill=GREEN if on else "#d1d5db", outline="")
        self._text(x, y + r + 12, label, 12, True, LABEL_FG if on else MUTED, "center")

    def _draw_chimney(self):
        hot = (tofloat(self._raw("tsp_value")) or 0) > 60
        self._rect(50, 60, 80, 240, fill="#9ca3af", outline="#6b7280", width=2)
        for y in range(80, 240, 20):
            self._line([(50, y), (80, y)], "#b6bcc6", 1)
        self._poly([(42, 48), (88, 48), (84, 60), (46, 60)], fill="#6b7280", outline="")
        if hot:
            for cx, cy, r in ((66, 36, 6), (74, 24, 8), (64, 10, 10)):
                self._oval(cx - r, cy - r, cx + r, cy + r, fill="#d1d5db", outline="")
        self._oval(59, 94, 71, 106, fill="#ffffff", outline=RED, width=2)      # czujnik spalin
        self._text(66, 226, "KOMIN", 11, True, "#374151", "center", angle=0)

    def _draw_boiler(self):
        working = str(self._raw("pl_status")) in ("1", "2") or (tofloat(self._raw("pl_flame")) or 0) > 0
        self._rect(50, 405, 80, 414, fill="#1f2937", outline="")
        self._rect(200, 405, 230, 414, fill="#1f2937", outline="")
        self._rrect(30, 240, 250, 405, 14, fill=STEEL, outline="#1f2937", width=2)
        self._text(46, 262, "KOCIOŁ", 14, True, "#e5e7eb")
        self._text(236, 262, self._temp("tkot_value"), 20, True, "#ffffff", "e")
        self._rrect(44, 282, 236, 395, 10, fill="#1f2937", outline="#111827")
        k = 1.6
        outer = [(32, 10), (46, 32), (44, 48), (32, 54), (20, 48), (18, 32), (26, 26)]
        inner = [(32, 30), (39, 42), (32, 50), (25, 42)]
        f = lambda pts: [(140 + (x - 32) * k, 340 + (y - 32) * k) for x, y in pts]
        self._poly(f(outer), fill="#f97316" if working else "#6b7280", outline="")
        self._poly(f(inner), fill="#fde68a" if working else "#9ca3af", outline="")

    def _draw_labels(self):
        # numer i nazwa obwodu - pod elementem (wyrównane do jego lewej krawędzi)
        for left, cy, num, name in ((700, 250, "1", "Woda użytkowa"),        # pod bojlerem
                                    (720, 440, "2", "Grzejniki"),            # pod grzejnikiem
                                    (690, 640, "3", "Ogrzewanie podłogowe")):  # pod podłogówką
            cx = left + 13
            self._oval(cx - 13, cy - 13, cx + 13, cy + 13, fill=ACCENT, outline="")
            self._text(cx, cy, num, 15, True, "#ffffff", "center")
            self._text(cx + 19, cy, name, 14, True, LABEL_FG)
        self._text(620, 498, "Zawór 3-drożny", 12, True, LABEL_FG, "center")
        self._text(796, 80, "ciepła woda", 11, False, PIPE_RED)
        self._text(796, 221, "zimna woda", 11, False, PIPE_BLUE)

    # ------------------------------------------------------------- karty z odczytami
    def _card(self, key):
        title, rows = READINGS[key]
        x, y, w = CARD_POS[key]
        h = HEAD + len(rows) * ROW + 8
        self._rrect(x, y, x + w, y + h, 10, fill=CARD, outline=BORDER)
        self._rect(x, y + 8, x + 4, y + HEAD - 8, fill=ACCENT, outline="")
        self._text(x + 14, y + HEAD / 2, title, 15, True, FG)
        self._line([(x + 10, y + HEAD), (x + w - 10, y + HEAD)], BORDER, 1)
        for i, (k, label) in enumerate(rows):
            yy = y + HEAD + ROW * (i + 0.5) + 3
            self._text(x + 14, yy, label, 14, False, LABEL_FG)
            raw = self._raw(k)
            colr = FG if raw is None else value_color(k, raw, self.fuel_thr)
            self._text(x + w - 14, yy, self._val(k), 14, True, colr, "e")

    def _draw_legend(self):
        x = 560
        for color, text, width in ((PIPE_RED, "zasilanie", 100), (PIPE_BLUE, "powrót", 90),
                                   (PIPE_OFF, "obwód nieaktywny", 170)):
            self._line([(x, 675), (x + 34, 675)], color, 6)
            self._text(x + 44, 675, text, 13, False, MUTED)
            x += width + 40

    def _draw_status_badge(self):
        if self.offline:
            text, bg = "Brak połączenia – dane nieaktualne", "#fee2e2"
        elif self.data is None:
            text, bg = "Połącz się, aby zobaczyć dane", "#e5e7eb"
        else:
            return
        self._rrect(770, 12, 1085, 42, 10, fill=bg, outline="")
        self._text(927, 27, text, 13, True, RED if self.offline else LABEL_FG, "center")
