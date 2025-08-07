import os, math, ctypes, ctypes.util, gi
lib = ctypes.util.find_library("gtk4-layer-shell")
if lib:
    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)

gi.require_version("Gtk4LayerShell", "1.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk4LayerShell as ls, Gtk, Gdk, GLib
from sprite import AnimatedSprite

ASSET   = os.path.abspath("assets/walk-crop.gif")
STEP    = 12
MOVE_MS = 16

css = Gtk.CssProvider()
css.load_from_data(b".transparent { background: transparent; }")
Gtk.StyleContext.add_provider_for_display(
    Gdk.Display.get_default(), css,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

class CatWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Wayland-Cat")
        self.add_css_class("transparent")
        self.set_decorated(False)
        self.set_resizable(False)

        ls.init_for_window(self)
        ls.set_layer(self, ls.Layer.OVERLAY)
        ls.set_keyboard_mode(self, ls.KeyboardMode.NONE)
        for e in (ls.Edge.TOP, ls.Edge.LEFT):
            ls.set_anchor(self, e, True)
            ls.set_margin(self, e, 0)

        if not os.path.exists(ASSET):
            raise SystemExit(f"asset not found: {ASSET}")
        self.sprite   = AnimatedSprite(ASSET, fps=12)
        self.picture  = Gtk.Picture.new_for_paintable(self.sprite.get_paintable())
        self.set_child(self.picture)

        GLib.timeout_add(int(1000/60), self._refresh)
        GLib.timeout_add(MOVE_MS,       self._move)

        self.pos_x = self.pos_y = 0

    def _refresh(self):
        self.picture.set_paintable(self.sprite.get_paintable())
        return True

    def _move(self):
        seat    = self.get_display().get_default_seat()
        pointer = seat.get_pointer()
        surface, sx, sy = pointer.get_surface_at_position()
        if surface is None:
            return True

        if hasattr(surface, "get_position"):
            ox, oy = surface.get_position()
        elif hasattr(surface, "get_origin"):
            ox, oy = surface.get_origin()
        else:
            ox, oy = 0, 0
        px, py = ox + sx, oy + sy

        w, h = self.get_width() or 1, self.get_height() or 1
        tx, ty = px - w/2, py - h/2
        dx, dy = tx - self.pos_x, ty - self.pos_y
        dist   = math.hypot(dx, dy)

        if dist > 1:
            self.pos_x += dx/dist * STEP
            self.pos_y += dy/dist * STEP
            ls.set_margin(self, ls.Edge.LEFT, int(self.pos_x))
            ls.set_margin(self, ls.Edge.TOP,  int(self.pos_y))
            self.queue_resize()
        return True

def on_activate(app):
    if not hasattr(app, "cat_win"):
        app.cat_win = CatWindow(app)
    app.cat_win.present()

app = Gtk.Application()
app.connect("activate", on_activate)
app.run()   