#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Exercise the installed app against a real desktop, panel and IBus daemon."""
import faulthandler
import os
from pathlib import Path
import subprocess
import time
import traceback

from blind_pew import config, hotkey, integration
from blind_pew.setup import Application
from gi.repository import Gdk, GLib

config.update(ui_language='en', favorite_profile='ua', favorite_base='us')
faulthandler.dump_traceback_later(20, repeat=True)
app = Application()
failures = []
started = time.monotonic()


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    context = GLib.MainContext.default()
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError('Desktop operation timed out')


def exercise():
    try:
        if time.monotonic() - started > 60:
            raise AssertionError('Desktop startup timed out: ' + str(app.last_startup))
        if not app.last_startup or not app.last_startup.ready or not app.tray or not app.tray.available():
            return GLib.SOURCE_CONTINUE
        assert Path(__import__('blind_pew').__file__).resolve().is_relative_to('/usr/share/blind-pew')
        assert not app.last_startup.needs_login, app.last_startup
        assert config.load()['hotkey_backup'], app.window.status.get_text()
        app.window.preview.set_text("Ukrai'na je g'")
        assert app.window.result.get_text() == 'Україна є ґ'
        app.select_source(('ibus', 'blind-pew:ua:us'))
        wait_for(lambda: app.switches.current == ('ibus', 'blind-pew:ua:us') and not app.switches.inflight)
        wait_for(lambda: app.tray.country == 'UA')
        normal = integration.normal_source('us')
        if integration.is_gnome():
            # Exercise the exported action and actual GNOME extension bridge.
            process = subprocess.Popen(['/usr/bin/blind-pew', 'toggle'])
            wait_for(lambda: process.poll() is not None)
            assert process.returncode == 0
        else:
            # The Xfce settings daemon must execute the registered F12 command.
            subprocess.run(['xdotool', 'key', 'F12'], check=True, timeout=4)
        wait_for(lambda: app.switches.current == normal and not app.switches.inflight)
        app.tray._indicator_scroll(app.tray.indicator, 1, Gdk.ScrollDirection.UP)
        wait_for(lambda: app.switches.current == ('ibus', 'blind-pew:ua:us') and not app.switches.inflight)
        app.tray._indicator_scroll(app.tray.indicator, 1, Gdk.ScrollDirection.DOWN)
        wait_for(lambda: app.switches.current == normal and not app.switches.inflight)
        app.select_source(('ibus', 'blind-pew:ru:de'))
        wait_for(lambda: app.switches.current == ('ibus', 'blind-pew:ru:de') and not app.switches.inflight)
        wait_for(lambda: app.tray.country == 'RU')
        assert app.hide_window()
        assert not app.window.get_visible()
        app.show_about()
        assert app.window.about.get_title() == 'About'
        app.window.about.destroy()
        app.set_language('de')
        assert app.window.preview.get_text() == "Ukrai'na je g'"
        app.set_language('en')
        app.toggle()
        wait_for(lambda: app.switches.current == normal and not app.switches.inflight)
        print('PASS real desktop, installed app, panel, switching, wheel callbacks, About and live language', flush=True)
        if not integration.is_gnome():
            print('PASS physical F12 event through Xfce settings daemon', flush=True)
        app.quit()
    except Exception:
        failures.append(traceback.format_exc())
        print(failures[-1], flush=True)
        app.quit()
    return GLib.SOURCE_REMOVE


GLib.timeout_add(300, exercise)
status = app.run(['blind-pew'])
faulthandler.cancel_dump_traceback_later()
assert not failures, failures
assert not config.load()['hotkey_backup'], 'Shortcut backups not restored on quit'
assert not config.load()['session_backup'], 'Session backups not restored on quit'
if not integration.is_gnome():
    assert hotkey._xfget(hotkey.XFCE_KEY) != hotkey.COMMAND
print('PASS settings restored on application shutdown', flush=True)
raise SystemExit(status)
