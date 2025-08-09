import os, ctypes
from ctypes import wintypes

if os.name == "nt":
    import gi
    gi.require_version('GdkWin32', '4.0')
    from gi.repository import GdkWin32
else:
    GdkWin32 = None

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
        self.hwnd = None
        self._styled = False
        self._last_err = 0
        self._hwnd_cache = 0

        if os.name == "nt":
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
        else:
            self.user32 = None
            self.kernel32 = None
            self.HWND_TOPMOST = None
            self.HWND_NOTOPMOST = None

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
            if GdkWin32 is not None and self.window is not None:
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
        if self.hwnd and self.user32.IsWindow(self.hwnd):
            return self.hwnd
        t = self.title or "Pixie"
        hwnd = self.user32.FindWindowW(None, t)
        if hwnd:
            self.hwnd = hwnd
        return self.hwnd

    def _apply_styles_once(self):
        if os.name != "nt":
            return
        if not self._find_hwnd():
            return
        if self._styled:
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
        if os.name != "nt":
            return
        if not self._find_hwnd():
            return
        self._apply_styles_once()
        ok = self.user32.SetWindowPos(
            self.hwnd, None, int(x), int(y), 0, 0,
            self.SWP_NOSIZE | self.SWP_NOZORDER | self.SWP_NOACTIVATE
        )
        self._last_err = 0 if ok else self.kernel32.GetLastError()

    def hide_from_taskbar(self):
        if os.name != "nt":
            return
        if not self._find_hwnd():
            return
        self._styled = False
        self._apply_styles_once()

    def always_on_top(self):
        if os.name != "nt":
            return False
        if not self._find_hwnd():
            return False
        self._apply_styles_once()
        ok = self.user32.SetWindowPos(
            self.hwnd, self.HWND_TOPMOST, 0, 0, 0, 0,
            self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE | self.SWP_SHOWWINDOW
        )
        self._last_err = 0 if ok else self.kernel32.GetLastError()
        return bool(ok)

    def assert_topmost(self):
        if os.name != "nt":
            try:
                self.window.set_keep_above(True)
                return True
            except Exception:
                return False
        hwnd = self._get_hwnd()
        if not hwnd:
            return False
        flags = self.SWP_NOMOVE | self.SWP_NOSIZE | self.SWP_NOACTIVATE
        ok = self.user32.SetWindowPos(hwnd, self.HWND_TOPMOST, 0, 0, 0, 0, flags)
        lasterr = ctypes.get_last_error()
        return bool(ok)

    def debug_report(self):
        if os.name != "nt":
            return "non-win32"
        ptr = ctypes.cast(self.hwnd, ctypes.c_void_p).value if self.hwnd else 0
        return f"hwnd=0x{ptr:X} lasterr={self._last_err}"