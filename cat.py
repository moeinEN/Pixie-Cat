import os, sys, signal, math, argparse, ctypes, ctypes.util, gi

lib = ctypes.util.find_library("gtk4-layer-shell")
if lib:
    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)

gi.require_version("Gtk4LayerShell", "1.0")
gi.require_version("Gtk",        "4.0")
gi.require_version("GdkPixbuf",  "2.0")
from gi.repository import (
    Gtk4LayerShell as ls,
    Gtk, Gdk, GdkPixbuf, GLib
)

from sprite           import AnimatedSprite
from behavior_manager import BehaviorManager
from pointer          import get_mouse_position

css = Gtk.CssProvider()
css.load_from_data(b"""
.transparent { background: transparent; }
""")
Gtk.StyleContext.add_provider_for_display(
    Gdk.Display.get_default(),
    css,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
)

DEATH_DURATION_MS = 500
ATTACK_THRESHOLD  = 64

def parse_color(hexstr):
    h = hexstr.lstrip('#')
    if len(h)!=6: raise ValueError("Color must be #RRGGBB")
    return tuple(int(h[i:i+2],16)/255.0 for i in (0,2,4))

class CatWindow(Gtk.ApplicationWindow):
    def __init__(self, app, speed, scale, color):
        super().__init__(application=app, title="Wayland-Cat")
        self._app   = app
        self._dying = False

        self.speed = max(0.01, speed)
        self.scale = max(0.01, scale)
        self.tint  = parse_color(color) if color else None

        self.add_css_class("transparent")
        self.set_decorated(False)
        self.set_resizable(False)

        ls.init_for_window(self)
        ls.set_layer(self, ls.Layer.OVERLAY)
        ls.set_keyboard_mode(self, ls.KeyboardMode.NONE)
        for e in (ls.Edge.TOP, ls.Edge.LEFT):
            ls.set_anchor(self, e, True)
            ls.set_margin(self, e, 0)

        disp     = Gdk.Display.get_default()
        monitors = disp.get_monitors()
        geom     = monitors[0].get_geometry()

        self.bm = BehaviorManager(geom.width, geom.height)

        self.pos_x   = geom.width/2
        self.pos_y   = geom.height/2
        self.facing  = 1
        self._mode   = None

        self.picture = Gtk.Picture.new_for_paintable(None)
        self.set_child(self.picture)

        click1 = Gtk.GestureClick.new()
        click1.set_button(1)
        click1.connect("pressed", lambda *_: self._trigger_run())
        self.picture.add_controller(click1)

        motion = Gtk.EventControllerMotion.new()
        motion.connect("motion", self._on_motion)
        motion.connect("leave",  self._on_pointer_leave)
        self.picture.add_controller(motion)

        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", self._on_scroll)
        self.picture.add_controller(scroll)

        self._is_happy       = False
        self._happy_timeout  = None

        self._load_behavior()

        self.connect("close-request", self._on_close_request)
        try:
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT,  self._on_close_request)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._on_close_request)
        except AttributeError:
            signal.signal(signal.SIGINT,  lambda *a: GLib.idle_add(self._on_close_request))
            signal.signal(signal.SIGTERM, lambda *a: GLib.idle_add(self._on_close_request))

    def tint_and_scale(self, pixbuf: GdkPixbuf.Pixbuf) -> GdkPixbuf.Pixbuf:
        if self.scale != 1.0:
            new_w = int(pixbuf.get_width()  * self.scale)
            new_h = int(pixbuf.get_height() * self.scale)
            pixbuf = pixbuf.scale_simple(new_w, new_h,
                                         GdkPixbuf.InterpType.BILINEAR)

        if self.tint:
            r_t, g_t, b_t = self.tint
            w, h        = pixbuf.get_width(), pixbuf.get_height()
            stride      = pixbuf.get_rowstride()
            nch         = pixbuf.get_n_channels()
            bps         = pixbuf.get_bits_per_sample()
            has_alpha   = pixbuf.get_has_alpha()
            cs          = pixbuf.get_colorspace()

            orig = pixbuf.get_pixels()
            data = bytearray(orig)

            for yy in range(h):
                row_start = yy * stride
                for xx in range(w):
                    idx = row_start + xx * nch
                    data[idx+0] = int(data[idx+0] * r_t)
                    data[idx+1] = int(data[idx+1] * g_t)
                    data[idx+2] = int(data[idx+2] * b_t)

            pixbuf = GdkPixbuf.Pixbuf.new_from_data(
                bytes(data),
                cs,
                has_alpha,
                bps,
                w, h,
                stride
            )

        return pixbuf

    def _load_behavior(self):
        for tid in ("_move_id","_refresh_id"):
            if hasattr(self,tid):
                GLib.source_remove(getattr(self,tid))

        asset    = self.bm.get_asset()
        fps      = self.bm.get_fps()
        interval = int(self.bm.get_move_interval()/self.speed)

        self.sprite      = AnimatedSprite(asset, fps=fps)
        self._refresh_id = GLib.timeout_add(int(1000/fps),    self._refresh)
        self._move_id    = GLib.timeout_add(interval,          self._move)
        self._mode       = self.bm.mode()

    def _refresh(self):
        pix = self.sprite.get_pixbuf()
        pix = self.tint_and_scale(pix.copy())
        if self.facing<0:
            pix = pix.flip(True)
        tex = Gdk.Texture.new_for_pixbuf(pix)
        self.picture.set_paintable(tex)
        return True

    def _move(self):
        nx, ny, f = self.bm.update(self.pos_x, self.pos_y)
        self.pos_x, self.pos_y = nx, ny
        self.facing           = f

        ls.set_margin(self, ls.Edge.LEFT, int(nx))
        ls.set_margin(self, ls.Edge.TOP,  int(ny))
        self.queue_resize()

        if self.bm.mode()!=self._mode:
            self._load_behavior()
        return True

    def _trigger_run(self):
        if self._dying or self.bm.mode()=="run":
            return
        self.bm.switch("run")
        self._load_behavior()

    def _trigger_attack(self, *_):
        if self._dying or self.bm.mode()=="attack":
            return
        self.bm.switch("attack")
        self._load_behavior()

    def _on_motion(self, controller, x, y):
        if self._dying or self.bm.mode() in ("run","happy"):
            return
        w,h = self.picture.get_allocated_width(), self.picture.get_allocated_height()
        if w<=0 or h<=0:
            return
        cx,cy = w/2,h/2
        dx,dy = x-cx, y-cy
        dist  = math.hypot(dx,dy)
        mode  = self.bm.mode()

        if mode not in ("attack","run","happy") and dist<=ATTACK_THRESHOLD:
            self.facing = 1 if dx>=15 else -1
            self.bm.switch("attack"); self._load_behavior()
        elif mode=="attack" and dist>ATTACK_THRESHOLD:
            self.bm.switch("walk"); self._load_behavior()

    def _on_pointer_leave(self, *_):
        if self._dying or self.bm.mode()!="attack":
            return
        self.bm.switch("walk"); self._load_behavior()

    def _on_scroll(self, controller, dx, dy):
        if self._dying or abs(dy)<0.1:
            return True
        happy = self.bm._behaviors["happy"]
        if self.bm.mode()=="happy":
            if self._happy_timeout:
                GLib.source_remove(self._happy_timeout)
            self._happy_timeout = GLib.timeout_add(happy.duration_ms, self._end_happy)
            return True
        self._happy_timeout = GLib.timeout_add(happy.duration_ms, self._end_happy)
        self.bm.switch("happy"); self._load_behavior()
        return True

    def _end_happy(self):
        if self.bm.mode()=="happy":
            self.bm.switch("walk"); self._load_behavior()
        self._happy_timeout = None
        return False

    def _on_close_request(self, *args):
        if self._dying:
            return False
        self._dying = True
        for tid in ("_move_id","_refresh_id"):
            if hasattr(self,tid):
                GLib.source_remove(getattr(self,tid))
        dead = os.path.abspath("assets/dead.gif")
        self.sprite = AnimatedSprite(dead, fps=12)
        self._refresh_id = GLib.timeout_add(int(1000/12), self._refresh)
        GLib.timeout_add(DEATH_DURATION_MS, lambda: (self._app.quit(),False))
        return True

def on_activate(app):
    cfg = getattr(app,"args",{})
    if not hasattr(app,"win"):
        app.win = CatWindow(app,
            speed=cfg.get("speed",1.0),
            scale=cfg.get("scale",1.0),
            color=cfg.get("color",None)
        )
    app.win.present()

if __name__=="__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--speed", type=float, default=1.0,
                   help="Movement speed multiplier")
    p.add_argument("--scale", type=float, default=1.0,
                   help="Sprite scale factor")
    p.add_argument("--color", type=str, default=None,
                   help="Hex tint color, e.g. '#FF00FF'")
    args = p.parse_args()

    app = Gtk.Application()
    app.args = vars(args)
    app.connect("activate", on_activate)
    app.run(None)