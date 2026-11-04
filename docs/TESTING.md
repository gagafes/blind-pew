# Testing Blind Pew

Run commands from the repository root. Use the system Python for GTK/IBus
checks so that packages installed through APT are available.

## Dependencies and local regressions

On Debian 13 or Ubuntu 24.04:

```sh
sudo apt install python3 python3-gi libglib2.0-bin gsettings-desktop-schemas gir1.2-ibus-1.0 \
  gir1.2-gtk-3.0 gir1.2-gtk-4.0 gir1.2-ayatanaappindicator3-0.1 \
  ibus ibus-gtk3 ibus-gtk4 im-config xfconf libxfconf-0-3 xvfb xauth dbus-x11 \
  desktop-file-utils nodejs dpkg lintian
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
lintian --fail-on error dist/*.deb
```

Run GUI checks sequentially. They isolate configuration, cache, GSettings,
the session bus and display. Xvfb uses local Xauthority authentication with
TCP listening disabled. The unit/protocol suite checks all eight profiles,
16 engine IDs, composition boundaries, backspace, focus/reset, modifiers and
Password/PIN/Private input. Preferences are tested against oversized/deep JSON,
invalid text, FIFOs, symlinks, interrupted writes and malformed shortcut backups.
Streaming tests include long input without newlines and every chunk boundary.

The regular GUI suite uses actual GI libraries and D-Bus with test services for
the panel and GNOME bridge. It covers live translation, RTL preview, window/tray
lifecycle, About, rapid source switching, stale replies, settings rollback and
shortcut restoration. These simulated services are distinct from the installed
desktop checks below. All 49 interface catalogs are compiled and checked;
that does not establish translation quality.

## Installed-package CI

`.github/workflows/ci.yml` runs separate Ubuntu 24.04 and Debian 13 jobs:

| Check | Scope |
|---|---|
| Source regressions | Unit, IBus protocol, GTK GUI and GNOME bridge tests |
| Package | Build twice and compare SHA-256, Lintian errors, upgrade from 0.1.0-1, installed-file verification, removal and clean reinstall |
| Installed program | CLI, profile/engine registration, 49 compiled catalogs, payload/licenses and friendly headless startup failure |
| Actual IBus daemon | All eight profiles, both bases across the test cases, committed text, Backspace, modifiers, focus changes and password bypass |
| Xfce desktop | Real Xfwm4, settings daemon and panel; installed application; X11 F12 key event; tray callbacks, About, live language and restoration on quit |
| GTK input | Actual X11 key events through installed GTK3/GTK4 IBus modules for Russian, Ukrainian and Russian DE profiles; password-field bypass |
| GNOME Wayland | Real headless GNOME Shell and AppIndicator extension; installed bridge, source changes, toggle action, tray callbacks, About and restoration |
| Security | Pyflakes, Bandit medium/high findings and Gitleaks over Git history |

The desktop runner **must be used only in a disposable OS user/container**.
Although it isolates XDG directories and D-Bus, the real application invokes
`im-config`, which may set that user's `~/.xinputrc`. CI sets
`BLIND_PEW_DISPOSABLE_SESSION=1` only inside its test containers. The runner
captures desktop/IBus logs as workflow artifacts. See the workflow for the
complete package prerequisites and commands.

Each package artifact includes `system-packages.tsv` with the tested distribution
versions and `SHA256SUMS`. Dependencies are supplied by APT and are not bundled
in the DEB. Source scanners are not a CVE clearance for the entire OS, nor a
proof that all defects have been found. Review the exact commit's CI conclusion;
a local pass or a run for an earlier commit does not establish final CI success.

## Remaining manual coverage

The author previously confirmed **Debian 13 / XFCE 4.20**. Automated desktops
run with virtual displays/software rendering. They do not establish behavior
in every interactive desktop, on physical keyboard hardware, or with Qt,
Electron, Flatpak and Snap applications. The GNOME test invokes the exported
toggle action; it does not synthesize a physical Wayland F12 event. Tray scroll
callbacks are exercised, not physical mouse hardware. All 49 translations have
not been reviewed by native speakers.

On a disposable desktop:

1. Install the DEB, log out and back in, and start Blind Pew.
2. On GNOME, enable Blind Pew Integration and the AppIndicator extension.
3. Apply profiles with QWERTY and QWERTZ; type in editors and browsers.
4. Check F12 and both vertical wheel directions, alternating and repeating them.
5. Check tray appearance, hide/show, interface language and About.
6. Quit and verify that unrelated sources and saved shortcuts remain.

## Package inspection and reproducibility

```sh
dpkg-deb --info dist/blind-pew_0.1.0-2_all.deb
dpkg-deb --contents dist/blind-pew_0.1.0-2_all.deb
```

The package includes 16 IBus engines, 49 catalogs, icons/logo, five READMEs,
English GNOME screenshots, project/license notices and release documentation.
Repository download links are omitted from installed documentation.
`tools/build.py` reads the version and default build timestamp from the Debian
changelog; `SOURCE_DATE_EPOCH` can override the timestamp. Reproducibility is
checked with the same toolchain. Different distribution/xz versions can produce
different compressed bytes. Use the Ubuntu 24.04 CI artifact for distribution.
