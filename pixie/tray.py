import os
import threading
import ctypes
from ctypes import wintypes
from pixie.debug import debug_print

class Tray:
    def __init__(self, title: str, icon_path: str | None, on_quit):
        self.title = title or "Pixie"
        self.icon_path = icon_path
        self.on_quit = on_quit
        self._thread = None
        self._running = False

        self._mode = None
        try:
            import win32api, win32con, win32gui
            self._mode = "pywin32"
        except Exception:
            self._mode = "ctypes"

    def start(self) -> bool:
        try:
            debug_print(f"[tray] start backend={self._mode}")
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            debug_print(f"[tray] start failed: {e!r}")
            return False

    def stop(self):
        try:
            if self._mode == "pywin32":
                import win32gui, win32con
                if hasattr(self, "_hwnd") and self._hwnd:
                    win32gui.PostMessage(self._hwnd, win32con.WM_CLOSE, 0, 0)
            else:
                if hasattr(self, "_hwnd") and self._hwnd:
                    ctypes.windll.user32.PostMessageW(self._hwnd, 0x0010, 0, 0)
        except Exception as e:
            debug_print(f"[tray] stop error: {e!r}")

    def _run(self):
        try:
            if os.name == "nt":
                debug_print("[tray] start backend=ctypes")
                self._run_ctypes()
            else:
                debug_print("[tray] tray disabled on non-Windows; skipping")
        finally:
            self._running = False

    def _run_pywin32(self):
        import win32api, win32con, win32gui
        WM_USER = 0x0400
        WM_TRAY = WM_USER + 1
        ID_TRAY_QUIT = 1001

        class_name = "PixieTrayWin32"

        def wndproc(hWnd, msg, wParam, lParam):
            if msg == win32con.WM_DESTROY:
                nid = (hWnd, 1)
                try:
                    win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
                except Exception:
                    pass
                win32gui.PostQuitMessage(0)
                return 0
            if msg == win32con.WM_COMMAND and wParam == ID_TRAY_QUIT:
                try:
                    if callable(self.on_quit):
                        self.on_quit()
                except Exception as e:
                    debug_print(f"[tray] on_quit error: {e!r}")
                return 0
            if msg == WM_TRAY and lParam == win32con.WM_RBUTTONUP:
                menu = win32gui.CreatePopupMenu()
                win32gui.AppendMenu(menu, win32con.MF_STRING, ID_TRAY_QUIT, "Quit")
                x, y = win32gui.GetCursorPos()
                win32gui.SetForegroundWindow(hWnd)
                win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, x, y, 0, hWnd, None)
                win32gui.DestroyMenu(menu)
                return 0
            return win32gui.DefWindowProc(hWnd, msg, wParam, lParam)

        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = class_name
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.lpfnWndProc = wndproc
        atom = win32gui.RegisterClass(wc)

        hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_TOOLWINDOW,
            atom,
            self.title,
            win32con.WS_OVERLAPPED,
            0, 0, 0, 0, 0, 0, wc.hInstance, None
        )
        self._hwnd = hwnd

        hicon = None
        if self.icon_path and os.path.isfile(self.icon_path):
            try:
                hicon = win32gui.LoadImage(
                    0, self.icon_path, win32con.IMAGE_ICON, 0, 0,
                    win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
                )
                debug_print("[tray] pywin32: loaded .ico")
            except Exception as e:
                debug_print(f"[tray] pywin32: LoadImage failed: {e!r}")
        if not hicon:
            hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
            debug_print("[tray] pywin32: using default icon")

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (hwnd, 1, flags, WM_TRAY, hicon, self.title[:127])
        try:
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        except Exception as e:
            debug_print(f"[tray] pywin32: NIM_ADD failed: {e!r}")
            return

        try:
            win32gui.PumpMessages()
        finally:
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 1))
            except Exception:
                pass
            try:
                win32gui.DestroyWindow(hwnd)
            except Exception:
                pass

    def _run_ctypes(self):
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        kernel32 = ctypes.windll.kernel32

        WM_DESTROY = 0x0002
        WM_COMMAND = 0x0111
        WM_USER = 0x0400
        WM_TRAY = WM_USER + 1
        WM_RBUTTONUP = 0x0205
        NIF_MESSAGE = 0x00000001
        NIF_ICON = 0x00000002
        NIF_TIP = 0x00000004
        NIM_ADD = 0x00000000
        NIM_DELETE = 0x00000002
        ID_TRAY_QUIT = 102

        WNDPROCTYPE = ctypes.WINFUNCTYPE(
            wintypes.LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
        )

        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROCTYPE),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HCURSOR),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("hWnd", wintypes.HWND),
                ("uID", wintypes.UINT),
                ("uFlags", wintypes.UINT),
                ("uCallbackMessage", wintypes.UINT),
                ("hIcon", wintypes.HICON),
                ("szTip", wintypes.WCHAR * 128),
                ("dwState", wintypes.DWORD),
                ("dwStateMask", wintypes.DWORD),
                ("szInfo", wintypes.WCHAR * 256),
                ("uTimeoutOrVersion", wintypes.UINT),
                ("szInfoTitle", wintypes.WCHAR * 64),
                ("dwInfoFlags", wintypes.DWORD),
                ("guidItem", ctypes.c_byte * 16),
                ("hBalloonIcon", wintypes.HICON),
            ]

        def LOWORD(dword):
            return dword & 0xFFFF

        def _load_icon():
            if self.icon_path and os.path.isfile(self.icon_path) and self.icon_path.lower().endswith(".ico"):
                hicon = user32.LoadImageW(
                    0, self.icon_path, 1, 0, 0, 0x00000010 | 0x00008000
                )
                if hicon:
                    debug_print("[tray] ctypes: loaded .ico")
                    return hicon
                else:
                    debug_print(f"[tray] ctypes: LoadImageW failed err={kernel32.GetLastError()}")
            debug_print("[tray] ctypes: using default icon")
            return user32.LoadIconW(None, 32512)

        @WNDPROCTYPE
        def WndProc(hWnd, msg, wParam, lParam):
            if msg == WM_COMMAND and LOWORD(wParam) == ID_TRAY_QUIT:
                try:
                    if callable(self.on_quit):
                        self.on_quit()
                except Exception as e:
                    debug_print(f"[tray] on_quit error: {e!r}")
                return 0
            if msg == WM_TRAY and lParam == WM_RBUTTONUP:
                hmenu = user32.CreatePopupMenu()
                user32.AppendMenuW(hmenu, 0x0000, ID_TRAY_QUIT, "Quit")
                pt = POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                user32.SetForegroundWindow(hWnd)
                user32.TrackPopupMenu(hmenu, 0x0100, pt.x, pt.y, 0, hWnd, None)
                user32.DestroyMenu(hmenu)
                return 0
            if msg == WM_DESTROY:
                nid = NOTIFYICONDATA()
                nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
                nid.hWnd = hWnd
                nid.uID = 1
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hWnd, msg, wParam, lParam)

        hInstance = kernel32.GetModuleHandleW(None)
        cls = WNDCLASS()
        cls.style = 0
        cls.lpfnWndProc = WndProc
        cls.cbClsExtra = cls.cbWndExtra = 0
        cls.hInstance = hInstance
        cls.hIcon = 0
        cls.hCursor = 0
        cls.hbrBackground = 0
        cls.lpszMenuName = None
        cls.lpszClassName = "PixieTrayWindow"
        if not user32.RegisterClassW(ctypes.byref(cls)):
            err = kernel32.GetLastError()
            debug_print(f"[tray] ctypes: RegisterClassW failed err={err}")

        hwnd = user32.CreateWindowExW(
            0x00000080,
            cls.lpszClassName,
            self.title,
            0x80000000,
            0, 0, 0, 0,
            None, None, hInstance, None
        )
        if not hwnd:
            debug_print(f"[tray] ctypes: CreateWindowExW failed err={kernel32.GetLastError()}")
            return
        self._hwnd = hwnd

        hicon = _load_icon()

        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAY
        nid.hIcon = hicon
        tip = (self.title or "Pixie")[:127]
        nid.szTip = tip

        ok = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        if not ok:
            debug_print(f"[tray] ctypes: NIM_ADD failed err={kernel32.GetLastError()}")
            return

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        try:
            nid = NOTIFYICONDATA()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
            nid.hWnd = hwnd
            nid.uID = 1
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
        except Exception:
            pass
        try:
            ctypes.windll.user32.DestroyWindow(hwnd)
        except Exception:
            pass