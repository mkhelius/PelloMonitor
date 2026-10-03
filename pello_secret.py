"""
pello_secret.py - bezpieczne przechowywanie hasła do sterownika.
Pello Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Kolejność prób (pierwsza, która zadziała):
  1. "keyring" - Menedżer poświadczeń Windows (biblioteka keyring, jeśli jest zainstalowana),
  2. "dpapi"   - szyfrowanie Windows DPAPI (tylko to konto Windows odczyta hasło; bez dodatkowych
                 bibliotek). W pliku ustawień zostaje tylko zaszyfrowany ciąg.
  3. "plain"   - OSTATECZNOŚĆ (np. system inny niż Windows): hasło jawnym tekstem w pliku ustawień.

Plik ustawień dostaje pola: pw_store ("keyring" / "dpapi" / "plain") oraz zależnie od metody
pw_enc (dpapi) albo password (plain). Stary plik z samym polem "password" jest rozpoznawany
jako "plain" i po wczytaniu zostaje zmigrowany do bezpieczniejszej metody.
"""
import base64
import os

SERVICE = "PelloMonitor"

METHOD_TEXT = {
    "keyring": "Hasło zapisane w Menedżerze poświadczeń Windows.",
    "dpapi": "Hasło zapisane zaszyfrowane (Windows DPAPI) – odczyta je tylko to konto Windows.",
    "plain": "UWAGA: hasło zapisane jawnym tekstem w pliku ustawień (brak bezpieczniejszej metody).",
    "none": "",
}


def _account(host, user):
    return f"{user}@{host}"


# ---------------------------------------------------------------- 1. keyring
def _keyring():
    """Zwraca moduł keyring, jeśli jest dostępny i ma działający backend; w przeciwnym razie None."""
    try:
        import keyring
        backend = keyring.get_keyring()
        if backend.__class__.__module__.startswith("keyring.backends.fail"):
            return None
        return keyring
    except Exception:
        return None


# ---------------------------------------------------------------- 2. DPAPI (Windows)
def _dpapi(data, protect):
    """Szyfruje (protect=True) lub odszyfrowuje dane przez Windows DPAPI (CryptProtectData)."""
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = BLOB()
    if protect:
        ok = crypt32.CryptProtectData(ctypes.byref(blob_in), "PelloMonitor", None, None, None, 0,
                                      ctypes.byref(blob_out))
    else:
        ok = crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0,
                                        ctypes.byref(blob_out))
    if not ok:
        raise OSError("Windows DPAPI: operacja nie powiodła się")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def _dpapi_available():
    return os.name == "nt"


# ---------------------------------------------------------------- API
def store(host, user, password):
    """Zapisuje hasło najlepszą dostępną metodą. Zwraca fragment słownika do pliku ustawień."""
    kr = _keyring()
    if kr is not None:
        try:
            kr.set_password(SERVICE, _account(host, user), password)
            return {"pw_store": "keyring"}
        except Exception:
            pass
    if _dpapi_available():
        try:
            blob = _dpapi(password.encode("utf-8"), True)
            return {"pw_store": "dpapi", "pw_enc": base64.b64encode(blob).decode("ascii")}
        except Exception:
            pass
    return {"pw_store": "plain", "password": password}


def load(cfg, host, user):
    """Odczytuje hasło wg pól pliku ustawień. Zwraca (hasło, metoda); metoda "none" = brak hasła.
    Stary format (samo pole "password") zwraca metodę "plain"."""
    method = cfg.get("pw_store") or ("plain" if cfg.get("password") else "none")
    try:
        if method == "keyring":
            kr = _keyring()
            return (kr.get_password(SERVICE, _account(host, user)) or "", method) if kr else ("", method)
        if method == "dpapi":
            blob = base64.b64decode(cfg.get("pw_enc", ""))
            return _dpapi(blob, False).decode("utf-8"), method
        if method == "plain":
            return cfg.get("password", ""), method
    except Exception:
        pass
    return "", method


def forget(host, user):
    """Usuwa hasło z Menedżera poświadczeń (jeśli było tam zapisane)."""
    kr = _keyring()
    if kr is not None:
        try:
            kr.delete_password(SERVICE, _account(host, user))
        except Exception:
            pass
