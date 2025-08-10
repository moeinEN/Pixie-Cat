import os
from importlib import resources
import gi
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gdk, GLib

def _resolve_asset(path):
    if os.path.isabs(path) and os.path.exists(path):
        return path
    cands = [path]
    if not path.startswith("assets/"):
        cands.append(f"assets/{path}")
    try:
        import pixie
        pkg_dir = os.path.dirname(pixie.__file__)
        for p in cands:
            p2 = p.split("assets/", 1)[-1]
            abs_p = os.path.join(pkg_dir, "assets", p2)
            if os.path.exists(abs_p):
                return abs_p
    except Exception:
        pass
    for p in cands:
        try:
            f = resources.files("pixie").joinpath(p)
            try:
                if f.is_file():
                    return str(f)
            except Exception:
                pass
            fp = str(f)
            if os.path.exists(fp):
                return fp
        except Exception:
            pass
        if os.path.exists(p):
            return p
    try:
        cwd_pkg = os.path.join(os.getcwd(), "pixie", "assets")
        p2 = path.split("assets/", 1)[-1]
        fp = os.path.join(cwd_pkg, p2)
        if os.path.exists(fp):
            return fp
    except Exception:
        pass
    return path

class AnimatedSprite:
    def __init__(self, filename, fps=12):
        self._stopped = False
        self._tick = 0
        filename = _resolve_asset(filename)
        self._is_gif = str(filename).lower().endswith(".gif")
        if self._is_gif:
            self._anim = GdkPixbuf.PixbufAnimation.new_from_file(filename)
            self._iter = self._anim.get_iter(None)
            self._paint = Gdk.Texture.new_for_pixbuf(self._iter.get_pixbuf())
            self._schedule_next()
        else:
            pix = GdkPixbuf.Pixbuf.new_from_file(filename)
            self._pixframes = [pix]
            self._index = 0
            self._paint = Gdk.Texture.new_for_pixbuf(self._pixframes[0])

    def _schedule_next(self):
        if self._stopped or not self._is_gif:
            return
        delay = self._iter.get_delay_time()
        if delay <= 0:
            delay = 80
        if self._tick:
            try:
                GLib.source_remove(self._tick)
            except Exception:
                pass
            self._tick = 0
        self._tick = GLib.timeout_add(delay, self._advance)

    def _advance(self):
        if self._stopped or not self._is_gif:
            return False
        try:
            self._iter.advance(None)
        except Exception:
            pass
        self._schedule_next()
        return False

    def get_pixbuf(self):
        if self._is_gif:
            return self._iter.get_pixbuf()
        return self._pixframes[self._index]

    def stop(self):
        self._stopped = True
        tid = getattr(self, "_tick", 0)
        if tid:
            try:
                GLib.source_remove(tid)
            except Exception:
                pass
            self._tick = 0