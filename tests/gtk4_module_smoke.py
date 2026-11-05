#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
# The import order is intentional: GI versions, runtime checks or sys.path
# bootstrap must precede importing their dependent modules.
# ruff: noqa: E402
"""Check the REAL GTK4 IBus input module, without faking successful input.

This checks GTK4 module loading and widget configuration, not end-to-end
typing. A live ibus-daemon and a desktop session are needed for that.
Run: /usr/bin/python3 tests/run_gui_smoke.py tests/gtk4_module_smoke.py
"""
import os
import time
os.environ['GTK_IM_MODULE'] = 'ibus'
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, GObject, Gtk

Gtk.init()
window = Gtk.Window(title='GTK4 input compatibility check')
box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
window.set_child(box)
field = Gtk.Text()
paragraph = Gtk.TextView()
for widget in (field, paragraph):
    widget.set_property('im-module', 'ibus')
    box.append(widget)
window.present()
field.grab_focus()
context = Gtk.IMMulticontext.new()
context.set_client_widget(field)
context.set_context_id('ibus')
context.focus_in()
main = GLib.MainContext.default()
deadline = time.monotonic() + 0.3
while time.monotonic() < deadline:
    while main.pending():
        main.iteration(False)
    time.sleep(0.005)
assert context.get_context_id() == 'ibus', context.get_context_id()
assert GObject.type_from_name('IBusIMContext')
for widget in (field, paragraph):
    assert widget.get_property('im-module') == 'ibus'
context.reset()
context.focus_out()
context.set_client_widget(None)
window.destroy()
print(f'PASS GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()}: actual IBusIMContext loaded; Gtk.Text and Gtk.TextView configured')
print('NOTE: module check only; end-to-end typing requires a live IBus desktop session.')
