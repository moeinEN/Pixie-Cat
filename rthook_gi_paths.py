import os, sys

_base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))

gi_typelib = os.path.join(_base, "lib", "girepository-1.0")
os.environ["GI_TYPELIB_PATH"] = os.pathsep.join(
    [gi_typelib, os.environ.get("GI_TYPELIB_PATH","")]
).strip(os.pathsep)

gdkpix_lib   = os.path.join(_base, "lib", "gdk-pixbuf-2.0")
loaders_dir  = os.path.join(gdkpix_lib, "2.10.0", "loaders")
cache_file   = os.path.join(gdkpix_lib, "2.10.0", "loaders.cache")
os.environ["GDK_PIXBUF_MODULEDIR"] = loaders_dir
os.environ["GDK_PIXBUF_MODULE_FILE"] = cache_file

os.environ["PATH"] = os.pathsep.join([
    _base,
    os.path.join(_base, "bin"),
    os.environ.get("PATH","")
])
