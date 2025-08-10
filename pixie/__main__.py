import os, sys

def main():
    if "GDK_BACKEND" not in os.environ:
        st = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") or st == "wayland":
            os.environ["GDK_BACKEND"] = "wayland"
    from .app import main as app_main
    app_main()

if __name__ == "__main__":
    main()
