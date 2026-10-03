"""
pello_edit.py - zasady edycji pojedynczych parametrów (logika, bez okna).
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Tu rozstrzygamy:
  * które parametry w ogóle wolno edytować (zablokowane na stałe - patrz pello_locks.py: sieć, czas,
    tożsamość, serwis, spalanie, korekty czujników kotła/powrotu/spalin/podajnika, parametry bez opisu;
    tylko do odczytu są też odczyty na żywo, harmonogramy i parametry urządzeń RF / stref),
  * jaki poziom ryzyka ma dany parametr (zielony / żółty / czerwony),
  * czy wpisana wartość jest poprawna (liczba, wybór z listy, rozsądny zakres temperatur).

Poziomy ryzyka:
  "green"  - nastawy temperatur (zadane, maksymalne, korekty krzywej pogodowej ...),
  "yellow" - histerezy, czasy, opóźnienia, korekty czujników, regulatory i pozostałe nastawy,
  "red"    - czyszczenie i pozostałe parametry urządzenia (tryb cichy, ekran, moduły, głowice ...);
             wymaga dodatkowego, drugiego potwierdzenia.
Spalanie, sieć i serwis nie mają poziomu ryzyka - są zablokowane. Wyjątek: add_fuel (ilość ostatnio
dosypanego paliwa) - zielony.
"""
import functools
import math
import re

from pello_backup import is_secret, kind_of
from pello_client import values_equal
from pello_config import tofloat
from pello_locks import ADD_FUEL_KEYS, lock_category, lock_reason
from pello_params import ENUMS, info

GREEN, YELLOW, RED = "green", "yellow", "red"

# (nazwa, krótki opis, kolor tekstu czytelny na białym tle)
RISK_INFO = {
    GREEN: ("niskie", "nastawa temperatury", "#15803d"),
    YELLOW: ("średnie", "histereza, czas lub inna nastawa regulacji", "#b45309"),
    RED: ("wysokie", "spalanie, paliwo, sieć lub serwis – błędna wartość może rozregulować piec "
                     "albo go zatrzymać", "#dc2626"),
}

LOCK_TEXT = "🔒 zablokowane"
TEMP_MIN, TEMP_MAX = -50.0, 150.0       # poza tym zakresem temperatura nie ma sensu fizycznego

RED_GROUPS = {"Czyszczenie", "Czyszczenie (bez opisu)", "Urządzenie i sieć"}
_RED_RE = re.compile(r"(^|_)(clean|clwym|clsln|rf|calib|wifi|net|dns|mqtt)(_|$)")
_YELLOW_RE = re.compile(r"(^|_)(hist\w*|time|delay|czas|pre|cal|opozn\w*|p|i|d)(_|$)")
_AUX_RE = re.compile(r"^(rf\d+_|strefa\d+_)")
_NUMBER_RE = re.compile(r"-?\d+(\.\d+)?")      # liczba: tylko cyfry, opcjonalny minus i KROPKA dziesiętna


def why_not_editable(key):
    """Zwraca powód, dla którego parametru nie wolno edytować, albo "" gdy wolno."""
    if not re.fullmatch(r"\w+", str(key)):
        return "Niedozwolona nazwa parametru."
    if is_secret(key):
        return "Dane dostępowe i wartości pochodne nie podlegają edycji."
    kind = kind_of(key)
    if kind == "live":                              # odczyt: to nie nastawa, więc bez „kłódki”
        return "To odczyt na żywo (stan, temperatura, licznik) – sterownik sam go wylicza."
    locked = lock_reason(key)                      # blokada na stałe: ważniejsza niż wszystko poniżej
    if locked:
        return locked
    if _AUX_RE.match(key):
        return ("To parametr urządzenia pomocniczego (termostat RF / strefa). Program zapisuje "
                "nastawy tylko do sterownika głównego.")
    if kind == "ident":
        return "To dane identyfikacyjne urządzenia (wersje, numer fabryczny) – nie podlegają edycji."
    if info(key)[2] in ("text", "unix"):
        return "Harmonogramy, teksty i daty nie są edytowane z tego okna."
    return ""


@functools.lru_cache(maxsize=4096)
def risk_of(key):
    """Poziom ryzyka edytowalnego parametru: "green" / "yellow" / "red"; None = tylko do odczytu."""
    if why_not_editable(key):
        return None
    if key in ADD_FUEL_KEYS:                        # jedyny edytowalny parametr z grupy „Palnik i paliwo”
        return GREEN
    desc, unit, kind, group = info(key)
    if group in RED_GROUPS or _RED_RE.search(key):
        return RED
    if _YELLOW_RE.search(key) or unit in ("s", "min", "h", "ms") or kind == "dur":
        return YELLOW
    if unit == "°C":
        return GREEN
    return YELLOW


def risk_text(key):
    """Tekst do kolumny „Ryzyko”: poziom ryzyka, „🔒 zablokowane” (blokada na stałe) albo — (tylko odczyt)."""
    r = risk_of(key)
    if r:
        return RISK_INFO[r][0]
    return LOCK_TEXT if lock_category(key) and kind_of(key) != "live" else "—"


def choices(key):
    """Lista (wartość_surowa, etykieta) dla parametrów wyboru; None dla liczb i tekstu."""
    if key in ENUMS:
        return list(ENUMS[key].items())
    kind = info(key)[2]
    if kind == "onoff":
        return [("0", "Wył."), ("1", "Wł.")]
    if kind == "yesno":
        return [("0", "Nie"), ("1", "Tak")]
    return None


def same(a, b):
    """Czy dwie wartości są takie same (liczby z tolerancją, tekst bez spacji brzegowych)."""
    return values_equal(a, b)


def _norm(f):
    if f == int(f):
        return str(int(f))
    return f"{f:.6f}".rstrip("0").rstrip(".")


def parse_new(key, current, text):
    """Sprawdza wpisaną wartość. Zwraca (wartość_do_wysłania, "") albo (None, komunikat błędu)."""
    text = str(text).strip()
    ch = choices(key)
    if ch is not None:
        if text not in {raw for raw, _ in ch}:
            return None, "Wybierz jedną z dostępnych wartości."
        return text, ""
    if text == "":
        return None, "Wpisz wartość."
    cur = "" if current is None else str(current).strip()
    kind, unit = info(key)[2], info(key)[1]
    if tofloat(cur) is not None or (cur == "" and kind in ("num", "dur")):
        if "," in text:
            return None, "Separator dziesiętny to kropka (np. 45.5), nie przecinek."
        if not _NUMBER_RE.fullmatch(text):
            return None, "Wpisz liczbę z kropką dziesiętną (np. 45 albo 45.5)."
        f = float(text)
        if not math.isfinite(f):
            return None, "Wpisz liczbę z kropką dziesiętną (np. 45 albo 45.5)."
        if unit == "°C" and not TEMP_MIN <= f <= TEMP_MAX:
            return None, f"Temperatura poza rozsądnym zakresem ({TEMP_MIN:.0f} … {TEMP_MAX:.0f} °C)."
        return _norm(f), ""
    if len(text) > 200 or any(ord(c) < 32 for c in text):
        return None, "Wartość jest za długa albo zawiera znaki sterujące."
    return text, ""
