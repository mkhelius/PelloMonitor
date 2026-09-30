"""
pello_client.py - komunikacja ze sterownikiem (HTTP) oraz zapis/odczyt historii CSV.
Pello 3.5 Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>
"""
import base64
import csv
import datetime
import urllib.parse
import urllib.request

from pello_config import ALL_KEYS, CHART_SERIES, CSV_DIR, TIME_FMT, TIMEOUT, tofloat


def parse_modules(lines):
    """Parsuje linie modułów syncvalues.cgi (po pierwszej linii głównej).

    Format: 86;<unixtime>;s:1;t:BT4;temp:22.70;...   oraz  100;<...>;s:1;t_lo:19.00;...
    Zwraca słownik: id_modulu -> {klucz: wartosc} (wartości zdekodowane z URL).
    """
    modules = {}
    for line in lines:
        line = line.strip()
        if not line or ";" not in line:
            continue
        parts = line.split(";")
        if not parts[0].isdigit():
            continue
        mod = {}
        for item in parts[1:]:
            if ":" in item:
                k, v = item.split(":", 1)
                k = urllib.parse.unquote(k).strip()
                if k:
                    mod[k] = urllib.parse.unquote(v).strip()
        modules[parts[0]] = mod
    return modules


class PelloClient:
    """Odczyt syncvalues.cgi i zapis nastaw przez setregister.cgi."""

    def __init__(self, host, user, password):
        self.host = host.strip()
        self.user = user
        self.password = password
        self.modules = {}          # surowe dane modułów (BT4, termostaty)

    def _open(self, path):
        req = urllib.request.Request(f"http://{self.host}{path}")
        if self.user and self.password:
            token = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            req.add_header("Authorization", f"Basic {token}")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def read_all(self):
        """Zwraca płaski słownik parametrów; scalone dane modułów (BT4, termostaty).

        Puste pola sterownika (np. tpod_value:) zostają pustym stringiem -
        tofloat() zamienia je bezpiecznie na None, więc wykres się nie sypie.
        """
        text = self._open("/syncvalues.cgi")
        lines = text.split("\n")

        data = {}
        for item in lines[0].split(";"):
            if ":" in item:
                k, v = item.split(":", 1)
                k = urllib.parse.unquote(k).strip()
                if k:
                    data[k] = urllib.parse.unquote(v).strip()

        # ---- moduły (linie po pierwszej)
        self.modules = parse_modules(lines[1:])

        # czujnik bezprzewodowy BT4 (moduł 86) - liczy się pomiar, nie flaga s:
        bt4 = self.modules.get("86")
        if bt4 and bt4.get("temp", ""):
            data["bt4_temp"] = bt4.get("temp", "")
            data["bt4_rh"] = bt4.get("rh", "")
            data["bt4_bat"] = bt4.get("bat", "")
            data["bt4_sig"] = bt4.get("sig", "")
            data["bt4_alarm"] = bt4.get("alarm", "0")

        # awaryjnie: szukaj modulu z t:BT4, gdyby mial inne ID niz 86
        if "bt4_temp" not in data:
            for m in self.modules.values():
                if m.get("t") == "BT4" and m.get("temp", ""):
                    data["bt4_temp"] = m["temp"]
                    data["bt4_rh"] = m.get("rh", "")
                    data["bt4_bat"] = m.get("bat", "")
                    data["bt4_sig"] = m.get("sig", "")
                    data["bt4_alarm"] = m.get("alarm", "0")
                    break

        # termostaty pokojowe (moduły 100-119) - tylko aktywne z pomiarem temperatury
        for mid, m in self.modules.items():
            if mid.isdigit() and 100 <= int(mid) <= 119 and m.get("temp", ""):
                if m.get("temp", ""):
                    data[f"thm{mid}_temp"] = m["temp"]
                    data[f"thm{mid}_tzad"] = m.get("t_norm", "")
                    data[f"thm{mid}_t_lo"] = m.get("t_lo", "")
                    data[f"thm{mid}_t_hi"] = m.get("t_hi", "")
                    data[f"thm{mid}_lock"] = m.get("lock", "0")
                    data[f"thm{mid}_alarm"] = m.get("alarm", "0")
        return data

    def set_register(self, key, value):
        self._open(f"/setregister.cgi?device=0&{key}={value}")


def write_csv(now, data):
    """Dopisuje odczyt do pliku z dzisiejszą datą. Zwraca tekst błędu albo ''."""
    try:
        CSV_DIR.mkdir(parents=True, exist_ok=True)
        path = CSV_DIR / f"pello_{now:%Y-%m-%d}.csv"
        new = not path.exists() or path.stat().st_size == 0
        row = [now.strftime(TIME_FMT)]
        for k in ALL_KEYS:
            v = data.get(k, "")
            if tofloat(v) is not None:
                v = str(v).replace(".", ",")   # przecinek dziesiętny dla polskiego Excela
            row.append(v)
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            if new:
                w.writerow(["czas"] + ALL_KEYS)
            w.writerow(row)
        return ""
    except PermissionError:
        return "CSV: plik zablokowany (zamknij go w Excelu)"
    except Exception as e:
        return f"CSV: {e}"


def load_history(hours=24):
    """Wczytuje punkty wykresu z dzisiejszego i wczorajszego pliku CSV."""
    result = []
    today = datetime.date.today()
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
    for day in (today - datetime.timedelta(days=1), today):
        path = CSV_DIR / f"pello_{day:%Y-%m-%d}.csv"
        if not path.exists():
            continue
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f, delimiter=";"):
                    try:
                        t = datetime.datetime.strptime(row["czas"], TIME_FMT)
                    except (KeyError, ValueError):
                        continue
                    if t >= cutoff:
                        result.append((t, {k: tofloat(row.get(k)) for k, _, _, _ in CHART_SERIES}))
        except Exception:
            pass
    return result