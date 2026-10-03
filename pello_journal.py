"""
pello_journal.py - dziennik zmian parametrów (logika, bez okna).
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Każda próba zmiany parametru ze sterownika trafia do pliku JSON na tym komputerze
(C:\\Users\\<Ty>\\PelloMonitor\\dziennik_zmian.json). Wpis zawiera m.in.: czas, parametr, starą i nową
wartość, wynik zapisu (potwierdzony odczytem lub nie), nazwę automatycznej kopii zrobionej przed
zmianą oraz - jeśli zmiana została cofnięta - numer wpisu cofającego.

Cofnąć można tylko zmianę potwierdzoną odczytem ("ok"), która nie została jeszcze cofnięta.
"""
import datetime
import json
import os
import threading
from pathlib import Path

JOURNAL_FILE = Path.home() / "PelloMonitor" / "dziennik_zmian.json"
FORMAT_VERSION = 1
ISO = "%Y-%m-%dT%H:%M:%S"

_lock = threading.RLock()


def _read(path):
    """Czyta wpisy. Błąd odczytu pliku (OSError) przepuszcza; uszkodzony JSON odkłada na bok
    (plik .uszkodzony_...), żeby nowe wpisy nie nadpisały danych, które da się jeszcze odzyskać."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        entries = data["entries"] if isinstance(data, dict) else data
        if not isinstance(entries, list):
            raise ValueError("zły format")
        return [e for e in entries if isinstance(e, dict) and "id" in e]
    except (ValueError, KeyError, TypeError):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            os.replace(path, path.with_name(f"{path.name}.uszkodzony_{stamp}"))
        except OSError:
            pass
        return []


def _write(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"format": FORMAT_VERSION, "entries": entries}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    os.replace(tmp, path)


def load(path=None):
    """Wszystkie wpisy (od najstarszego). Przy niedostępnym pliku zwraca pustą listę."""
    with _lock:
        try:
            return _read(Path(path or JOURNAL_FILE))
        except OSError:
            return []


def add(entry, path=None):
    """Dopisuje wpis, nadając mu kolejny numer "id" i czas. Zwraca wpis. Rzuca OSError przy błędzie zapisu."""
    path = Path(path or JOURNAL_FILE)
    with _lock:
        entries = _read(path)
        entry = dict(entry)
        entry["id"] = max((int(e.get("id", 0)) for e in entries), default=0) + 1
        entry.setdefault("time", datetime.datetime.now().strftime(ISO))
        entries.append(entry)
        _write(path, entries)
        return entry


def mark_undone(entry_id, by_id, path=None):
    """Oznacza wpis jako cofnięty przez wpis by_id."""
    path = Path(path or JOURNAL_FILE)
    with _lock:
        entries = _read(path)
        for e in entries:
            if e.get("id") == entry_id:
                e["undone_by"] = by_id
        _write(path, entries)


def get(entry_id, path=None):
    for e in load(path):
        if e.get("id") == entry_id:
            return e
    return None


def undoable(entry):
    """Cofnąć można tylko zmianę potwierdzoną odczytem, która nie została jeszcze cofnięta."""
    return bool(entry) and entry.get("result") == "ok" and not entry.get("undone_by")
