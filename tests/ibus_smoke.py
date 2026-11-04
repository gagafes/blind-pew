#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Real IBus/D-Bus smoke test. Run under tests/run_ibus_smoke.sh after install."""
import time
import gi
gi.require_version('IBus', '1.0')
from gi.repository import GLib, IBus


def pump(seconds=0.04):
    until = time.monotonic() + seconds
    context = GLib.MainContext.default()
    while time.monotonic() < until:
        while context.pending():
            context.iteration(False)
        time.sleep(0.002)


IBus.init()
bus = IBus.Bus.new()
for _ in range(50):
    if bus.is_connected():
        break
    pump(0.05)
assert bus.is_connected(), 'No IBus connection'
found = [e.get_name() for e in bus.list_engines() if e.get_name().startswith('blind-pew:')]
assert len(found) == 16, found
ctx = bus.create_input_context('blind-pew-test')
ctx.set_capabilities(IBus.Capabilite.PREEDIT_TEXT | IBus.Capabilite.FOCUS | IBus.Capabilite.PROPERTY)
committed = []
preedits = []
ctx.connect('commit-text', lambda _, value: committed.append(value.get_text()))
ctx.connect('update-preedit-text', lambda _, value, cursor, visible: preedits.append(value.get_text() if visible else ''))
ctx.focus_in()


def select(name):
    ctx.set_engine(name)
    pump(0.3)
    engine = ctx.get_engine()
    assert engine and engine.get_name() == name, (name, engine.get_name() if engine else None)
    committed.clear()
    preedits.clear()


def key(value, flags=0):
    consumed = ctx.process_key_event(value, 0, flags)
    pump()
    return consumed


def type_text(value):
    for ch in value:
        consumed = key(IBus.unicode_to_keyval(ch))
        if not consumed:
            committed.append(ch)


for name, text, expected in [
    ('blind-pew:ru:us', 'Privet, mir! sh zh shh raj+on ', 'Привет, мир! ш ж щ район '),
    ('blind-pew:ru:de', 'y z ö ä ü ', 'ы з ё э ю '),
    ('blind-pew:rude:de', 'sch tsch ei w v ', 'ш ч ай в ф '),
    ('blind-pew:ua:us', "Pryvit! Ukrai'na je g' ", 'Привіт! Україна є ґ '),
    ('blind-pew:ge:de', "gamarjoba! k' p' t' ch' ", 'გამარჯობა! კ პ ტ ჭ '),
    ('blind-pew:am:us', 'Barev! sh gh jh u & ', 'Բարեվ! շ ղ ժ ու և '),
    ('blind-pew:il:de', 'shloms fs cs ms ns ks ', 'שלום ף ץ ם ן ך '),
    ('blind-pew:be:us', 'Pryvitanne! w i jo je ', 'Прывітанне! ў і ё э '),
    ('blind-pew:li:de', 'Labas! aa cx ee ex ii sx uu ux zx ', 'Labas! ą č ę ė į š ų ū ž '),
]:
    select(name)
    type_text(text)
    assert ''.join(committed) == expected, (name, committed, expected)
    print('PASS', name)

select('blind-pew:ru:us')
type_text('sh')
assert key(IBus.KEY_BackSpace)
type_text('a ')
assert ''.join(committed) == 'а ', committed
print('PASS visible-character Backspace')

committed.clear()
type_text('s')
assert not key(IBus.KEY_c, IBus.ModifierType.CONTROL_MASK)
assert ''.join(committed) == 'с', committed
assert not key(IBus.KEY_s, IBus.ModifierType.RELEASE_MASK)
print('PASS shortcuts, pending commit and release events')

committed.clear()
assert not key(IBus.KEY_F12)
assert not key(IBus.KEY_Escape)
print('PASS no internal F12/Esc conversion shortcuts')

committed.clear()
type_text('s')
ctx.focus_out()
pump(0.15)
assert ''.join(committed) == 'с', ('focus-out lost or duplicated preedit', committed)
ctx.focus_in()
pump()
committed.clear()
type_text('h ')
assert ''.join(committed) == 'х ', committed
print('PASS focus-out commits once; new focus cannot combine old text')

ctx.set_content_type(IBus.InputPurpose.PASSWORD, IBus.InputHints.NONE)
pump()
assert not key(IBus.KEY_s)
assert not key(IBus.KEY_F12)
ctx.set_content_type(IBus.InputPurpose.FREE_FORM, IBus.InputHints.NONE)
pump()
print('PASS password bypass')
ctx.destroy()
print('ALL IBUS SMOKE CHECKS PASSED')
