import gi, os
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gdk, GLib

class AnimatedSprite:
    def __init__(self, filename, fps=12):
        self._is_gif = filename.lower().endswith(".gif")

        if self._is_gif:
            self._anim  = GdkPixbuf.PixbufAnimation.new_from_file(filename)
            self._iter  = self._anim.get_iter(None)
            self._paint = Gdk.Texture.new_for_pixbuf(self._iter.get_pixbuf())
            delay = max(self._iter.get_delay_time(), 16)
            self._tick  = GLib.timeout_add(delay, self._advance_gif)
        else:
            sheet   = GdkPixbuf.Pixbuf.new_from_file(filename)
            size    = sheet.get_height()
            cols    = sheet.get_width() // size
            self._pixframes = [
                sheet.new_subpixbuf(i*size, 0, size, size)
                for i in range(cols)
            ]
            self._frames = [
                Gdk.Texture.new_for_pixbuf(p)
                for p in self._pixframes
            ]
            self._index = 0
            self._paint = self._frames[0]
            self._tick  = GLib.timeout_add(int(1000/fps), self._advance_sheet)

    def _advance_gif(self):
        self._iter.advance(None)
        pix = self._iter.get_pixbuf()
        self._paint = Gdk.Texture.new_for_pixbuf(pix)
        delay = max(self._iter.get_delay_time(), 16)
        GLib.source_remove(self._tick)
        self._tick = GLib.timeout_add(delay, self._advance_gif)
        return False

    def _advance_sheet(self):
        self._index = (self._index + 1) % len(self._frames)
        self._paint = self._frames[self._index]
        return True

    def get_paintable(self):
        return self._paint

    def get_pixbuf(self):
        if self._is_gif:
            return self._iter.get_pixbuf()
        else:
            return self._pixframes[self._index]

    def stop(self):
        if hasattr(self, "_tick"):
            GLib.source_remove(self._tick)
            del self._tick