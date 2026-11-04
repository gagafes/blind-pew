# Testing Blind Pew

Run commands from the repository root. Use the system Python for GTK/IBus
checks so that packages installed through APT are available.

## Dependencies

On Debian 13 or Ubuntu 24.04:

~~~sh
sudo apt install python3 python3-gi libglib2.0-bin gsettings-desktop-schemas gir1.2-ibus-1.0 \
  gir1.2-gtk-3.0 gir1.2-gtk-4.0 gir1.2-ayatanaappindicator3-0.1 \
  ibus ibus-gtk3 ibus-gtk4 im-config xfconf xvfb dbus-x11 \
  desktop-file-utils nodejs dpkg
~~~

## Automated checks

~~~sh
/usr/bin/python3 -m unittest discover -s tests -v
sh tests/run_protocol_smoke.sh
/usr/bin/python3 tests/run_gui_smoke.py
/usr/bin/python3 tests/run_gui_smoke.py tests/about_smoke.py
/usr/bin/python3 tests/run_gui_smoke.py tests/hotkey_smoke.py
/usr/bin/python3 tests/run_gui_smoke.py tests/desktop_smoke.py
/usr/bin/python3 tests/run_gui_smoke.py tests/gtk4_module_smoke.py
desktop-file-validate assets/blind-pew.desktop
node --input-type=module --check < assets/gnome-extension/extension.js
/usr/bin/python3 tools/build.py
~~~

Run GUI checks sequentially. The runners isolate configuration, cache,
GSettings and the display. Their private D-Bus sessions use loopback TCP
to work in environments that restrict Unix sockets.

The tests cover:

- All eight transliteration tables, generated input sequences, bounded
  preedit, Backspace, focus/reset and Password/PIN/Private input.
- IBus startup, configuration validation, atomic saves and rollback.
- All 49 translation catalogs, locale priority, aliases and fallback.
- F12 and vertical tray scrolling toggling the selected profile and
  returning to the ordinary source, including rapid and mixed events.
- AppIndicator registration, tray visibility, window lifecycle, country
  codes, live translation and the About dialog.
- GNOME/IBus global settings and GNOME/XFCE shortcut backup and restoration.
- GNOME bridge messages, stale replies and shutdown.
- Loading the IBus input context for GTK4 text widgets.

The GitHub Actions workflow uses Ubuntu 24.04 and runs these checks before
building the DEB. A local pass does not establish that a GitHub run has passed.

## Desktop verification

The author confirmed operation on **Debian 13 with XFCE 4.20**.

The automated tests use actual GI libraries and D-Bus, with test services for
the panel and GNOME bridge. The tray test substitutes IBus startup and
source-switch results. These checks do not replace a complete desktop session.
Full GNOME/Wayland operation and end-to-end input in GTK4, Qt, Electron,
Flatpak and Snap applications still need manual verification.
Loading a GTK4 input module alone does not verify typing through that module.
All 49 translation catalogs have not been reviewed by native speakers.

On a regular test desktop, the additional command
`sh tests/run_ibus_smoke.sh` exercises the engine through a real ibus-daemon.

1. Install the DEB, log out and back in, and start Blind Pew.
2. On GNOME, enable Blind Pew Integration and the AppIndicator extension.
3. Apply a profile with QWERTY, then QWERTZ, and type in an editor and browser.
4. Check F12 and both vertical scroll directions: selected transliteration
   ↔ ordinary source. Mix them and repeat quickly.
5. Check the tray indicator, hide/show, interface language and About dialog.
6. Quit and verify that unrelated sources and saved desktop shortcuts remain.

## Package inspection

~~~sh
dpkg-deb --info dist/blind-pew_0.1.0-1_all.deb
dpkg-deb --contents dist/blind-pew_0.1.0-1_all.deb
~~~

The package contains 16 IBus engines, 49 compiled catalogs, the application
and tray SVG icons, the About logo, five READMEs and the MIT license.
It does not bundle its system dependencies. Repository download links are
omitted from installed documentation.

For reproducible DEBs, keep the same build tools and set
`SOURCE_DATE_EPOCH`. The build script also supplies a fixed default.

