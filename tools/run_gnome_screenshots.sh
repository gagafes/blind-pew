#!/bin/bash
set -euo pipefail
mkdir -p screenshot-output docs/screenshots
export XDG_RUNTIME_DIR
XDG_RUNTIME_DIR=$(mktemp -d /tmp/blind-pew-gnome-XXXXXXXX)
chmod 700 "$XDG_RUNTIME_DIR"
export XDG_CONFIG_HOME="$XDG_RUNTIME_DIR/config"
export XDG_CACHE_HOME="$XDG_RUNTIME_DIR/cache"
export XDG_CURRENT_DESKTOP=GNOME
export XDG_SESSION_TYPE=wayland
export GDK_BACKEND=wayland
export WAYLAND_DISPLAY=wayland-blind-pew
export LANG=C.UTF-8 LANGUAGE=en LC_ALL=C.UTF-8
shell_pid=
cleanup() {
    if [ -n "$shell_pid" ]; then
        kill "$shell_pid" 2>/dev/null || true
        wait "$shell_pid" 2>/dev/null || true
    fi
    rm -rf "$XDG_RUNTIME_DIR"
}
trap cleanup EXIT

dbus-update-activation-environment XDG_RUNTIME_DIR XDG_CONFIG_HOME XDG_CACHE_HOME \
    XDG_CURRENT_DESKTOP XDG_SESSION_TYPE GDK_BACKEND WAYLAND_DISPLAY LANG LANGUAGE LC_ALL

gnome-shell --version | tee screenshot-output/gnome-version.txt
gsettings set org.gnome.desktop.interface gtk-theme 'Adwaita'
gsettings set org.gnome.desktop.interface icon-theme 'Adwaita'
gsettings set org.gnome.desktop.interface font-name 'Cantarell 11'
gsettings set org.gnome.desktop.interface color-scheme 'prefer-light'
gsettings set org.gnome.desktop.interface enable-animations false
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.desktop.notifications show-banners false
gsettings set org.gnome.desktop.background picture-uri ''
gsettings set org.gnome.desktop.background picture-uri-dark ''
gsettings set org.gnome.desktop.background primary-color '#263238'
gsettings set org.gnome.desktop.background color-shading-type 'solid'
gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'us')]"
gsettings set org.gnome.shell disable-user-extensions false
gsettings set org.gnome.shell enabled-extensions "['blind-pew@local', 'ubuntu-appindicators@ubuntu.com']"
gsettings set org.gnome.shell welcome-dialog-last-shown-version '46.0'

# This disposable compositor contains only the demo application. Its testing
# mode permits the native screenshot and window-positioning D-Bus calls.
gnome-shell --headless --wayland --no-x11 --virtual-monitor=1280x960 \
    --wayland-display="$WAYLAND_DISPLAY" --unsafe-mode \
    > screenshot-output/gnome-shell.log 2>&1 &
shell_pid=$!
for attempt in $(seq 1 40); do
    if gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
        --method org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1; then break; fi
    kill -0 "$shell_pid"
    sleep 1
done
gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
    --method org.freedesktop.DBus.Peer.Ping
ibus-daemon --daemonize --panel disable --config disable --cache refresh \
    > screenshot-output/ibus.log 2>&1
export PYTHONPATH=/usr/share/blind-pew
/usr/bin/python3 tools/capture_gnome_screenshots.py 2>&1 | tee screenshot-output/capture.log

