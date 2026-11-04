# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Event-driven active input-source monitor."""
import gi
gi.require_version('IBus', '1.0')
from gi.repository import Gio, GLib, IBus
from .catalog import country_for, profile_title
from .i18n import tr
from . import integration


class InputMonitor:
    def __init__(self, changed, bus=None, source_changed=lambda source: None):
        self.changed = changed
        self.source_changed = source_changed
        self.desktop_source = None
        self.last_source = None
        self.stopped = False
        self.name = ''
        self.generation = 0
        self.cancel = Gio.Cancellable()
        self.last = None
        self.settings = None
        self.settings_handler = None
        if integration.is_gnome():
            try:
                self.settings = integration._settings('org.gnome.desktop.input-sources')
                self.settings_handler = self.settings.connect('changed', lambda *_: self._render())
            except RuntimeError:
                pass
        IBus.init()
        self.owns_bus = bus is None
        self.bus = bus or IBus.Bus.new_async()
        self.bus.set_watch_ibus_signal(True)
        self.handlers = [self.bus.connect('connected', lambda *_: self.refresh()),
                         self.bus.connect('disconnected', self._disconnected),
                         self.bus.connect('global-engine-changed', self._engine_changed)]
        self.refresh()

    def refresh(self):
        if self.stopped:
            return
        self.generation += 1
        generation = self.generation
        if not self.bus.is_connected():
            self.name = ''
            self._render()
            return
        def done(bus, result, *_):
            try:
                engine = bus.get_global_engine_async_finish(result)
                name = engine.get_name() if engine else ''
            except GLib.Error:
                name = ''
            if not self.stopped and generation == self.generation:
                self.name = name
                self._render()
        self.bus.get_global_engine_async(1200, self.cancel, done, None)

    def _engine_changed(self, bus, name):
        self.generation += 1
        self.name = name
        self._render()

    def _disconnected(self, *_):
        self.generation += 1
        self.name = ''
        self._render()

    def _render(self):
        if self.stopped:
            return
        source_type, source_id = 'ibus', self.name
        if self.desktop_source:
            source_type, source_id = self.desktop_source
        elif self.settings and self.name.startswith('xkb:'):
            # GNOME uses xkb:us::eng as an echo engine for ALL ordinary XKB
            # sources. Its engine name cannot identify their actual country.
            mru = self.settings.get_value('mru-sources').unpack()
            if not self.settings.get_boolean('per-window') and mru and mru[0][0] == 'xkb':
                source_type, source_id = mru[0]
            else:
                sources = self.settings.get_value('sources').unpack()
                native = [s for s in sources if s[0] == 'xkb']
                source_type, source_id = native[0] if len(native) == 1 else ('', '')
        source = (source_type, source_id) if source_id else None
        if source != self.last_source:
            self.last_source = source
            self.source_changed(source)
        country = country_for(source_type, source_id)
        name = country or tr('Unknown')
        if source_type == 'ibus' and source_id.startswith('blind-pew:'):
            parts = source_id.split(':')
            try:
                name = profile_title(parts[1])
            except (KeyError, IndexError):
                pass
        detail = tr('Current layout') + ': ' + name
        if country:
            detail += ' (' + country + ')' 
        value = country, detail
        if value != self.last:
            self.last = value
            self.changed(*value)

    def set_desktop_source(self, source):
        self.desktop_source = source
        self._render()

    def stop(self):
        self.stopped = True
        self.cancel.cancel()
        for handler in self.handlers:
            self.bus.disconnect(handler)
        self.handlers.clear()
        if self.settings_handler:
            self.settings.disconnect(self.settings_handler)
        if self.owns_bus:
            self.bus.destroy()
        self.changed = lambda *args: None
        self.source_changed = lambda source: None
