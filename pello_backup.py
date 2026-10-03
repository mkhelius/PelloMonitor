"""
pello_backup.py - kopie zapasowe ustawień sterownika (logika, bez okna).
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Kopia to plik JSON z WSZYSTKIMI parametrami odczytanymi ze sterownika (bez danych logowania
auth_* i bez numeru seryjnego). Etap 1 niczego nie zapisuje do sterownika - tylko czyta.

Rodzaje kopii:
  "original" - "pierwotna": powstaje automatycznie przy pierwszym połączeniu z danym
               sterownikiem i NIGDY nie jest nadpisywana ani usuwana przez program,
  "manual"   - zwykła kopia robiona przyciskiem,
  "auto"     - kopia robiona automatycznie tuż przed zmianą pojedynczego parametru (zakładka „Parametry”).

Przy porównywaniu parametry dzielą się na:
  "setting" - ustawienia (nastawy, histerezy, harmonogramy ...),
  "ident"   - identyfikacja urządzenia (wersje, numer fabryczny...) - też warto widzieć zmiany,
  "live"    - odczyty na żywo, stany, liczniki i czas - domyślnie ukryte w porównaniu,
              bo zmieniają się ciągle i zasłaniałyby prawdziwe zmiany ustawień.
Podział dotyczy tylko wyświetlania różnic; w pliku kopii zawsze jest komplet parametrów.
"""
import datetime
import json
import os
import re
from pathlib import Path

from pello_params import GROUP_ORDER, SENSITIVE_PREFIXES, group_of

BACKUP_DIR = Path.home() / "PelloMonitor" / "kopie"
FORMAT_VERSION = 1
MIN_KEYS = 100                      # mniej parametrów = odpowiedź niepełna, nie robimy kopii pierwotnej
EXCLUDE_KEYS = {"device_sn"}        # numeru seryjnego nie zapisujemy w kopii
ISO = "%Y-%m-%dT%H:%M:%S"

KIND_TEXT = {"original": "Pierwotna", "manual": "Ręczna", "auto": "Przed zmianą"}

# ---------------------------------------------------------------- podział: ustawienia / odczyty
IDENT_EXACT = {"device_id", "device_type", "device_soft_version", "device_hard_version", "prod_date",
               "eth_mac"}

LIVE_EXACT = {
    # czas i zegar
    "datetime", "daytime", "date", "time", "node_time", "rtc_correction",
    # stany i statusy
    "kot_status", "pl_status", "pl_status_ext", "pl_wyg_state", "pl_plimit_state", "zima_lato_state",
    "tryb_auto_state", "cwu_state", "cwu_out_state", "kot_st_tobn", "cwu_st_tobn",
    "remote_server_status", "rf_status", "upd_pgs", "node_st", "et_stop", "et_roz", "et_pr", "et_wyg",
    # wejścia cyfrowe (stan chwilowy)
    "di_zawl", "di_zas", "di_alarm", "di_termik", "di_stb", "di_term1", "di_term2",
    # odczyty i wartości chwilowe
    "tzew_act", "kot_tact", "cwu_tact", "fuel_level", "fuel_level_enum", "time_to_empty",
    "next_fuel_time", "add_fuel_time", "stats_pwr", "act_dm_speed", "mpl_feed", "mpl_heat",
    "mpl_clean", "mpl_temp", "mpl_opto", "mpl_dm_rpm", "exh_fan_speed", "dp_value", "pl_flame",
    "pl_flame_b", "pl_tfire", "pl_power", "pl_power_kw", "pl_fuel_flow", "pl_wyg_cnt", "rp_active",
    "proc_time", "fire_time", "clwym_err", "clwym_time", "mpl_di_hall2",
    "mod2_flow", "mod2_power", "mod2_energy", "wh_global", "wh_yr", "wh_mon",
    "eth_ip_ro", "eth_mask_ro", "eth_gate_ro",
    # liczniki
    "pod_run_time", "pod_run_time_str", "pod_run_time_last", "pod_run_time_hour", "pl_tptotal",
    "clean_burn_time", "clean_act_kg",
}

_LIVE_RE = [
    re.compile(r"^out_"),                                   # wyjścia (pompy, dmuchawa ...)
    re.compile(r"_value$"),                                 # temperatury z czujników
    re.compile(r"^alarm_"), re.compile(r"_alarm$"),         # flagi alarmów
    re.compile(r"^ob\d+_(pok_tact|pok_tzad|pok_heat|term_state|zaw4d_pos|zaw4d_sta|out_pump|"
               r"out_zaw4d|t1|t2|zaw4d_tzad|t1_alarm|t2_alarm|hitemp_alarm|mr3_alarm|di_term)$"),
    re.compile(r"^rf\d+_(temp|rh|bat|sig|alarm)$"),         # termostaty RF - odczyty
    re.compile(r"^strefa\d+_(temp|heat|lock|relays|hb0|hb1|alarm)$"),
]
_IDENT_RE = [re.compile(r"^rf\d+_(t|v)$")]


def is_secret(key):
    return key.startswith(SENSITIVE_PREFIXES) or key in EXCLUDE_KEYS or key.startswith("_")


def kind_of(key):
    """Zwraca "ident", "live" albo "setting"."""
    if key in IDENT_EXACT or any(r.match(key) for r in _IDENT_RE):
        return "ident"
    if key in LIVE_EXACT or any(r.search(key) for r in _LIVE_RE):
        return "live"
    return "setting"


# ---------------------------------------------------------------- tworzenie i zapis kopii
def device_info(data, host=""):
    return {
        "id": data.get("device_id", ""),
        "name": data.get("device_name", ""),
        "type": data.get("device_type", ""),
        "soft": data.get("device_soft_version", ""),
        "hard": data.get("device_hard_version", ""),
        "host": str(host or ""),
    }


def device_key(data, host=""):
    """Bezpieczny dla nazwy pliku identyfikator sterownika (numer urządzenia albo adres)."""
    raw = data.get("device_id") or host or "sterownik"
    return re.sub(r"[^\w.-]+", "_", str(raw))


def make_backup(data, host="", kind="manual", note="", program=""):
    params = {k: str(v) for k, v in data.items() if not is_secret(k)}
    return {
        "format": FORMAT_VERSION,
        "program": program,
        "created": datetime.datetime.now().strftime(ISO),
        "kind": kind,
        "note": note,
        "device": device_info(data, host),
        "count": len(params),
        "params": params,
    }


def _write_json(path, backup):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(backup, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def original_path(key, directory=None):
    return Path(directory or BACKUP_DIR) / f"pierwotna_{key}.json"


def ensure_original(data, host="", program="", directory=None):
    """Tworzy kopię pierwotną, jeśli jeszcze nie ma jej dla tego sterownika.
    Zwraca ścieżkę nowego pliku albo None (już istnieje / odpowiedź niepełna)."""
    directory = Path(directory or BACKUP_DIR)
    if len([k for k in data if not is_secret(k)]) < MIN_KEYS:
        return None
    path = original_path(device_key(data, host), directory)
    if path.exists():
        return None
    directory.mkdir(parents=True, exist_ok=True)
    text = json.dumps(make_backup(data, host, "original", "Stan z pierwszego połączenia programu",
                                  program), ensure_ascii=False, indent=1)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        os.link(tmp, path)                 # atomowo: zawiedzie, jeśli plik już istnieje (nigdy nie nadpisuje)
    except FileExistsError:
        return None                        # ktoś był szybszy - nie nadpisujemy
    except OSError:                        # system plików bez twardych linków: tryb wyłączności
        try:
            with open(path, "x", encoding="utf-8") as f:
                f.write(text)
        except FileExistsError:
            return None
    finally:
        tmp.unlink(missing_ok=True)
    return path


def save_backup(backup, directory=None):
    """Zapisuje zwykłą kopię; zwraca ścieżkę pliku (nazwa z datą i godziną)."""
    directory = Path(directory or BACKUP_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    key = re.sub(r"[^\w.-]+", "_", str(backup.get("device", {}).get("id") or backup.get("device", {}).get("host")
                                       or "sterownik"))
    stamp = datetime.datetime.strptime(backup["created"], ISO).strftime("%Y%m%d_%H%M%S")
    path = directory / f"kopia_{key}_{stamp}.json"
    n = 2
    while path.exists():                   # dwie kopie w tej samej sekundzie
        path = directory / f"kopia_{key}_{stamp}_{n}.json"
        n += 1
    _write_json(path, backup)
    return path


# ---------------------------------------------------------------- lista i odczyt kopii
def load_backup(path):
    """Wczytuje i sprawdza plik kopii; przy błędnym pliku rzuca ValueError."""
    try:
        b = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"Nie można odczytać pliku kopii: {e}") from e
    if not isinstance(b, dict) or not isinstance(b.get("params"), dict) or "created" not in b:
        raise ValueError("To nie jest plik kopii Pello Monitor.")
    if int(b.get("format", 0)) > FORMAT_VERSION:
        raise ValueError("Kopia pochodzi z nowszej wersji programu.")
    b["params"] = {str(k): str(v) for k, v in b["params"].items() if not is_secret(str(k))}
    return b


def list_backups(directory=None):
    """Lista kopii: pierwotne na górze, potem od najnowszej. Uszkodzone pliki są pomijane."""
    out = []
    directory = Path(directory or BACKUP_DIR)
    if not directory.exists():
        return out
    for p in directory.glob("*.json"):
        try:
            b = load_backup(p)
        except ValueError:
            continue
        dev = b.get("device", {})
        out.append({"path": p, "kind": b.get("kind", "manual"), "created": b["created"],
                    "device": dev, "count": b.get("count", len(b["params"])), "note": b.get("note", "")})
    out.sort(key=lambda r: r["created"], reverse=True)
    out.sort(key=lambda r: r["kind"] != "original")
    return out


def delete_backup(path):
    """Usuwa zwykłą kopię. Kopii pierwotnej program nie usuwa."""
    path = Path(path)
    if path.name.startswith("pierwotna_") or load_backup(path).get("kind") == "original":
        raise ValueError("Kopii pierwotnej nie można usunąć z programu.")
    path.unlink()


# ---------------------------------------------------------------- porównywanie
def _num(v):
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def values_differ(a, b):
    if a == b:
        return False
    fa, fb = _num(a), _num(b)
    if fa is not None and fb is not None and str(a).strip() != "" and str(b).strip() != "":
        return abs(fa - fb) > 1e-9
    return str(a).strip() != str(b).strip()


def diff(old, new, include_live=False):
    """Porównuje dwa słowniki parametrów (kopia -> inny stan).
    Zwraca (zmiany, ukryte_odczyty): zmiany to lista (klucz, status, stara, nowa, rodzaj),
    status: "zmieniony" / "nowy" / "usunięty"."""
    order = {g: i for i, g in enumerate(GROUP_ORDER)}
    changes, hidden = [], 0
    for key in set(old) | set(new):
        if is_secret(key):
            continue
        in_old, in_new = key in old, key in new
        if in_old and in_new:
            if not values_differ(old[key], new[key]):
                continue
            status = "zmieniony"
        else:
            status = "nowy" if in_new else "usunięty"
        kind = kind_of(key)
        if kind == "live" and not include_live:
            hidden += 1
            continue
        changes.append((key, status, old.get(key), new.get(key), kind))
    changes.sort(key=lambda c: (order.get(group_of(c[0]), 999), c[0]))
    return changes, hidden
