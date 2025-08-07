import os, ctypes, ctypes.util, gi

lib = ctypes.util.find_library("gtk4-layer-shell")
if lib:
    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)

gi.require_version("Gtk4LayerShell", "1.0")
gi.require_version("Gtk",        "4.0")
from gi.repository import Gtk4LayerShell as ls, Gtk, Gdk, GLib

from sprite             import AnimatedSprite
from behavior_manager   import BehaviorManager

css = Gtk.CssProvider()
css.load_from_data(b"""
.transparent {
    background: transparent;
}
""")
Gtk.StyleContext.add_provider_for_display(
    Gdk.Display.get_default(),
    css,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)

class CatWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Wayland-Cat")
        self.add_css_class("transparent")
        self.set_decorated(False)
        self.set_resizable(False)

        ls.init_for_window(self)
        ls.set_layer(self, ls.Layer.OVERLAY)
        ls.set_keyboard_mode(self, ls.KeyboardMode.NONE)
        for edge in (ls.Edge.TOP, ls.Edge.LEFT):
            ls.set_anchor(self, edge, True)
            ls.set_margin(self, edge, 0)

        disp     = Gdk.Display.get_default()
        monitors = disp.get_monitors()
        if not monitors:
            raise SystemExit("No monitors found!")
        geom = monitors[0].get_geometry()

        self.bm = BehaviorManager(geom.width, geom.height)

        self.pos_x  = geom.width  / 2
        self.pos_y  = geom.height / 2
        self.facing = 1
        self._mode  = None

        self._load_behavior()

        click = Gtk.GestureClick.new()
        click.set_button(1)
        click.connect("pressed", self._on_click)
        self.add_controller(click)

    def _load_behavior(self):
        for name in ("_move_id", "_refresh_id"):
            if hasattr(self, name):
                GLib.source_remove(getattr(self, name))

        asset    = self.bm.get_asset()
        fps      = self.bm.get_fps()
        interval = self.bm.get_move_interval()

        self.sprite = AnimatedSprite(asset, fps=fps)
        pic = Gtk.Picture.new_for_paintable(self.sprite.get_paintable())
        self.set_child(pic)
        self.picture = pic

        w = self.sprite.get_pixbuf().get_width()
        h = self.sprite.get_pixbuf().get_height()
        self.set_default_size(w, h)
        self.picture.set_size_request(w, h)

        self._refresh_id = GLib.timeout_add(int(1000/fps), self._refresh)
        self._move_id    = GLib.timeout_add(interval,       self._move)
        self._mode       = self.bm.mode()

    def _refresh(self):
        pix = self.sprite.get_pixbuf()
        if self.facing < 0:
            pix = pix.flip(True)
        tex = Gdk.Texture.new_for_pixbuf(pix)
        self.picture.set_paintable(tex)
        return True

    def _move(self):
        nx, ny, facing = self.bm.update(self.pos_x, self.pos_y)
        self.pos_x, self.pos_y = nx, ny
        self.facing          = facing

        ls.set_margin(self, ls.Edge.LEFT, int(nx))
        ls.set_margin(self, ls.Edge.TOP,  int(ny))
        self.queue_resize()

        if self.bm.mode() != self._mode:
            self._load_behavior()

        print(f"mode={self.bm.mode():4s} steps={self.bm.get_steps():4d}", end="\r")
        return True

    def _on_click(self, gesture, n_press, x, y):
        if self.bm.mode() != "run":
            self.bm.switch("run")
            self._load_behavior()

def on_activate(app):
    if not hasattr(app, "win"):
        app.win = CatWindow(app)
    app.win.present()

app = Gtk.Application()
app.connect("activate", on_activate)
app.run()