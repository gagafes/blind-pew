#!/usr/bin/python3
"""Send real X11 key events through installed GTK3/GTK4 and IBus modules."""
import subprocess
import sys
import time
import gi

gi.require_version('Gtk', sys.argv[1])
gi.require_version('IBus', '1.0')
from gi.repository import GLib, Gtk, IBus

Gtk.init()
IBus.init()
window = Gtk.Window(title='Blind Pew installed typing test')
entry = Gtk.Entry()
entry.set_property('im-module', 'ibus')
if sys.argv[1] == '3.0':
    window.add(entry)
    window.show_all()
else:
    window.set_child(entry)
window.present()
entry.grab_focus()
bus = IBus.Bus.new()


def pump(seconds=0.25):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        time.sleep(0.005)


pump(1)
subprocess.run(['xdotool', 'search', '--name', '^Blind Pew installed typing test$',
                'windowactivate', '--sync'], check=True, timeout=5)
pump()
for name, text, expected in (
    ('blind-pew:ru:us', 'Privet shh ', 'Привет щ '),
    ('blind-pew:ua:us', "Ukrai'na je g' ", 'Україна є ґ '),
    ('blind-pew:rude:de', 'sch tsch ei w v ', 'ш ч ай в ф '),
):
    entry.set_text('')
    assert bus.set_global_engine(name), name
    pump(0.5)
    # Run asynchronously: GTK must keep processing events while xdotool types.
    process = subprocess.Popen(['xdotool', 'type', '--clearmodifiers', '--delay', '45', text])
    while process.poll() is None:
        pump(0.02)
    assert process.returncode == 0
    pump(0.4)
    assert entry.get_text() == expected, (sys.argv[1], name, entry.get_text(), expected)
    print('PASS real GTK', sys.argv[1], name, flush=True)
entry.set_text('')
entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
entry.set_visibility(False)
pump()
process = subprocess.Popen(['xdotool', 'type', '--clearmodifiers', '--delay', '45', 'secret'])
while process.poll() is None:
    pump(0.02)
pump()
assert entry.get_text() == 'secret', 'Password text was transliterated'
print('PASS GTK', sys.argv[1], 'password field bypass', flush=True)
window.destroy()
