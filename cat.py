import os
import signal
import math
import ctypes, ctypes.util
import gi

lib = ctypes.util.find_library("gtk4-layer-shell")
if lib:
    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)

gi.require_version("Gtk4LayerShell", "1.0")
gi.require_version("Gtk",        "4.0")
from gi.repository import Gtk4LayerShell as ls, Gtk, Gdk, GLib

from sprite           import AnimatedSprite
from behavior_manager import BehaviorManager

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

DEATH_DURATION_MS = 500
ATTACK_THRESHOLD = 64

class CatWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Wayland-Cat")
        self._app      = app
        self._dying    = False
        self._happy_timeout_id = None
        self._is_happy       = False

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
        geom     = monitors[0].get_geometry()

        self.bm = BehaviorManager(geom.width, geom.height)

        self.pos_x  = geom.width  / 2
        self.pos_y  = geom.height / 2
        self.facing = 1
        self._mode  = None

        self.picture = Gtk.Picture.new_for_paintable(None)
        self.set_child(self.picture)

        click = Gtk.GestureClick.new()
        click.set_button(1)
        click.connect("pressed", lambda *_: self._trigger_run())
        self.picture.add_controller(click)

        motion = Gtk.EventControllerMotion.new()
        motion.connect("motion", self._on_motion)
        motion.connect("leave",  self._on_pointer_leave)
        self.picture.add_controller(motion)

        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", self._on_scroll)
        self.picture.add_controller(scroll)

        self._load_behavior()

        self.connect("close-request", self._on_close_request)
        try:
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT,  self._on_close_request)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._on_close_request)
        except AttributeError:
            signal.signal(signal.SIGINT,  lambda *a: GLib.idle_add(self._on_close_request))
            signal.signal(signal.SIGTERM, lambda *a: GLib.idle_add(self._on_close_request))

    def _on_pointer_leave(self, controller):
        if not self._dying and self.bm.mode() == "attack":
            self.bm.switch("walk")
            self._load_behavior()

    def _on_scroll(self, controller, dx, dy):
        if self._dying or abs(dy) < 0.1:
            return True

        if not self._is_happy:
            self._start_happy()
        else:
            self._extend_happy()

        return True

    def _start_happy(self):
        happy_beh = self.bm._behaviors["happy"]
        self.bm.switch("happy")
        self._load_behavior()
        self._is_happy = True

        if self._happy_timeout_id:
            GLib.source_remove(self._happy_timeout_id)
        self._happy_timeout_id = GLib.timeout_add(
            happy_beh.duration_ms,
            self._end_happy
        )

    def _extend_happy(self):
        if self._happy_timeout_id:
            GLib.source_remove(self._happy_timeout_id)
        happy_beh = self.bm._behaviors["happy"]
        self._happy_timeout_id = GLib.timeout_add(
            happy_beh.duration_ms,
            self._end_happy
        )

    def _end_happy(self):
        if self.bm.mode() == "happy":
            self.bm.switch("walk")
            self._load_behavior()
        self._is_happy        = False
        self._happy_timeout_id = None
        return False
    
    def _load_behavior(self):
        for tid in ("_move_id", "_refresh_id"):
            if hasattr(self, tid):
                GLib.source_remove(getattr(self, tid))

        asset    = self.bm.get_asset()
        fps      = self.bm.get_fps()
        interval = self.bm.get_move_interval()

        self.sprite = AnimatedSprite(asset, fps=fps)
        self.picture.set_paintable(self.sprite.get_paintable())

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

        self.facing = facing

        ls.set_margin(self, ls.Edge.LEFT, int(nx))
        ls.set_margin(self, ls.Edge.TOP,  int(ny))
        self.queue_resize()

        if self.bm.mode() != self._mode:
            self._load_behavior()
        return True

    def _trigger_run(self):
        if not self._dying and self.bm.mode() != "run":
            self.bm.switch("run")
            self._load_behavior()

    def _on_motion(self, controller, x, y):
        mode = self.bm.mode()
        if self._dying or mode in ("run", "happy"):
            return

        alloc_w = self.picture.get_allocated_width()
        alloc_h = self.picture.get_allocated_height()
        if alloc_w <= 0 or alloc_h <= 0:
            return

        cx, cy = alloc_w / 2, alloc_h / 2
        dx, dy = x - cx, y - cy
        dist   = math.hypot(dx, dy)
        mode   = self.bm.mode()

        if mode not in ("attack", "run") and dist <= ATTACK_THRESHOLD:
            if dx >= 15:
                self.facing = 1
            elif dx <= -15:
                self.facing = -1
            self.bm.switch("attack")
            self._load_behavior()

        elif mode == "attack" and dist > ATTACK_THRESHOLD:
            self.bm.switch("walk")
            self._load_behavior()


    def _on_close_request(self, *args):
        if self._dying:
            return False
        self._dying = True

        for tid in ("_move_id", "_refresh_id"):
            if hasattr(self, tid):
                GLib.source_remove(getattr(self, tid))

        dead = os.path.abspath("assets/dead.gif")
        self.sprite = AnimatedSprite(dead, fps=12)
        self.picture.set_paintable(self.sprite.get_paintable())
        self._refresh_id = GLib.timeout_add(int(1000/12), self._refresh)

        GLib.timeout_add(DEATH_DURATION_MS,
                         lambda: (self._app.quit(), False))
        return True

def on_activate(app):
    if not hasattr(app, "win"):
        app.win = CatWindow(app)
    app.win.present()

if __name__ == "__main__":
    app = Gtk.Application()
    app.connect("activate", on_activate)
    app.run()