"""
pello_tray.py - ikona płomienia (okno, plik .exe, zasobnik) oraz powiadomienia Windows.
Pello 3.5 Monitor (wersja FREE) - autor: Mariusz <mk.helius@gmail.com>

Uruchomienie  `python pello_tray.py pello.ico`  zapisuje ikonę pliku .exe.
"""
import io
import sys

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_OK = True
except Exception:  # brak bibliotek pystray / Pillow
    TRAY_OK = False
    try:
        from PIL import Image, ImageDraw
    except Exception:
        Image = ImageDraw = None

STATE_COLORS = {
    "ok": (255, 120, 30, 255),       # pomarańczowy - praca
    "alarm": (230, 30, 30, 255),     # czerwony - alarm
    "off": (150, 150, 150, 255),     # szary - brak połączenia
}


def make_icon(state="ok", size=64):
    """Rysuje płomień w kółku (skalowany do dowolnego rozmiaru)."""
    col = STATE_COLORS.get(state, STATE_COLORS["ok"])
    k = size / 64.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2 * k, 2 * k, 62 * k, 62 * k), fill=(35, 35, 35, 255), outline=col,
              width=max(1, round(4 * k)))
    flame = [(32, 10), (46, 32), (44, 48), (32, 54), (20, 48), (18, 32), (26, 26)]
    d.polygon([(x * k, y * k) for x, y in flame], fill=col)
    core = [(32, 30), (39, 42), (32, 50), (25, 42)]
    d.polygon([(x * k, y * k) for x, y in core], fill=(255, 235, 130, 255))
    return img


def icon_png_base64(size=64):
    """Ikona okna (pasek tytułu / pasek zadań) jako PNG w base64 - dla tk.PhotoImage."""
    if Image is None:
        return None
    import base64
    buf = io.BytesIO()
    make_icon("ok", size).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def save_ico(path):
    """Zapisuje wielorozmiarową ikonę .ico (do pliku .exe)."""
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    make_icon("ok", 256).save(path, format="ICO", sizes=sizes)


class Tray:
    """Ikona w zasobniku systemowym + powiadomienia. Bez pystray/Pillow działa jako atrapa."""

    def __init__(self, title, on_show, on_quit):
        self.title = title
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon = None
        self._state = None
        self.ok = False

    def start(self):
        if not TRAY_OK:
            return False
        try:
            menu = pystray.Menu(
                pystray.MenuItem("Pokaż okno", lambda icon, item: self._on_show(), default=True),
                pystray.MenuItem("Zakończ", lambda icon, item: self._on_quit()),
            )
            self._icon = pystray.Icon("pello_monitor", make_icon("off"), self.title, menu)
            self._state = "off"
            self._icon.run_detached()
            self.ok = True
        except Exception:
            self.ok = False
        return self.ok

    def set_state(self, state, tooltip=None):
        if not self.ok:
            return
        try:
            if state != self._state:
                self._icon.icon = make_icon(state)
                self._state = state
            if tooltip:
                self._icon.title = tooltip[:120]
        except Exception:
            pass

    def notify(self, title, msg):
        if not self.ok:
            return
        try:
            self._icon.notify(msg, title)
        except Exception:
            pass

    def stop(self):
        if not self.ok:
            return
        try:
            self._icon.stop()
        except Exception:
            pass


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "pello.ico"
    save_ico(target)
    print("Zapisano ikonę:", target)
