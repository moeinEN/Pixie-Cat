import os, sys, signal, math, argparse, ctypes, ctypes.util, gi
from importlib import resources
from .tray import Tray
from pixie.debug import debug_print

def resolve_asset_path(path: str) -> str:
    if os.path.isabs(path) and os.path.exists(path):
        return path
    try:
        rel = path if path.startswith("assets/") else f"assets/{path}"
        return str(resources.files("pixie").joinpath(rel))
    except Exception:
        return path

def resolve_tray_icon():
    cands = [
        resolve_asset_path("assets/icon.ico"),
        resolve_asset_path("assets/icon.png"),
        resolve_asset_path("assets/tray.png"),
        resolve_asset_path("assets/happy.png"),
    ]
    for p in cands:
        if p and os.path.isfile(p):
            debug_print(f"[app] tray icon resolved: {p}")
            return p
    debug_print("[app] no tray icon file found, will use default")
    return None

lib = ctypes.util.find_library("gtk4-layer-shell")
if lib:
    try:
        ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
    except Exception:
        pass

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from .sprite import AnimatedSprite
from .behavior_manager import BehaviorManager
from .positioner import Positioner

def _install_css_for_display(display: Gdk.Display):
    css = Gtk.CssProvider()
    rule = ".transparent { background: transparent; }"
    try:
        css.load_from_data(rule, len(rule))
    except TypeError:
        css.load_from_data(rule)
    Gtk.StyleContext.add_provider_for_display(
        display, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

DEATH_DURATION_MS = 500
ATTACK_THRESHOLD  = 64

def parse_color(hexstr):
    h = hexstr.lstrip('#')
    if len(h)!=6: raise ValueError("Color must be #RRGGBB")
    return tuple(int(h[i:i+2],16)/255.0 for i in (0,2,4))

class CatWindow(Gtk.ApplicationWindow):
    def __init__(self, app, speed, scale, color):
        super().__init__(application=app, title="Pixie")
        _install_css_for_display(self.get_display())
        self._app   = app
        self._dying = False
        self.total_steps = 0
        self.speed = max(0.01, speed)
        self.scale = max(0.01, scale)
        self.tint  = parse_color(color) if color else None
        self.add_css_class("transparent")
        self.set_decorated(False)
        self.set_resizable(False)
        

        disp     = Gdk.Display.get_default()
        monitors = disp.get_monitors()
        mon0 = monitors.get_item(0) if hasattr(monitors, "get_item") else monitors[0]
        geom = mon0.get_geometry()

        self.bm = BehaviorManager(geom.width, geom.height, scale=self.scale)

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

        self._happy_timeout = None

        self.pos = Positioner(self)

        def _after_map(*_):
            try:
                self.pos.hide_from_taskbar()
                self.set_keep_above(True)
            except Exception:
                pass
            GLib.timeout_add(200, self._assert_topmost)
            debug_print("[map] hide_from_taskbar done")
            return False

        self.connect("map", _after_map)

        self._load_behavior()

        self.connect("close-request", self._on_close_request)
        try:
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT,  self._on_close_request)
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._on_close_request)
        except AttributeError:
            signal.signal(signal.SIGINT,  lambda *a: GLib.idle_add(self._on_close_request))
            signal.signal(signal.SIGTERM, lambda *a: GLib.idle_add(self._on_close_request))

    def _assert_topmost(self):
        keep_above_ok = False
        try:
            self.set_keep_above(True)
            keep_above_ok = True
        except Exception:
            pass
        pos_ok = False
        try:
            pos_ok = bool(self.pos.always_on_top())
        except Exception:
            pass
        debug_print(f"[top] tick asserted topmost: pos={pos_ok} keep_above={keep_above_ok} {self.pos.debug_report()}")
        GLib.timeout_add(1500, self._assert_topmost)
        return False

    def tint_and_scale(self, pixbuf: GdkPixbuf.Pixbuf) -> GdkPixbuf.Pixbuf:
        if self.scale != 1.0:
            new_w = int(pixbuf.get_width()  * self.scale)
            new_h = int(pixbuf.get_height() * self.scale)
            pixbuf = pixbuf.scale_simple(new_w, new_h, GdkPixbuf.InterpType.BILINEAR)
        if self.tint:
            r_t, g_t, b_t = self.tint
            w, h      = pixbuf.get_width(), pixbuf.get_height()
            stride    = pixbuf.get_rowstride()
            nch       = pixbuf.get_n_channels()
            bps       = pixbuf.get_bits_per_sample()
            has_alpha = pixbuf.get_has_alpha()
            cs        = pixbuf.get_colorspace()
            data = bytearray(pixbuf.get_pixels())
            for yy in range(h):
                row_start = yy * stride
                for xx in range(w):
                    idx = row_start + xx * nch
                    data[idx+0] = int(data[idx+0] * r_t)
                    data[idx+1] = int(data[idx+1] * g_t)
                    data[idx+2] = int(data[idx+2] * b_t)
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(bytes(data), cs, has_alpha, bps, w, h, stride)
        return pixbuf

    def _load_behavior(self):
        for tid in ("_move_id", "_refresh_id"):
            if hasattr(self, tid):
                GLib.source_remove(getattr(self, tid))
        asset = resolve_asset_path(self.bm.get_asset())
        fps      = self.bm.get_fps()
        interval = int(self.bm.get_move_interval() / self.speed)
        self.sprite = AnimatedSprite(asset, fps=fps)
        first = self.sprite.get_pixbuf()
        first = self.tint_and_scale(first.copy())
        if self.facing < 0:
            first = first.flip(True)
        sw, sh = first.get_width(), first.get_height()
        self.set_default_size(sw, sh)
        self.picture.set_size_request(sw, sh)
        self.picture.set_paintable(Gdk.Texture.new_for_pixbuf(first))
        self._refresh_id = GLib.timeout_add(int(1000 / fps), self._refresh)
        self._move_id    = GLib.timeout_add(interval,        self._move)
        self._mode       = self.bm.mode()

    def _refresh(self):
        pix = self.sprite.get_pixbuf()
        pix = self.tint_and_scale(pix.copy())
        if self.facing < 0:
            pix = pix.flip(True)
        tex = Gdk.Texture.new_for_pixbuf(pix)
        self.picture.set_paintable(tex)
        return True

    def _move(self):
        prev_x, prev_y = self.pos_x, self.pos_y
        nx, ny, f = self.bm.update(self.pos_x, self.pos_y)
        moved = math.hypot(nx - prev_x, ny - prev_y)
        self.total_steps += int(moved)
        self.pos_x, self.pos_y = nx, ny
        self.facing = f
        try:
            self.pos.set_position(nx, ny)
        except Exception:
            pass
        self.queue_resize()
        if self.bm.mode() != self._mode:
            self._load_behavior()
        return True

    def _trigger_run(self):
        if self._dying or self.bm.mode() == "run":
            return
        self.bm.switch("run")
        self._load_behavior()

    def _trigger_attack(self, *_):
        if self._dying or self.bm.mode() == "attack":
            return
        self.bm.switch("attack")
        self._load_behavior()

    def _on_motion(self, controller, x, y):
        if self._dying or self.bm.mode() in ("run", "happy"):
            return
        w = self.picture.get_allocated_width()
        h = self.picture.get_allocated_height()
        if w <= 0 or h <= 0:
            return
        cx, cy = w / 2, h / 2
        dx, dy = x - cx, y - cy
        dist   = math.hypot(dx, dy)
        threshold = ATTACK_THRESHOLD * self.scale
        deadzone  = 15 * self.scale
        mode = self.bm.mode()
        if mode not in ("attack", "run", "happy") and dist <= threshold:
            if dx >=  deadzone:
                self.facing = 1
            elif dx <= -deadzone:
                self.facing = -1
            self.bm.switch("attack"); self._load_behavior()
        elif mode == "attack" and dist > threshold:
            self.bm.switch("walk"); self._load_behavior()

    def _on_pointer_leave(self, *_):
        if self._dying or self.bm.mode() != "attack":
            return
        self.bm.switch("walk"); self._load_behavior()

    def _on_scroll(self, controller, dx, dy):
        if self._dying or abs(dy) < 0.1:
            return True
        happy = self.bm._behaviors["happy"]
        if self.bm.mode() == "happy":
            if self._happy_timeout:
                GLib.source_remove(self._happy_timeout)
            self._happy_timeout = GLib.timeout_add(happy.duration_ms, self._end_happy)
            return True
        self._happy_timeout = GLib.timeout_add(happy.duration_ms, self._end_happy)
        self.bm.switch("happy"); self._load_behavior()
        return True

    def _end_happy(self):
        if self.bm.mode() == "happy":
            self.bm.switch("walk"); self._load_behavior()
        self._happy_timeout = None
        return False

    def _request_quit(self):
        GLib.idle_add(self._on_close_request)

    def _on_close_request(self, *args):
        if self._dying:
            return False
        self._dying = True
        for tid in ("_move_id","_refresh_id"):
            if hasattr(self,tid):
                GLib.source_remove(getattr(self,tid))
        dead = resolve_asset_path("assets/dead.gif")
        self.sprite = AnimatedSprite(dead, fps=12)
        self._refresh_id = GLib.timeout_add(int(1000/12), self._refresh)
        GLib.timeout_add(DEATH_DURATION_MS, lambda: (self.get_application().quit(), False))
        return True

def assert_top_tick(app):
    try:
        if not getattr(app, "win", None):
            return True
        pos = getattr(app.win, "pos", None)
        if not pos or not hasattr(pos, "assert_topmost"):
            return True
        ok = pos.assert_topmost()
        keep = False
        try:
            keep = bool(app.win.get_keep_above())
        except Exception:
            pass
        debug_print(f"[top] tick asserted topmost: pos={bool(ok)} keep_above={keep} {pos.debug_report()}")
    except Exception as e:
        debug_print(f"[top] tick error: {e!r}")
    return True

def on_activate(app):
    cfg = getattr(app, "args", {})
    if not hasattr(app, "win"):
        app.win = CatWindow(
            app,
            speed=cfg.get("speed", 1.0),
            scale=cfg.get("scale", 1.0),
            color=cfg.get("color", None),
        )
    app.win.present()
    try:
        app.hold()
        debug_print("[app] application hold")
    except Exception as e:
        debug_print("[app] app.hold not available:", repr(e))
    try:
        icon_path = resolve_tray_icon()
        def quit_app():
            GLib.idle_add(app.win._on_close_request)
        app.tray = Tray("Pixie", icon_path, on_quit=quit_app)
        ok = app.tray.start()
        debug_print(f"[app] tray started = {bool(ok)}")
    except Exception as e:
        debug_print("[app] tray init failed:", repr(e))

    debug_print("[pos]", app.win.pos.debug_report())
    GLib.timeout_add(1000, lambda: assert_top_tick(app))

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--color", type=str, default=None)
    args = p.parse_args(argv)
    app = Gtk.Application()
    app.args = vars(args)
    app.connect("activate", on_activate)
    app.run(None)

if __name__ == "__main__":
    main()