# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Activate global input sources through GNOME or IBus."""
import subprocess
from gi.repository import Gio, GLib
from . import integration
from .i18n import tr

GNOME_INTERFACE = 'org.blindpew.Desktop'
GNOME_PATH = '/org/blindpew/Desktop'
GNOME_UUID = 'blind-pew@local'


def enable_gnome_extension():
    """Called in the setup worker after install; never turn off Shell safeguards."""
    if not integration.is_gnome():
        return ''
    try:
        result = subprocess.run(['gnome-extensions', 'enable', GNOME_UUID],
                                capture_output=True, text=True, timeout=4)
        if result.returncode == 0:
            return ''
    except (OSError, subprocess.TimeoutExpired):
        pass
    return tr('Enable {name}.', name='Blind Pew Integration') + ' ' + tr('Log out and back in after installation.')


class DesktopBackend:
    def __init__(self, bus, source_changed):
        self.bus, self.source_changed = bus, source_changed
        self.gnome = integration.is_gnome()
        self.stopped = False
        self.proxy = None
        self.handlers = []
        self.generation = 0
        self.cancel = Gio.Cancellable()
        if self.gnome:
            Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_AUTO_START,
                None, 'org.gnome.Shell', GNOME_PATH, GNOME_INTERFACE, self.cancel, self._proxy_ready)

    def _proxy_ready(self, source, result):
        try:
            proxy = Gio.DBusProxy.new_for_bus_finish(result)
        except GLib.Error:
            return
        if self.stopped:
            return
        self.proxy = proxy
        self.handlers = [proxy.connect('g-signal', self._signal),
                         proxy.connect('notify::g-name-owner', lambda *_: self.refresh())]
        self.refresh()

    def _state(self, values):
        if self.stopped:
            return
        kind, ident = values
        self.source_changed((kind, ident) if kind and ident else None)

    def _signal(self, proxy, sender, name, params):
        if name == 'StateChanged':
            self.generation += 1
            self._state(params.unpack())

    def refresh(self):
        if self.stopped:
            return
        if not self.proxy:
            return
        self.generation += 1
        generation = self.generation
        def done(proxy, result):
            try:
                values = proxy.call_finish(result).unpack()
            except GLib.Error:
                if not self.stopped and generation == self.generation:
                    self.source_changed(None)
                return
            if generation == self.generation:
                self._state(values)
        self.proxy.call('GetState', None, Gio.DBusCallFlags.NONE, 1200, self.cancel, done)

    def activate(self, source, callback):
        if self.stopped:
            return
        kind, name = source
        if kind not in ('ibus', 'xkb') or not name:
            callback(False, tr('Unknown input source'))
            return
        try:
            if kind == 'ibus' and name.startswith('blind-pew:'):
                integration.add_engine(name)
        except (OSError, ValueError, RuntimeError) as error:
            callback(False, str(error))
            return
        if self.gnome:
            if not self.proxy:
                callback(False, tr('Enable {name}.', name='Blind Pew Integration') + ' ' + tr('Log out and back in after installation.'))
                return
            def attempt(number=0):
                if self.stopped:
                    return False
                def done(proxy, result):
                    if self.stopped:
                        return
                    try:
                        ok, = proxy.call_finish(result).unpack()
                    except GLib.Error:
                        callback(False, tr('Enable {name}.', name='Blind Pew Integration') + ' ' + tr('Log out and back in after installation.'))
                        return
                    if not ok and number < 4:
                        GLib.timeout_add(100, lambda: (attempt(number + 1), False)[1])
                    else:
                        callback(ok, '' if ok else tr('Log out and back in after installation.'))
                self.proxy.call('Activate', GLib.Variant('(ss)', (kind, name)),
                                Gio.DBusCallFlags.NONE, 1500, self.cancel, done)
                return False
            attempt()
        else:
            if not self.bus.is_connected():
                callback(False, tr('IBus: not running'))
                return
            def done(bus, result, *_):
                if self.stopped:
                    return
                try:
                    ok = bus.set_global_engine_async_finish(result)
                    callback(ok, '' if ok else tr('Log out and back in after installation.'))
                except GLib.Error as error:
                    callback(False, str(error))
            self.bus.set_global_engine_async(name, 2000, self.cancel, done, None)

    def stop(self):
        self.stopped = True
        self.cancel.cancel()
        if self.proxy:
            for handler in self.handlers:
                self.proxy.disconnect(handler)
        self.handlers.clear()
        self.proxy = None
        self.bus = None
