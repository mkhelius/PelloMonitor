"""
pello_locks.py - parametry zablokowane NA STAŁE przed zapisem z programu (logika, bez okna).
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Tych parametrów nie da się odblokować w Ustawieniach. Zapis blokuje też PelloClient.set_register,
więc nie obejdzie go ani zakładka „Parametry”, ani przycisk „Cofnij”, ani żaden przyszły kod.

Kategorie:
  network    - adres IP, maska, brama, DHCP, interfejs, serwer zdalny (zmiana odcięłaby program),
  time       - zegar i data sterownika, strefa czasowa, RTC,
  identity   - nazwa, numer, typ i wersje urządzenia, MAC,
  service    - protokół i tryb serwisowy, kody typu instalacji i kotła, aktualizacje, parowanie RF,
  combustion - spalanie: palnik, dmuchawa, podajnik, dawki paliwa, rozpalanie, wygaszanie
               (wyjątek: add_fuel - ilość ostatnio dosypanego paliwa, niskie ryzyko),
  sensor     - korekty czujników kotła, powrotu, spalin i podajnika (tylko z wyświetlacza palnika),
  unknown    - parametry bez opisu w katalogu (nie wiadomo, co zmieniają).
"""
import re

from pello_params import info

# kod -> (nazwa w kolumnie, powód pokazywany w podpowiedzi i w oknie)
CATEGORIES = {
    "network": ("sieć",
                "Zmiana adresu IP, maski, bramy lub DHCP odcięłaby program od sterownika, a przycisk „Cofnij” "
                "przestałby działać. Zmień to z panelu sterownika."),
    "time": ("czas", "Zegar, datę i strefę czasową sterownika ustawia się z jego panelu."),
    "identity": ("tożsamość", "Tożsamość urządzenia (nazwa, numer, typ, wersje, adres MAC) nie podlega zmianie "
                              "z programu."),
    "service": ("serwis", "Parametr serwisowy (protokół serwisowy, kody typu instalacji i kotła, aktualizacje, "
                          "parowanie RF) zmienia się tylko z panelu sterownika."),
    "combustion": ("spalanie", "Parametr spalania (palnik, dmuchawa, podajnik, dawki paliwa, rozpalanie, "
                               "wygaszanie). Zła wartość może uszkodzić kocioł albo spowodować niebezpieczną "
                               "pracę. Zmieniaj go z wyświetlacza palnika."),
    "sensor": ("czujnik", "Korekty czujników kotła, powrotu, spalin i podajnika zmienia się tylko z wyświetlacza "
                          "palnika."),
    "unknown": ("bez opisu", "Parametr bez opisu – nie wiadomo, co zmienia, więc program go nie zmienia."),
}

ADD_FUEL_KEYS = {"add_fuel"}                       # wyjątek od blokady spalania (niskie ryzyko)

_IDENTITY_RE = re.compile(r"^(device_\w+|prod_date|eth_mac|burner)$")
_NETWORK_RE = re.compile(r"^(eth_|remote_)")
_TIME_RE = re.compile(r"^(datetime|daytime|date|time|node_time|localtimezone|rtc_\w+|ntp(_\w+)?|tz(_\w+)?|"
                      r"timezone|time_zone|dst(_\w+)?)$")
_SERVICE_RE = re.compile(r"^(en_serv|prot_serv|install_type|typ_kotla|accesslevel|node_add|node_del|rf_update|"
                         r"upd_\w+)$|(^|_)(serv|serwis|service|factory|reset|pass|pwd|pin|boot|fw)(_|$)")
_SENSOR_KEYS = {"tkot_cal", "tpow_cal", "tsp_cal", "tpod_cal"}
_COMBUSTION_GROUPS = {"Palnik i paliwo", "Moduł palnika i dmuchawa", "Podajnik", "Palnik (bez opisu)",
                      "Moduł palnika (bez opisu)"}
_COMBUSTION_KEYS = {"limit_power"}                 # ograniczenie mocy kotła
_COMBUSTION_RE = re.compile(r"(^|_)(pl|mpl|dm|exh|pod|fuel|rozp|wyg|zaplon)(_|$)")


def lock_category(key):
    """Kod kategorii trwałej blokady albo "" (parametr nie jest zablokowany na stałe)."""
    key = str(key)
    if _IDENTITY_RE.match(key):
        return "identity"
    if _NETWORK_RE.match(key):
        return "network"
    if _TIME_RE.match(key):
        return "time"
    if _SERVICE_RE.search(key):
        return "service"
    if key in _SENSOR_KEYS:
        return "sensor"
    if key in ADD_FUEL_KEYS:
        return ""
    desc, _unit, _kind, group = info(key)
    if group in _COMBUSTION_GROUPS or key in _COMBUSTION_KEYS or _COMBUSTION_RE.search(key):
        return "combustion"
    if not desc:
        return "unknown"
    return ""


def lock_reason(key):
    """Pełny tekst „Zablokowane na stałe: …” albo "" gdy parametr nie jest zablokowany na stałe."""
    cat = lock_category(key)
    return f"Zablokowane na stałe. {CATEGORIES[cat][1]}" if cat else ""
