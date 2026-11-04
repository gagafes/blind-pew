#!/usr/bin/python3
"""Capture the installed, unmodified application inside a disposable GNOME session."""
import json
import os
from pathlib import Path
import subprocess
import time

from blind_pew import config, i18n

config.update(ui_language='en', favorite_profile='ua', favorite_base='us')

from blind_pew.setup import Application
from gi.repository import Gio, GLib

output = Path('docs/screenshots').resolve()
output.mkdir(parents=True, exist_ok=True)
connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
app = Application()
started = time.monotonic()
failed = []


def shell_eval(code):
    result = connection.call_sync(
        'org.gnome.Shell', '/org/gnome/Shell', 'org.gnome.Shell', 'Eval',
        GLib.Variant('(s)', (code,)), GLib.VariantType.new('(bs)'),
        Gio.DBusCallFlags.NONE, 10000, None).unpack()
    if not result[0]:
        raise RuntimeError('GNOME evaluation failed: ' + str(result))
    return result[1]


def capture(name):
    filename = output / name
    result = connection.call_sync(
        'org.gnome.Shell.Screenshot', '/org/gnome/Shell/Screenshot',
        'org.gnome.Shell.Screenshot', 'Screenshot',
        GLib.Variant('(bbs)', (False, False, str(filename))),
        GLib.VariantType.new('(bs)'), Gio.DBusCallFlags.NONE, 15000, None).unpack()
    if not result[0] or filename.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError('GNOME did not capture ' + name)
    print('Captured', name, filename.stat().st_size, 'bytes', flush=True)


def guarded(callback):
    def run():
        try:
            return callback()
        except Exception as error:
            failed.append(str(error))
            import traceback
            traceback.print_exc()
            app.quit()
            return GLib.SOURCE_REMOVE
    return run


def settings_capture():
    capture('gnome-settings-en.png')
    app.window.about_button.clicked()
    GLib.timeout_add(2000, guarded(about_capture))
    return GLib.SOURCE_REMOVE


def about_capture():
    assert app.window.about is not None
    assert app.window.about.get_title() == 'About'
    capture('gnome-about-en.png')
    info = {
        'gnome': subprocess.check_output(['gnome-shell', '--version'], text=True).strip(),
        'session': os.environ['XDG_SESSION_TYPE'],
        'interface_language': i18n.current(),
        'ibus_ready': app.last_startup.ready,
        'tray_available': app.tray.available(),
        'source': '/usr/share/blind-pew (installed DEB)',
    }
    Path('screenshot-output/capture-info.json').write_text(json.dumps(info, indent=2) + '\n')
    print(json.dumps(info), flush=True)
    app.quit()
    return GLib.SOURCE_REMOVE


def ready():
    if time.monotonic() - started > 55:
        raise RuntimeError('GNOME/IBus/tray did not become ready')
    if not app.window or not app.last_startup or not app.last_startup.ready:
        return GLib.SOURCE_CONTINUE
    if not app.tray or not app.tray.available():
        return GLib.SOURCE_CONTINUE
    assert i18n.current() == 'en'
    app.window.preview.set_text("Ukrai'na je g'")
    app.window.on_add()
    app.window.resize(740, 720)
    shell_eval("Main.overview.hide(); global.get_window_actors().forEach(a => { const w = a.meta_window; if (w.get_title() === 'Blind Pew') w.move_resize_frame(true, 270, 100, 740, 720); });")
    GLib.timeout_add(3000, guarded(settings_capture))
    return GLib.SOURCE_REMOVE


GLib.timeout_add(500, guarded(ready))
status = app.run(['blind-pew'])
if failed:
    raise SystemExit('; '.join(failed))
raise SystemExit(status)
