"""
pello_client.py - komunikacja ze sterownikiem (HTTP) oraz zapis/odczyt historii CSV.
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>
"""
import base64
import csv
import datetime
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from pello_config import CHART_SERIES, CSV_DIR, CSV_KEYS, TIME_FMT, TIMEOUT, tofloat
from pello_locks import lock_reason
from pello_params import SENSITIVE_PREFIXES


def parse_sync(text):
    """Zamienia odpowiedź syncvalues.cgi na słownik {klucz: wartość}.

    Linia 0 to parametry sterownika. Kolejne linie to urządzenia pomocnicze:
      1..99  -> termostaty/czujniki RF   (klucze  rf<N>_...)
      100+   -> strefy termostatów       (klucze  strefa<N>_...)
    Linie nieaktywne (s:0) pomijamy. Dane dostępowe (auth_*) nigdy nie trafiają do programu.
    """
    data = {}
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]   # puste linie nie przesuwają numeracji
    for i, line in enumerate(lines):
        parts = line.split(";")
        num = parts[0].strip()
        if i == 0:
            prefix = ""
        elif num.isdigit():
            prefix = f"rf{num}_" if int(num) < 100 else f"strefa{num}_"
        else:
            continue
        items = {}
        for item in parts[1:]:
            if ":" in item:
                k, v = item.split(":", 1)
                items[k] = v
        if i > 0 and items.get("s") != "1":
            continue
        for k, v in items.items():
            if k == "s" or k.startswith(SENSITIVE_PREFIXES):
                continue
            data[prefix + k] = urllib.parse.unquote(v)
    return data


class PelloWriteError(Exception):
    """Sterownik odmówił zapisu nastawy (np. access_denied) albo brak uprawnień."""


_REG_TAG = re.compile(r"<reg\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")

_STATUS_TEXT = {
    "access_denied": "brak uprawnień do zapisu tego rejestru (sprawdź login i hasło - "
                     "użytkownik musi mieć prawa zapisu)",
    "error": "sterownik zgłosił błąd zapisu",
}


def check_write_response(text):
    """Analizuje odpowiedź setregister.cgi.

    Zwraca True, gdy sterownik potwierdził zapis (status="ok" we wszystkich znacznikach <reg>),
    None, gdy odpowiedź nie zawiera informacji o statusie (wtedy trzeba sprawdzić odczytem),
    a gdy któryś rejestr ma status inny niż "ok" (np. access_denied) - rzuca PelloWriteError.
    """
    statuses = []
    for tag in _REG_TAG.findall(text or ""):
        attrs = {m[0].lower(): (m[1] or m[2]) for m in _ATTR.findall(tag)}
        if "status" in attrs:
            statuses.append((attrs.get("name") or attrs.get("id") or "", attrs["status"]))
    if not statuses:
        return None
    bad = [(n, st) for n, st in statuses if st.strip().lower() != "ok"]
    if bad:
        name, st = bad[0]
        why = _STATUS_TEXT.get(st.strip().lower(), f"status: {st}")
        raise PelloWriteError(f"Sterownik odrzucił zapis{' ' + name if name else ''} ({st}): {why}.")
    return True


def values_equal(actual, expected):
    """Porównuje wartość odczytaną ze sterownika z zadaną (liczby z tolerancją)."""
    a, b = tofloat(actual), tofloat(expected)
    if a is not None and b is not None:
        return abs(a - b) < 0.01
    return actual is not None and str(actual).strip() == str(expected).strip()


class PelloClient:
    """Odczyt syncvalues.cgi i zapis nastaw przez setregister.cgi."""

    def __init__(self, host, user, password):
        self.host = host.strip()
        self.user = user
        self.password = password

    def _open(self, path):
        req = urllib.request.Request(f"http://{self.host}{path}")
        if self.user and self.password:
            token = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            req.add_header("Authorization", f"Basic {token}")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def read_all(self):
        return parse_sync(self._open("/syncvalues.cgi"))

    def set_register(self, key, value):
        """Wysyła nastawę. Zwraca True (sterownik potwierdził), None (brak statusu w odpowiedzi)
        albo rzuca PelloWriteError, gdy sterownik odmówił zapisu."""
        if not re.fullmatch(r"\w+", str(key)):
            raise PelloWriteError(f"Niedozwolona nazwa rejestru: {key!r}")
        locked = lock_reason(key)                  # ostatnia linia obrony: żadna ścieżka nie zapisze tych kluczy
        if locked:
            raise PelloWriteError(f"Program nie zapisuje parametru {key}. {locked}")
        query = f"device=0&{key}={urllib.parse.quote(str(value), safe='')}"
        try:
            text = self._open(f"/setregister.cgi?{query}")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise PelloWriteError(f"Brak uprawnień (HTTP {e.code}) - sprawdź login i hasło.") from e
            raise
        return check_write_response(text)

    def set_and_verify(self, key, value, attempts=4, delay=1.0):
        """Zapisuje nastawę i potwierdza ją odczytem zwrotnym.

        Zwraca (ok, wartość_odczytana, dane). Odmowę zgłoszoną przez sterownik (access_denied)
        zwraca jako wyjątek PelloWriteError. Odczyt zwrotny działa niezależnie od formatu
        odpowiedzi, więc wykrywa też ciche ignorowanie zapisu."""
        self.set_register(key, value)
        actual, data = None, {}
        for _ in range(attempts):
            time.sleep(delay)
            data = self.read_all()
            actual = data.get(key)
            if values_equal(actual, value):
                return True, actual, data
        return False, actual, data


def _csv_value(data, k):
    v = data.get(k, "")
    if tofloat(v) is not None:
        v = str(v).replace(".", ",")   # przecinek dziesiętny dla polskiego Excela
    return v


def write_csv(now, data):
    """Dopisuje odczyt do pliku z dzisiejszą datą. Zwraca tekst błędu albo ''."""
    try:
        CSV_DIR.mkdir(parents=True, exist_ok=True)
        path = CSV_DIR / f"pello_{now:%Y-%m-%d}.csv"
        header = None
        if path.exists() and path.stat().st_size > 0:      # plik z wcześniejszej wersji ma inne kolumny
            with open(path, newline="", encoding="utf-8-sig") as f:
                header = next(csv.reader(f, delimiter=";"), None)
        cols = header if header else ["czas"] + CSV_KEYS
        row = [now.strftime(TIME_FMT)] + [_csv_value(data, k) for k in cols[1:]]
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            if not header:
                w.writerow(cols)
            w.writerow(row)
        return ""
    except PermissionError:
        return "CSV: plik zablokowany (zamknij go w Excelu)"
    except Exception as e:
        return f"CSV: {e}"


def export_snapshot(data, describe):
    """Zapisuje pełny zrzut wszystkich parametrów do pliku CSV. Zwraca ścieżkę."""
    from pello_params import group_of
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    path = CSV_DIR / f"pello_parametry_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["grupa", "opis", "parametr", "wartosc"])
        for k in sorted(data, key=lambda x: (group_of(x), x)):
            w.writerow([group_of(k), describe(k) if describe(k) != k else "", k, data[k]])
    return path


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
