import os, sys

def _root():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)

root = _root()

os.environ["PATH"] = os.path.join(root, "bin") + os.pathsep + os.environ.get("PATH", "")
os.environ["GI_TYPELIB_PATH"] = os.path.join(root, "lib", "girepository-1.0") + os.pathsep + os.environ.get("GI_TYPELIB_PATH", "")
os.environ["GDK_PIXBUF_MODULEDIR"] = os.path.join(root, "lib", "gdk-pixbuf-2.0", "2.10.0", "loaders")
