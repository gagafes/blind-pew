# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""GNOME's global source-switching bridge over a real D-Bus session."""
import os
import time
os.environ['XDG_CURRENT_DESKTOP']='GNOME'
from gi.repository import Gio, GLib
from blind_pew.desktop import DesktopBackend, GNOME_PATH, GNOME_INTERFACE

main=GLib.MainContext.default()
def wait(predicate):
    end=time.monotonic()+4
    while time.monotonic()<end:
        while main.pending():main.iteration(False)
        if predicate():return
        time.sleep(.005)
    raise AssertionError('GNOME bridge timed out')

connection=Gio.bus_get_sync(Gio.BusType.SESSION,None)
xml='''<node><interface name="org.blindpew.Desktop">
<method name="GetState"><arg type="s" direction="out"/><arg type="s" direction="out"/></method>
<method name="Activate"><arg type="s" direction="in"/><arg type="s" direction="in"/><arg type="b" direction="out"/></method>
<signal name="StateChanged"><arg type="s"/><arg type="s"/></signal>
</interface></node>'''
state=['xkb','de']
pending = []
hold = False
def emit():
    connection.emit_signal(None,GNOME_PATH,GNOME_INTERFACE,'StateChanged',GLib.Variant('(ss)',state))
def method(conn,sender,path,iface,name,params,invocation):
    if name=='GetState':
        if hold:
            pending.append((invocation, tuple(state)))
        else:
            invocation.return_value(GLib.Variant('(ss)',state))
    else:
        state[:]=params.unpack()
        emit()
        invocation.return_value(GLib.Variant('(b)',(True,)))
registration=connection.register_object(GNOME_PATH,Gio.DBusNodeInfo.new_for_xml(xml).interfaces[0],method,None,None)
owner=Gio.bus_own_name_on_connection(connection,'org.gnome.Shell',Gio.BusNameOwnerFlags.NONE,None,None)
changes,replies=[],[]
backend=DesktopBackend(None,changes.append)
try:
    wait(lambda: changes and changes[-1]==('xkb','de'))
    backend.activate(('ibus','blind-pew:ua:de'),lambda *v:replies.append(v))
    wait(lambda: replies and changes[-1]==('ibus','blind-pew:ua:de'))
    assert replies[-1]==(True,'')
    state[:]=['xkb','de'];emit()
    wait(lambda: changes[-1]==('xkb','de'))
    hold = True
    backend.refresh()
    wait(lambda: pending)
    state[:] = ['xkb', 'us']; emit()
    wait(lambda: changes[-1] == ('xkb', 'us'))
    invocation, snapshot = pending.pop()
    invocation.return_value(GLib.Variant('(ss)', snapshot))
    marker = []
    GLib.timeout_add(100, lambda: (marker.append(True), False)[1])
    wait(lambda: marker)
    assert changes[-1] == ('xkb', 'us'), 'Stale GetState overwrote a newer source signal'
    state[:] = ['', '']; emit()
    wait(lambda: changes[-1] is None)
    print('PASS real D-Bus: global source read, activation and external source changes')
    print('PASS delayed GNOME state reply cannot overwrite a newer source change')
    print('PASS GNOME bridge shutdown releases the desktop source override')
finally:
    backend.stop()
    Gio.bus_unown_name(owner)
    connection.unregister_object(registration)
