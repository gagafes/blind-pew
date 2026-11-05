#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
# The import order is intentional: GI versions, runtime checks or sys.path
# bootstrap must precede importing their dependent modules.
# ruff: noqa: E402
"""Real GI engine + D-Bus protocol, with a minimal test client (no ibus-daemon).

This isolates protocol edge cases and complements the installed daemon test.
"""
import time
import gi
gi.require_version('IBus', '1.0')
from gi.repository import Gio, GLib, IBus
from blind_pew.engine import Engine, Factory
from blind_pew.core import engines

IBus.init()
connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
main = GLib.MainContext.default()
events = []
object_path = '/org/freedesktop/IBus/BlindPew/Test'


def pump():
    until = time.monotonic() + 0.01
    while time.monotonic() < until:
        while main.pending():
            main.iteration(False)
        time.sleep(0.001)


subscription = connection.signal_subscribe(
    None, 'org.freedesktop.IBus.Engine', None, object_path, None,
    Gio.DBusSignalFlags.NONE,
    lambda _c, sender, path, interface, signal, params: events.append((signal, params.unpack())))


def call(method, signature=None, args=(), interface='org.freedesktop.IBus.Engine', path=None):
    done = []
    def callback(conn, result):
        try:
            done.append(conn.call_finish(result))
        except Exception as error:
            done.append(error)
    connection.call(connection.get_unique_name(), path or object_path,
                    interface, method,
                    GLib.Variant(signature, args) if signature else None,
                    None, Gio.DBusCallFlags.NONE, 3000, None, callback)
    deadline = time.monotonic() + 4
    while not done and time.monotonic() < deadline:
        pump()
    assert done, method + ' timed out'
    if isinstance(done[0], Exception):
        raise done[0]
    pump()
    return done[0].unpack()


def key(value, flags=0):
    return call('ProcessKeyEvent', '(uuu)', (value, 0, int(flags)))[0]


def type_text(value):
    for char in value:
        if not key(IBus.unicode_to_keyval(char)):
            events.append(('PassThrough', char))


def committed():
    result = ''
    for name, args in events:
        if name == 'CommitText':
            result += args[0][2]
        elif name == 'PassThrough':
            result += args
    return result


samples = {
    'ru': ('Privet, mir! sh zh shh raj+on ', 'Привет, мир! ш ж щ район '),
    'rude': ('w v z s c h x ei sch tsch ', 'в ф ц з с ч кс ай ш ч '),
    'ua': ("Pryvit! Ukrai'na je g' ", 'Привіт! Україна є ґ '),
    'ge': ("gamarjoba! k' p' t' ch' ", 'გამარჯობა! კ პ ტ ჭ '),
    'am': ('Barev! sh gh jh u & ', 'Բարեվ! շ ղ ժ ու և '),
    'il': ('shloms fs cs ms ns ks ha aa ka tt ', 'שלום ף ץ ם ן ך ה ע כ ט '),
    'be': ('Pryvitanne! w i jo je ', 'Прывітанне! ў і ё э '),
    'li': ('Labas! aa cx ee ex ii sx uu ux zx a+a s+x ', 'Labas! ą č ę ė į š ų ū ž aa sx '),
}
for name, profile, base in engines():
    engine = Engine(connection, object_path, name)
    call('Enable')
    call('FocusIn')
    assert engine._prop.get_label().get_text() == __import__('blind_pew.i18n', fromlist=['tr']).tr('Transliteration')
    assert engine._prop.get_symbol().get_text() == profile['symbol']
    events.clear()
    text, expected = samples[profile['id']]
    type_text(text)
    assert committed() == expected, (name, committed(), expected, events)
    assert not key(IBus.KEY_F12)  # desktop owns the global shortcut
    assert not key(IBus.KEY_Escape)
    events.clear()
    type_text(text)
    assert committed() == expected  # no hidden conversion toggle
    call('Disable')
    engine.destroy()
    pump()
    print('PASS', name)

for mode, sequence, pending in [('ua', 'g', 'г'), ('ge', 'k', 'ქ'),
                                ('am', 's', 'ս'), ('il', 'm', 'מ'),
                                ('be', 'j', 'й'), ('li', 'a', 'a')]:
    engine = Engine(connection, object_path, f'blind-pew:{mode}:us')
    call('FocusIn')
    events.clear()
    type_text(sequence)
    assert engine.composer.pending == pending, (mode, engine.composer.pending)
    assert key(IBus.KEY_BackSpace)
    assert engine.composer.pending == ''
    assert committed() == ''
    engine.destroy()
    pump()
print('PASS scripts: preedit Backspace, labels and shortcut passthrough')

engine = Engine(connection, object_path, 'blind-pew:ru:us')
call('FocusIn')
events.clear()
type_text('sh')
assert engine.composer.pending == 'ш'
assert key(IBus.KEY_BackSpace)
assert not engine.composer.pending
type_text('a ')
assert committed() == 'а '
print('PASS Backspace and preedit lifecycle')

events.clear()
type_text('s')
assert not key(IBus.KEY_c, IBus.ModifierType.CONTROL_MASK)
assert committed() == 'с'
assert not key(IBus.KEY_s, IBus.ModifierType.RELEASE_MASK)
assert not key(IBus.KEY_F12)
assert not key(IBus.KEY_Escape)
assert key(IBus.KEY_a)
print('PASS F12/Esc passed to desktop/client; transliteration remains active')

for purpose, hints in [(IBus.InputPurpose.PASSWORD, 0), (IBus.InputPurpose.PIN, 0),
                       (IBus.InputPurpose.FREE_FORM, IBus.InputHints.PRIVATE)]:
    call('Set', '(ssv)', ('org.freedesktop.IBus.Engine', 'ContentType',
                        GLib.Variant('(uu)', (int(purpose), int(hints)))),
         interface='org.freedesktop.DBus.Properties')
    assert not key(IBus.KEY_s)
    assert not key(IBus.KEY_F12)
call('Set', '(ssv)', ('org.freedesktop.IBus.Engine', 'ContentType',
                    GLib.Variant('(uu)', (int(IBus.InputPurpose.FREE_FORM), 0))),
     interface='org.freedesktop.DBus.Properties')
print('PASS Password/PIN/Private bypass')

type_text('s')
call('FocusOut')
assert not engine.composer.pending
call('FocusIn')
events.clear()
type_text('h ')
assert committed() == 'х '
type_text('s')
call('Reset')
assert not engine.composer.pending
print('PASS clear on focus-out/reset; no cross-field composition')
print('NOTE: automatic preedit commit on focus-out belongs to ibus-daemon, not this test client.')
engine.destroy()
connection.signal_unsubscribe(subscription)

class ConnectionProvider:
    def get_connection(self):
        return connection

factory = Factory(ConnectionProvider())
created_path, = call('CreateEngine', '(s)', ('blind-pew:ru:us',),
                    interface='org.freedesktop.IBus.Factory', path=IBus.PATH_FACTORY)
assert created_path.startswith('/org/freedesktop/IBus/BlindPew/Engine')
assert len(factory.instances) == 1
for item in list(factory.instances):
    item.destroy()
pump()
assert not factory.instances
factory.destroy()
print('PASS real IBus factory export, engine creation and destruction')
