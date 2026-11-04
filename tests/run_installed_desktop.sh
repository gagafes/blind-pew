#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
set -euo pipefail
# Run inside a disposable session bus; the caller supplies Xvfb for Xfce.
: "${BLIND_PEW_DISPOSABLE_SESSION:?Run only in a disposable OS user/container; startup calls im-config}"
mkdir -p desktop-output
export XDG_RUNTIME_DIR
XDG_RUNTIME_DIR=$(mktemp -d /tmp/blind-pew-desktop-XXXXXXXX)
chmod 700 "$XDG_RUNTIME_DIR"
export XDG_CONFIG_HOME="$XDG_RUNTIME_DIR/config"
export XDG_CACHE_HOME="$XDG_RUNTIME_DIR/cache"
export LANG=C.UTF-8 LANGUAGE=en LC_ALL=C.UTF-8
export GTK_IM_MODULE=ibus XMODIFIERS=@im=ibus
export PYTHONPATH=/usr/share/blind-pew
export LIBGL_ALWAYS_SOFTWARE=1
export LP_NUM_THREADS=2
export GSK_RENDERER=cairo GTK_A11Y=none NO_AT_BRIDGE=1
unset GSETTINGS_BACKEND IBUS_USE_PORTAL
export IBUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/ibus"
pids=()
cleanup() {
    for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
    for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
    rm -rf "$XDG_RUNTIME_DIR"
}
trap cleanup EXIT
if [ "$1" = gnome ]; then
    export XDG_CURRENT_DESKTOP=GNOME XDG_SESSION_TYPE=wayland
    export GDK_BACKEND=wayland WAYLAND_DISPLAY=wayland-blind-pew
else
    export XDG_CURRENT_DESKTOP=XFCE XDG_SESSION_TYPE=x11 GDK_BACKEND=x11
    unset WAYLAND_DISPLAY
fi
dbus-update-activation-environment XDG_RUNTIME_DIR XDG_CONFIG_HOME XDG_CACHE_HOME \
    XDG_CURRENT_DESKTOP XDG_SESSION_TYPE GDK_BACKEND LANG LANGUAGE LC_ALL \
    GTK_IM_MODULE XMODIFIERS IBUS_ADDRESS
ibus-daemon --address="$IBUS_ADDRESS" --panel disable --config disable --cache refresh \
    > "desktop-output/ibus-$1.log" 2>&1 &
ibus_pid=$!
pids+=("$ibus_pid")
for attempt in $(seq 1 40); do
    kill -0 "$ibus_pid"
    if ibus list-engine >/dev/null 2>&1; then break; fi
    sleep 0.25
done
ibus list-engine >/dev/null
if [ "$1" = gnome ]; then
    dbus-update-activation-environment WAYLAND_DISPLAY
    gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'us')]"
    gsettings set org.gnome.shell disable-user-extensions false
    indicator=appindicatorsupport@rgcjonas.gmail.com
    if [ -d /usr/share/gnome-shell/extensions/ubuntu-appindicators@ubuntu.com ]; then
        indicator=ubuntu-appindicators@ubuntu.com
    fi
    gsettings set org.gnome.shell enabled-extensions "['blind-pew@local', '$indicator']"
    gsettings set org.gnome.desktop.interface enable-animations false
    gnome-shell --headless --wayland --no-x11 --virtual-monitor=1280x960 \
        --wayland-display="$WAYLAND_DISPLAY" > desktop-output/gnome-shell.log 2>&1 &
    shell_pid=$!
    pids+=("$shell_pid")
    for attempt in $(seq 1 40); do
        if gdbus call --session --dest org.gnome.Shell --object-path /org/gnome/Shell \
            --method org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1; then break; fi
        kill -0 "$shell_pid"
        sleep 1
    done
else
    dbus-update-activation-environment DISPLAY XAUTHORITY
    mkdir -p "$XDG_CONFIG_HOME/xfce4/xfconf/xfce-perchannel-xml"
    cat > "$XDG_CONFIG_HOME/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
 <property name="configver" type="int" value="2"/>
 <property name="panels" type="array"><value type="int" value="1"/>
  <property name="panel-1" type="empty">
   <property name="position" type="string" value="p=6;x=0;y=0"/>
   <property name="length" type="uint" value="100"/>
   <property name="plugin-ids" type="array"><value type="int" value="1"/></property>
  </property>
 </property>
 <property name="plugins" type="empty"><property name="plugin-1" type="string" value="systray"/></property>
</channel>
XML
    xfwm4 --compositor=off > desktop-output/xfwm4.log 2>&1 &
    pids+=("$!")
    xfsettingsd --no-daemon > desktop-output/xfsettingsd.log 2>&1 &
    pids+=("$!")
    xfce4-panel --disable-wm-check > desktop-output/xfce4-panel.log 2>&1 &
    pids+=("$!")
fi
/usr/bin/python3 tests/installed_desktop_smoke.py
kill -0 "$ibus_pid"
if [ "$1" = xfce ]; then
    gsettings set org.freedesktop.ibus.general use-global-engine true
    /usr/bin/python3 tests/installed_gtk_input.py 3.0
    kill -0 "$ibus_pid"
    GDK_DEBUG=gl-disable,vulkan-disable /usr/bin/python3 tests/installed_gtk_input.py 4.0
fi
