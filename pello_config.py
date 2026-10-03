"""
pello_config.py - stałe, teksty, kolory i drobne funkcje pomocnicze.
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>
"""
import datetime
import tkinter as tk
from pathlib import Path

from pello_params import (ALARM_GROUPS, ALARM_KEYS, CSV_KEYS, ENUMS as MAPS, GROUPS, READING_GROUPS,
                          describe, format_param,
                          group_of, has_description, info, is_alarm, unit_of, with_unit)

# ---------------------------------------------------------------- informacje o programie
APP_TITLE = "Pello Monitor"
APP_VERSION = "3.4"
APP_EDITION = "FREE"
AUTHOR = "Mariusz"
AUTHOR_EMAIL = "mk.helius@gmail.com"
COPYRIGHT = f"© 2026 {AUTHOR}"

LICENSE_TEXT = [
    "Pello Monitor w wersji FREE jest programem darmowym. Możesz go bezpłatnie używać do celów "
    "prywatnych i niekomercyjnych oraz kopiować i przekazywać dalej w niezmienionej postaci.",

    "Zabronione jest sprzedawanie programu, pobieranie za niego jakichkolwiek opłat, usuwanie informacji "
    "o autorze oraz podawanie się za autora programu.",

    "Program jest udostępniany w stanie „tak jak jest” (AS IS), bez jakiejkolwiek gwarancji. Autor nie "
    "ponosi odpowiedzialności za szkody wynikające z jego użytkowania, w tym za nieprawidłowe nastawy lub "
    "działanie pieca, utratę danych czy przerwy w ogrzewaniu. Nastawy sterownika zmieniasz na własną "
    "odpowiedzialność.",

    "Program nie jest oficjalnym produktem producenta sterownika (esterownik.pl) i nie jest z nim powiązany. "
    "Wszystkie nazwy i znaki towarowe należą do ich właścicieli.",
]

FEATURES = [
    "odczyt wszystkich parametrów sterownika Pello (3.5 / D) i zmiana nastaw (CWU, kocioł, Zima/Lato)",
    "zakładka „Parametry”: wszystkie ponad 800 wartości ze sterownika, z wyszukiwarką i własnymi opisami",
    "schemat instalacji: kocioł, komin, rozdzielacz i 3 obwody z odczytami na żywo",
    "wykres temperatur w czasie (1 h / 6 h / 24 h)",
    "historia pracy zapisywana do plików CSV (otwiera się w Excelu)",
    "zapis nastaw potwierdzany odczytem ze sterownika, hasło przechowywane w zaszyfrowanej postaci",
    "kopie zapasowe ustawień: pierwotna automatycznie, ręczne i porównywanie zmian",
    "edycja pojedynczych parametrów (domyślnie wyłączona): kolory ryzyka, kopia przed zmianą, "
    "dziennik zmian z przyciskiem „Cofnij”; sieć, czas, tożsamość, serwis i spalanie zablokowane na stałe",
    "jednolite okienka w całym programie",
    "zakładka „Alarmy” z podsumowaniem aktywnych alarmów",
    "powiadomienia Windows: alarmy, niski poziom paliwa, brak połączenia",
    "praca w tle z ikoną w zasobniku systemowym",
]

# ---------------------------------------------------------------- ścieżki i komunikacja
CONFIG_FILE = Path.home() / ".pello_monitor.json"
CSV_DIR = Path.home() / "PelloMonitor"
TIMEOUT = 10
TIME_FMT = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------- wygląd
FONT_FAMILY = "Segoe UI"
BASE_PT = 9                      # bazowy rozmiar czcionki
LABEL_PT = BASE_PT + 3           # opisy parametrów: +3 pkt
VALUE_PT = BASE_PT + 2           # wartości: +2 pkt (pogrubione)
FONT_LABEL = (FONT_FAMILY, LABEL_PT)
FONT_VALUE = (FONT_FAMILY, VALUE_PT, "bold")
FONT_SECTION = (FONT_FAMILY, LABEL_PT + 1, "bold")   # nagłówki sekcji (pogrubione)

BG = "#eef1f5"
CARD = "#ffffff"
BORDER = "#dfe3e8"
ROWSEP = "#f1f3f5"
FG = "#111827"
LABEL_FG = "#374151"
MUTED = "#6b7280"
ACCENT = "#f97316"
ACCENT_DK = "#ea580c"
DARK = "#111827"
GREEN = "#16a34a"
RED = "#dc2626"

# (klucz, nazwa, jednostka)
# Serie na wykresie: (klucz, nazwa, kolor, domyślnie włączona)
CHART_SERIES = [
    ("tkot_value", "Kocioł", "#e4572e", True),
    ("tcwu_value", "CWU", "#2e86ab", True),
    ("tpow_value", "Powrót", "#8e44ad", True),
    ("tzew_value", "Zewnętrzna", "#7f8c8d", True),
    ("t1_value", "Obieg CO 1", "#16a085", False),
    ("twew_value", "Pokój CO 1", "#27ae60", False),
    ("ob2_pok_tact", "Pokój CO 2", "#c0392b", False),
    ("tsp_value", "Spaliny", "#f39c12", False),
]
RANGES = {"1 godzina": 1, "6 godzin": 6, "24 godziny": 24}

# ---------------------------------------------------------------- pomocnicze
def tofloat(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def safe_int(var, default):
    try:
        return int(var.get())
    except (tk.TclError, ValueError):
        return default


def format_value(key, val):
    """Czytelny tekst wartości parametru (bez jednostki) - patrz pello_params.format_param."""
    return format_param(key, val)


def value_color(key, raw, fuel_thr=None):
    """Kolor wartości zależny od stanu (alarm = czerwony, praca = zielony)."""
    raw = str(raw)
    kind = info(key)[2]
    if kind == "onoff":
        if is_alarm(key):
            return RED if raw == "1" else GREEN
        if key.startswith("out_") or key.startswith("_pompa") or key == "cwu_out_state":
            return GREEN if raw == "1" else MUTED
        return FG
    if key == "pl_status":
        return GREEN if raw == "2" else FG
    if key == "tryb_auto_state":
        return RED if raw == "2" else FG
    if key == "fuel_level" and fuel_thr is not None:
        v = tofloat(raw)
        if v is not None and v <= fuel_thr:
            return RED
    return FG
