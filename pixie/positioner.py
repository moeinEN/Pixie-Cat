import os, ctypes
from ctypes import wintypes

if os.name == "nt":
    import gi
    gi.require_version("GdkWin32", "4.0")
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
        self._xid = 0
        self._xdisplay_ptr = None
        self._libX11 = None
        self._atoms = {}
        self._x11_state_applied = False

        if os.name == "nt":
            self.hwnd = None
            self._styled = False
            self._hwnd_cache = 0
            self.user32 = ctypes.windll.user32
            self.kernel32 = ctypes.windll.kernel32
            self.user32.SetWindowPos.restype = wintypes.BOOL
            self.user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
            self.user32.FindWindowW.restype = wintypes.HWND
            self.user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
            self.user32.IsWindow.restype = wintypes.BOOL
            self.user32.IsWindow.argtypes = [wintypes.HWND]
            self.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.GetWindowLongPtrW.restype = ctypes.c_longlong
            self.user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.SetWindowLongPtrW.restype = ctypes.c_longlong
            self.user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
            mask = (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)) - 1
            self.HWND_TOPMOST = ctypes.c_void_p((-1) & mask)
            self.HWND_NOTOPMOST = ctypes.c_void_p((-2) & mask)
            return

        import gi
        gi.require_version("Gdk", "4.0"); gi.require_version("Gtk", "4.0")
        from gi.repository import Gdk

        st = os.environ.get("XDG_SESSION_TYPE", "").lower()
        be = os.environ.get("GDK_BACKEND", "").lower()
        try:
            disp = Gdk.Display.get_default()
            disp_name = type(disp).__name__.lower()
        except Exception:
            disp = None
            disp_name = ""

        if ("x11" in st) or ("x11" in be) or ("x11" in disp_name):
            self._backend = "x11"
        elif ("wayland" in st) or ("wayland" in be) or ("wayland" in disp_name):
            self._backend = "wayland"
        else:
            self._backend = "x11" if "x11" in be else ("wayland" if "wayland" in be else "unknown")

        print(f"[pos] detect st='{st}' be='{be}' disp='{disp_name}'")
        print(f"[pos] backend selection => {self._backend}")

        self.LayerShell = None
        self._disp_obj = disp
        self._Gdk = Gdk
        self._GdkX11 = None

        if self._backend == "wayland":
            try:
                gi.require_version("Gtk4LayerShell", "1.0")
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
                        self.LayerShell.set_keyboard_mode(self.window, self.LayerShell.KeyboardMode.NONE)
                        print("[pos] layer-shell set_keyboard_mode -> NONE")
                    elif hasattr(self.LayerShell, "set_keyboard_interactivity"):
                        self.LayerShell.set_keyboard_interactivity(self.window, False)
                        print("[pos] layer-shell set_keyboard_interactivity -> False")
                    if hasattr(self.LayerShell, "set_exclusive_zone"):
                        self.LayerShell.set_exclusive_zone(self.window, 0)
                    self.LayerShell.set_anchor(self.window, self.LayerShell.Edge.LEFT, True)
                    self.LayerShell.set_anchor(self.window, self.LayerShell.Edge.TOP, True)
                    self.LayerShell.set_anchor(self.window, self.LayerShell.Edge.RIGHT, False)
                    self.LayerShell.set_anchor(self.window, self.LayerShell.Edge.BOTTOM, False)
                    self._wl_active = True
                    print("[pos] layer-shell setup OK")
                except Exception as e:
                    self._wl_active = False
                    print(f"[pos] layer-shell setup failed: {e!r}")
            return

        try:
            gi.require_version("GdkX11", "4.0")
            from gi.repository import GdkX11
            self._GdkX11 = GdkX11
        except Exception:
            self._GdkX11 = None

        try:
            self._libX11 = ctypes.CDLL("libX11.so.6")
            self._libX11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            self._libX11.XOpenDisplay.restype = ctypes.c_void_p
            self._libX11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
            self._libX11.XDefaultRootWindow.restype = ctypes.c_ulong
            self._libX11.XMoveWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int]
            self._libX11.XRaiseWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            self._libX11.XFlush.argtypes = [ctypes.c_void_p]
            self._libX11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_bool]
            self._libX11.XInternAtom.restype = ctypes.c_ulong
            self._libX11.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
            self._libX11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_bool, ctypes.c_long, ctypes.c_void_p]
            self._libX11.XSendEvent.restype = ctypes.c_int
        except Exception:
            self._libX11 = None

    def _ensure_x11_bound(self):
        if self._x11_ready or self._wl_active or os.name == "nt":
            return
        if not self.window:
            return
        surf = None
        try:
            surf = self.window.get_surface()
        except Exception:
            surf = None
        if not surf:
            return
        xid = 0
        if self._GdkX11:
            try:
                xid = int(self._GdkX11.X11Surface.get_xid(surf))
            except Exception:
                xid = 0
        if not xid:
            return
        xdisp = None
        if self._libX11:
            try:
                xdisp = self._libX11.XOpenDisplay(None)
            except Exception:
                xdisp = None
        if not xdisp:
            return
        try:
            self._xid = xid
            self._xdisplay_ptr = ctypes.c_void_p(int(xdisp))
            self._x11_ready = True
            print(f"[pos] x11 ready xid=0x{int(self._xid):X}")
        except Exception:
            self._x11_ready = False

    def _atom(self, name):
        if not self._libX11 or not self._xdisplay_ptr:
            return 0
        a = self._atoms.get(name)
        if a:
            return a
        a = self._libX11.XInternAtom(self._xdisplay_ptr, name.encode("utf-8"), False)
        self._atoms[name] = a
        return a

    def _x11_apply_above(self):
        if not self._x11_ready or not self._libX11:
            return False
        nstate = self._atom("_NET_WM_STATE")
        s_above = self._atom("_NET_WM_STATE_ABOVE")
        if not (nstate and s_above):
            return False
        arr = (ctypes.c_ulong * 1)()
        arr[0] = s_above
        self._libX11.XChangeProperty(self._xdisplay_ptr, ctypes.c_ulong(self._xid), nstate, self._atom("ATOM"), 32, 0, ctypes.cast(ctypes.pointer(arr), ctypes.c_void_p), 1)
        root = self._libX11.XDefaultRootWindow(self._xdisplay_ptr)
        data = (ctypes.c_long * 5)()
        data[0] = 1
        data[1] = ctypes.c_long(s_above).value
        data[2] = 0
        data[3] = 0
        data[4] = 0
        class XClientMessageEvent(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_int),
                ("serial", ctypes.c_ulong),
                ("send_event", ctypes.c_int),
                ("display", ctypes.c_void_p),
                ("window", ctypes.c_ulong),
                ("message_type", ctypes.c_ulong),
                ("format", ctypes.c_int),
                ("data", ctypes.c_long * 5),
            ]
        ev = XClientMessageEvent()
        ev.type = 33
        ev.serial = 0
        ev.send_event = 1
        ev.display = self._xdisplay_ptr
        ev.window = ctypes.c_ulong(self._xid).value
        ev.message_type = ctypes.c_ulong(nstate).value
        ev.format = 32
        ev.data = data
        SubstructureRedirectMask = 0x00100000
        SubstructureNotifyMask = 0x00080000
        mask = SubstructureRedirectMask | SubstructureNotifyMask
        self._libX11.XSendEvent(self._xdisplay_ptr, ctypes.c_ulong(root), False, ctypes.c_long(mask), ctypes.byref(ev))
        self._libX11.XFlush(self._xdisplay_ptr)
        return True

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
        self.user32.SetWindowPos(self.hwnd, None, 0, 0, 0, 0, self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOZORDER | self.SWP_FRAMECHANGED)
        self._styled = True

    def set_position(self, x, y):
        if os.name == "nt":
            if not self._find_hwnd():
                return
            self._apply_styles_once()
            ok = self.user32.SetWindowPos(self.hwnd, None, int(x), int(y), 0, 0, self.SWP_NOSIZE | self.SWP_NOZORDER | self.SWP_NOACTIVATE)
            self._last_err = 0 if ok else self.kernel32.GetLastError()
            return
        if self._wl_active and self.LayerShell and self.window:
            try:
                self.LayerShell.set_margin(self.window, self.LayerShell.Edge.LEFT, int(x))
                self.LayerShell.set_margin(self.window, self.LayerShell.Edge.TOP, int(y))
                try:
                    self.window.queue_allocate()
                except Exception:
                    pass
                print(f"[pos] wl move -> x={int(x)} y={int(y)}")
            except Exception as e:
                print(f"[pos] wl move failed: {e!r}")
            return
        self._ensure_x11_bound()
        if self._x11_ready and self._libX11:
            try:
                self._libX11.XMoveWindow(self._xdisplay_ptr, ctypes.c_ulong(self._xid), int(x), int(y))
                self._libX11.XFlush(self._xdisplay_ptr)
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
            ok = self.user32.SetWindowPos(self.hwnd, self.HWND_TOPMOST, 0, 0, 0, 0, self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE | self.SWP_SHOWWINDOW)
            self._last_err = 0 if ok else self.kernel32.GetLastError()
            return bool(ok)
        if self._wl_active:
            return True
        self._ensure_x11_bound()
        if self._x11_ready and self._libX11:
            try:
                self._libX11.XRaiseWindow(self._xdisplay_ptr, ctypes.c_ulong(self._xid))
                if not self._x11_state_applied:
                    self._x11_state_applied = self._x11_apply_above()
                self._libX11.XFlush(self._xdisplay_ptr)
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
        self._ensure_x11_bound()
        if self._x11_ready and self._libX11:
            try:
                self._libX11.XRaiseWindow(self._xdisplay_ptr, ctypes.c_ulong(self._xid))
                if not self._x11_state_applied:
                    self._x11_state_applied = self._x11_apply_above()
                self._libX11.XFlush(self._xdisplay_ptr)
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