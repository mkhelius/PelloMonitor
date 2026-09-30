"""
pello_config.py - stałe, teksty, kolory i drobne funkcje pomocnicze.
Pello 3.5 Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>
"""
import datetime
import tkinter as tk
from pathlib import Path

# ---------------------------------------------------------------- informacje o programie
APP_TITLE = "Pello 3.5 Monitor"
APP_VERSION = "2.4"
APP_EDITION = "FREE"
AUTHOR = "Mariusz"
AUTHOR_EMAIL = "mk.helius@gmail.com"
COPYRIGHT = f"© 2026 {AUTHOR}"

LICENSE_TEXT = [
    "Pello 3.5 Monitor w wersji FREE jest programem darmowym. Możesz go bezpłatnie używać do celów "
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
    "odczyt wszystkich parametrów pieca i zmiana nastaw (CWU, kocioł, Zima/Lato)",
    "schemat instalacji: kocioł, komin, rozdzielacz i 3 obwody z odczytami na żywo",
    "wykres temperatur w czasie (1 h / 6 h / 24 h)",
    "dane modułów: czujnik pokojowy BT4 (temperatura, wilgotność, bateria)",
    "ciśnienie spalin, serwis wymiennika, zużycie paliwa i energia",
    "historia pracy zapisywana do plików CSV (otwiera się w Excelu)",
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
GROUPS = {
    "Temperatury i moc": [
        ("tzew_value", "Temperatura zewnętrzna", "°C"),
        ("tkot_value", "Temperatura kotła", "°C"),
        ("tcwu_value", "Temperatura CO 2", "°C"),
        ("twew_value", "Temperatura CO 1", "°C"),
        ("tpow_value", "Temperatura powrotu", "°C"),
        ("tsp_value", "Temperatura spalin", "°C"),
        ("kot_tzad", "Zadana temp. kotła", "°C"),
        ("cwu_tzad", "Zadana temp. CWU", "°C"),
        ("pl_power_kw", "Moc palnika", "kW"),
    ],
    "Paliwo": [
        ("fuel_level", "Poziom paliwa", "%"),
        ("time_to_empty", "Czas do braku paliwa", "h"),
        ("pl_fuel_flow", "Spalanie paliwa", "kg/h"),
        ("next_fuel_time", "Data następnego zasypu", ""),
    ],
    "Stan urządzeń": [
        ("tryb_auto_state", "Tryb pieca", ""),
        ("pl_status", "Status kotła", ""),
        ("out_pomp1", "Pompa CO", ""),
        ("out_cwu", "Pompa CWU", ""),
        ("out_dm", "Stan dmuchawy", ""),
        ("act_dm_speed", "Prędkość dmuchawy", "%"),
        ("out_zaw4d", "Stan zaworu 4D", ""),
        ("ob1_zaw4d_pos", "Pozycja zaworu 4D", "%"),
        ("pl_flame", "Wartość płomienia", "%"),
        ("zima_lato", "Tryb Zima / Lato", ""),
    ],
    "Podajnik i kalibracja": [
        ("pod_run_time_str", "Czas pracy podajnika", ""),
        ("pl_calib_time", "Czas kalibracji", "s"),
        ("pl_calib_perf", "Wartość kalibracji", "g"),
    ],
    "Czujnik pokojowy BT4": [
        ("bt4_temp", "Temp. pokojowa (BT4)", "°C"),
        ("bt4_rh", "Wilgotność (BT4)", "%"),
        ("bt4_bat", "Bateria (BT4)", "%"),
        ("bt4_sig", "Sygnał (BT4)", "%"),
        ("ob1_pok_tact", "Pokój ob1 – aktualna", "°C"),
        ("ob1_pok_tzad", "Pokój ob1 – zadana", "°C"),
        ("ob2_pok_tact", "Pokój ob2 – aktualna", "°C"),
        ("ob2_pok_tzad", "Pokój ob2 – zadana", "°C"),
    ],
    "Ciśnienie i wentylator": [
        ("dp_value", "Ciśnienie spalin (Δp)", "mbar"),
        ("dp_alarm", "Alarm ciśnienia spalin", ""),
        ("exh_fan_speed", "Wentylator spalin", "%"),
        ("exh_en", "Wentylator spalin – aktywny", ""),
    ],
    "Serwis wymiennika": [
        ("clean_burn_time", "Czas pracy palnika", "s"),
        ("clean_act_kg", "Zużycie od serwisu", "kg"),
        ("clean_exch_kg", "Limit serwisu wymiennika", "kg"),
        ("alarm_clean_exch", "Alarm serwisu wymiennika", ""),
    ],
    "Moduł CQ i energia": [
        ("mod2_flow", "Przepływ (moduł CQ)", ""),
        ("mod2_power", "Moc modułu", "kW"),
        ("mod2_energy", "Energia modułu", "kWh"),
        ("wh_global", "Energia – łącznie", "kWh"),
        ("wh_yr", "Energia – rok", "kWh"),
        ("wh_mon", "Energia – miesiąc", "kWh"),
    ],
    "Info o sterowniku": [
        ("device_name", "Nazwa urządzenia", ""),
        ("device_soft_version", "Wersja oprogramowania", ""),
        ("eth_ip", "Adres IP sterownika", ""),
        ("typ_kotla", "Typ kotła", ""),
        ("fuel_level_enum", "Poziom paliwa (skala)", ""),
    ],
    "Alarmy": [
        ("alarm_rozp", "Alarm rozpalanie", ""),
        ("alarm_rozp_ext", "Alarm rozpalanie (ext)", ""),
        ("alarm_pod_zaplon", "Alarm podajnik zapłon", ""),
        ("alarm_tkot", "Alarm temp. kotła", ""),
        ("alarm_tkot_90", "Alarm temp. kotła >90°C", ""),
        ("alarm_tpow", "Alarm temp. powrotu", ""),
        ("alarm_tpod", "Alarm temp. podajnika", ""),
        ("alarm_tpod_hi", "Alarm wysoka temp. podajnika", ""),
        ("alarm_tcwu", "Alarm temp. CWU", ""),
        ("alarm_twew", "Alarm temp. CO", ""),
        ("alarm_tzew", "Alarm czujnika zewn.", ""),
        ("alarm_tsp", "Alarm temp. spalin", ""),
        ("alarm_tco1_hi", "Alarm wysoka temp. CO 1", ""),
        ("alarm_termik", "Alarm STB (Termik)", ""),
        ("alarm_stb", "Alarm STB", ""),
        ("alarm_zasobnik", "Alarm zasobnika", ""),
        ("alarm_otw_zasob", "Alarm otwarcie zasobnika", ""),
        ("alarm_ipconflict", "Alarm konflikt IP", ""),
        ("alarm_cis", "Alarm ciśnienia spalin", ""),
        ("alarm_tank_hi", "Zbiornik – poziom wysoki", ""),
        ("alarm_tank_lo", "Zbiornik – poziom niski", ""),
        ("alarm_tank_hitemp", "Zbiornik – przegrzanie", ""),
        ("alarm_clean_exch", "Serwis wymiennika", ""),
        ("alarm_clwym", "Czyszczenie wymuszone", ""),
        ("alarm_poz_ruszt", "Alarm pozycji rusztu", ""),
        ("dp_alarm", "Czujnik ciśnienia Δp", ""),
        ("mpl_alarm", "Alarm mieszacza MPL", ""),
    ],
}
ALL_KEYS = [k for g in GROUPS.values() for k, _, _ in g]

# Serie na wykresie: (klucz, nazwa, kolor, domyślnie włączona)
CHART_SERIES = [
    ("tkot_value", "Kocioł", "#e4572e", True),
    ("tcwu_value", "CO 2", "#2e86ab", True),
    ("tpow_value", "Powrót", "#8e44ad", True),
    ("tzew_value", "Zewnętrzna", "#7f8c8d", True),
    ("twew_value", "CO 1", "#27ae60", False),
    ("tsp_value", "Spaliny", "#f39c12", False),
]
RANGES = {"1 godzina": 1, "6 godzin": 6, "24 godziny": 24}

MAPS = {
    "pl_status": {"0": "Stop", "1": "Rozpalanie", "2": "Praca", "3": "Wygaszanie", "4": "Czyszczenie"},
    "tryb_auto_state": {"0": "Ręczny", "1": "Automatyczny", "2": "Alarmowy"},
    "out_zaw4d": {"0": "Wyłączony", "1": "Otwierany", "2": "Zamykany"},
    "zima_lato": {"0": "Zima", "1": "Lato"},
    "exh_en": {"0": "Nie", "1": "Tak"},
    "typ_kotla": {"5": "Pello 3.5", "0": "Inny"},
}
ON_OFF = {"0": "Wył.", "1": "Wł."}
for _k in ("out_pomp1", "out_cwu", "out_dm"):
    MAPS[_k] = ON_OFF

# Alarmy spoza prefiksu "alarm_" (działają tak samo w kolorach i powiadomieniach)
EXTRA_ALARM_KEYS = {"dp_alarm", "mpl_alarm"}

# ---------------------------------------------------------------- pomocnicze
def is_alarm_key(key):
    return key.startswith("alarm_") or key in EXTRA_ALARM_KEYS


def tofloat(v):
    """Bezpieczna konwersja: puste pole sterownika -> None (wykres się nie sypie)."""
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
    if val is None:
        return "—"
    val = str(val)
    if key in MAPS:
        return MAPS[key].get(val, f"Nieznany ({val})")
    if is_alarm_key(key):
        return ON_OFF.get(val, f"Nieznany ({val})")
    if key == "next_fuel_time":
        try:
            dt = datetime.datetime.fromtimestamp(float(val), tz=datetime.timezone.utc).astimezone()
            return dt.strftime("%d-%m-%Y %H:%M")
        except (ValueError, TypeError, OSError):
            return "—"
    try:
        f = float(val)
        return str(int(f)) if f == int(f) else f"{f:.1f}"
    except ValueError:
        return val


def value_color(key, raw, fuel_thr=None):
    """Kolor wartości zależny od stanu (alarm = czerwony, praca = zielony)."""
    raw = str(raw)
    if is_alarm_key(key):
        return RED if raw == "1" else GREEN
    if key in ("out_pomp1", "out_cwu", "out_dm"):
        return GREEN if raw == "1" else MUTED
    if key == "pl_status":
        return GREEN if raw == "2" else FG
    if key == "tryb_auto_state":
        return RED if raw == "2" else FG
    if key == "fuel_level" and fuel_thr is not None:
        v = tofloat(raw)
        if v is not None and v <= fuel_thr:
            return RED
    return FG