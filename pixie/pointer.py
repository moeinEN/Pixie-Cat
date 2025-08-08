from __future__ import annotations

import os
import sys
from typing import Optional, Tuple

__all__ = ["get_mouse_position"]

_POS_TYPE = Tuple[int, int]


def _gtk_backend() -> Optional[_POS_TYPE]:
    try:
        import gi
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk
    except (ModuleNotFoundError, ImportError, ValueError):
        return None

    display = Gdk.Display.get_default()
    if display is None:
        return None

    seat = display.get_default_seat()
    pointer = seat.get_pointer()

    if hasattr(pointer, "get_position"):
        _surf, x, y = pointer.get_position()
        return int(x), int(y)

    if hasattr(pointer, "get_surface_at_position"):
        surface, sx, sy = pointer.get_surface_at_position()
        if surface is None:
            return None
        if hasattr(surface, "get_position"):
            ox, oy = surface.get_position()
        elif hasattr(surface, "get_origin"):
            ox, oy = surface.get_origin()
        else:
            ox = oy = 0
        return int(ox + sx), int(oy + sy)

    return None


def _win_backend() -> Optional[_POS_TYPE]:
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return None

    pt = wintypes.POINT()
    if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        return pt.x, pt.y
    return None


def _x11_backend() -> Optional[_POS_TYPE]:
    if os.environ.get("WAYLAND_DISPLAY"):
        return None
    try:
        from Xlib import display
    except ImportError:
        return None

    dsp = display.Display()
    root = dsp.screen().root
    data = root.query_pointer()._data
    return data["root_x"], data["root_y"]


_backends = (_gtk_backend, _win_backend, _x11_backend)

def get_mouse_position() -> Optional[_POS_TYPE]:
    for backend in _backends:
        pos = backend()
        if pos is not None:
            return pos
    return None
