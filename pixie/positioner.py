import os, ctypes
from ctypes import wintypes

if os.name == "nt":
    import gi
    gi.require_version('GdkWin32', '4.0')
    from gi.repository import GdkWin32

class Positioner:
    GWL_EXSTYLE = -20
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_NOACTIVATE = 0x08000000

    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW = 0x0040

    def __init__(self, window=None, title=None):
        self.window = window
        self.title = title or (window.get_title() if window else "Pixie")
        self._last_err = 0

        self._backend = "win32" if os.name == "nt" else "unknown"
        self._wl_active = False
        self._x11_ready = False

        if os.name == "nt":
            self.hwnd = None
            self._styled = False
            self._hwnd_cache = 0

            self.user32 = ctypes.windll.user32
            self.kernel32 = ctypes.windll.kernel32

            self.user32.SetWindowPos.restype = wintypes.BOOL
            self.user32.SetWindowPos.argtypes = [
                wintypes.HWND, wintypes.HWND,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_uint
            ]
            self.user32.FindWindowW.restype = wintypes.HWND
            self.user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
            self.user32.IsWindow.restype = wintypes.BOOL
            self.user32.IsWindow.argtypes = [wintypes.HWND]
            self.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.GetWindowLongPtrW.restype = ctypes.c_longlong
            self.user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.SetWindowLongPtrW.restype = ctypes.c_longlong
            self.user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
            self.kernel32.GetLastError.restype = wintypes.DWORD

            mask = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
            self.HWND_TOPMOST = ctypes.c_void_p((-1) & mask)
            self.HWND_NOTOPMOST = ctypes.c_void_p((-2) & mask)
            return

        import gi
        gi.require_version('Gdk', '4.0'); gi.require_version('Gtk', '4.0')
        from gi.repository import Gdk, Gtk

        st = os.environ.get('XDG_SESSION_TYPE', '').lower()
        be = os.environ.get('GDK_BACKEND', '').lower()
        try:
            disp = Gdk.Display.get_default()
            disp_name = type(disp).__name__.lower()
        except Exception:
            disp_name = ''

        if 'wayland' in (st or be or disp_name):
            self._backend = 'wayland'
        elif 'x11' in (st or be or disp_name):
            self._backend = 'x11'
        else:
            self._backend = 'unknown'

        print(f"[pos] detect st='{st}' be='{be}' disp='{disp_name}'")
        print(f"[pos] backend selection => {self._backend}")

        self.LayerShell = None
        if self._backend == 'wayland':
            try:
                gi.require_version('Gtk4LayerShell', '1.0')
                from gi.repository import Gtk4LayerShell as LayerShell
                self.LayerShell = LayerShell
                print("[pos] Gtk4LayerShell introspection OK")
            except Exception as e:
                self.LayerShell = None
                print(f"[pos] Gtk4LayerShell import failed: {e!r}")

            if self.LayerShell and self.window is not None:
                try:
                    self.LayerShell.init_for_window(self.window)
                    self.LayerShell.set_layer(self.window, self.LayerShell.Layer.TOP)

                    if hasattr(self.LayerShell, "set_keyboard_mode"):
                        self.LayerShell.set_keyboard_mode(
                            self.window, self.LayerShell.KeyboardMode.NONE
                        )
                        print("[pos] layer-shell set_keyboard_mode -> NONE")
                    elif hasattr(self.LayerShell, "set_keyboard_interactivity"):
                        self.LayerShell.set_keyboard_interactivity(self.window, False)
                        print("[pos] layer-shell set_keyboard_interactivity -> False")
                    else:
                        print("[pos] WARNING: no keyboard API found on Gtk4LayerShell")

                    if hasattr(self.LayerShell, "set_exclusive_zone"):
                        self.LayerShell.set_exclusive_zone(self.window, 0)

                    self.LayerShell.set_anchor(self.window, self.LayerShell.Edge.LEFT, True)
                    self.LayerShell.set_anchor(self.window, self.LayerShell.Edge.TOP,  True)
                    self.LayerShell.set_anchor(self.window, self.LayerShell.Edge.RIGHT, False)
                    self.LayerShell.set_anchor(self.window, self.LayerShell.Edge.BOTTOM, False)

                    self._wl_active = True
                    print("[pos] layer-shell setup OK")
                except Exception as e:
                    self._wl_active = False
                    print(f"[pos] layer-shell setup failed: {e!r}")

        self._xdisplay = None
        self._xid = 0
        if self._backend == 'x11' and not self._wl_active:
            try:
                gi.require_version('GdkX11', '4.0')
                from gi.repository import GdkX11
                self.GdkX11 = GdkX11
            except Exception:
                self.GdkX11 = None

            try:
                from Xlib import display as Xdisplay, X
                self.Xdisplay = Xdisplay
                self.X = X
            except Exception:
                self.Xdisplay = None
                self.X = None

            if self.GdkX11 and self.Xdisplay and self.window is not None:
                try:
                    surf = self.window.get_surface()
                    if surf is not None:
                        self._xid = self.GdkX11.X11Surface.get_xid(surf)
                        self._xdisplay = self.Xdisplay.Display()
                        self._x11_ready = bool(self._xdisplay and self._xid)
                except Exception:
                    self._x11_ready = False

    def _get_hwnd(self):
        if os.name != "nt":
            return 0
        try:
            if self._hwnd_cache:
                try:
                    import win32gui
                    if win32gui.IsWindow(self._hwnd_cache):
                        return self._hwnd_cache
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if 'GdkWin32' in globals() and self.window is not None:
                surf = None
                try:
                    surf = self.window.get_surface()
                except Exception:
                    pass
                get_handle = getattr(GdkWin32, "surface_get_handle", None)
                if surf and get_handle:
                    try:
                        hwnd = int(get_handle(surf))
                        if hwnd:
                            self._hwnd_cache = hwnd
                            return hwnd
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            import win32gui, win32process
            pid = os.getpid()
            found = [0]
            def _enum_cb(h, _):
                try:
                    if not win32gui.IsWindow(h):
                        return
                    _pid = win32process.GetWindowThreadProcessId(h)[1]
                    if _pid != pid:
                        return
                    title = win32gui.GetWindowText(h) or ""
                    if title.strip() != "":
                        found[0] = h
                except Exception:
                    pass
            win32gui.EnumWindows(_enum_cb, None)
            if found[0]:
                self._hwnd_cache = found[0]
                return found[0]
        except Exception:
            pass
        return 0

    def _find_hwnd(self):
        if os.name != "nt":
            return None
        if getattr(self, "hwnd", None) and self.user32.IsWindow(self.hwnd):
            return self.hwnd
        t = self.title or "Pixie"
        hwnd = self.user32.FindWindowW(None, t)
        if hwnd:
            self.hwnd = hwnd
        return getattr(self, "hwnd", None)

    def _apply_styles_once(self):
        if os.name != "nt":
            return
        if not self._find_hwnd():
            return
        if getattr(self, "_styled", False):
            return
        ex = self.user32.GetWindowLongPtrW(self.hwnd, self.GWL_EXSTYLE)
        ex = (ex | self.WS_EX_TOOLWINDOW | self.WS_EX_NOACTIVATE) & ~self.WS_EX_APPWINDOW
        self.user32.SetWindowLongPtrW(self.hwnd, self.GWL_EXSTYLE, ex)
        self.user32.SetWindowPos(
            self.hwnd, None, 0, 0, 0, 0,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOZORDER | self.SWP_FRAMECHANGED
        )
        self._styled = True

    def set_position(self, x, y):
        if os.name == "nt":
            if not self._find_hwnd():
                return
            self._apply_styles_once()
            ok = self.user32.SetWindowPos(
                self.hwnd, None, int(x), int(y), 0, 0,
                self.SWP_NOSIZE | self.SWP_NOZORDER | self.SWP_NOACTIVATE
            )
            self._last_err = 0 if ok else self.kernel32.GetLastError()
            return

        if self._wl_active and self.LayerShell and self.window:
            try:
                self.LayerShell.set_margin(self.window, self.LayerShell.Edge.LEFT, int(x))
                self.LayerShell.set_margin(self.window, self.LayerShell.Edge.TOP,  int(y))
                try:
                    self.window.queue_allocate()
                except Exception:
                    pass
                print(f"[pos] wl move -> x={int(x)} y={int(y)}")
            except Exception as e:
                print(f"[pos] wl move failed: {e!r}")
            return

        if self._x11_ready:
            try:
                w = self._xdisplay.create_resource_object('window', int(self._xid))
                w.configure(x=int(x), y=int(y))
                self._xdisplay.sync()
            except Exception:
                pass

    def hide_from_taskbar(self):
        if os.name == "nt":
            if not self._find_hwnd():
                return
            self._styled = False
            self._apply_styles_once()
            return

    def always_on_top(self):
        if os.name == "nt":
            if not self._find_hwnd():
                return False
            self._apply_styles_once()
            ok = self.user32.SetWindowPos(
                self.hwnd, self.HWND_TOPMOST, 0, 0, 0, 0,
                self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE | self.SWP_SHOWWINDOW
            )
            self._last_err = 0 if ok else self.kernel32.GetLastError()
            return bool(ok)

        if self._wl_active:
            return True

        if self._x11_ready:
            try:
                w = self._xdisplay.create_resource_object('window', int(self._xid))
                w.configure(stack_mode=self.X.Above)
                self._xdisplay.sync()
                return True
            except Exception:
                return False

        return False

    def assert_topmost(self):
        if os.name == "nt":
            hwnd = self._get_hwnd()
            if not hwnd:
                return False
            flags = self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE
            ok = self.user32.SetWindowPos(hwnd, self.HWND_TOPMOST, 0, 0, 0, 0, flags)
            return bool(ok)

        if self._wl_active:
            return True
        if self._x11_ready:
            try:
                w = self._xdisplay.create_resource_object('window', int(self._xid))
                w.configure(stack_mode=self.X.Above)
                self._xdisplay.sync()
                return True
            except Exception:
                return False
        return False

    def debug_report(self):
        if os.name == "nt":
            ptr = ctypes.cast(getattr(self, "hwnd", None), ctypes.c_void_p).value if getattr(self, "hwnd", None) else 0
            return f"hwnd=0x{ptr:X} lasterr={self._last_err}"
        if self._wl_active:
            return "backend=wayland layer-shell=on"
        if self._backend == "wayland" and not self._wl_active:
            return "backend=wayland layer-shell=OFF"
        if self._x11_ready:
            return f"backend=x11 xid=0x{int(self._xid):X}"
        return f"backend={self._backend}"