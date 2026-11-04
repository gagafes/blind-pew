# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""SNI/AppIndicator on panels and an XEmbed tray icon on X11."""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import AyatanaAppIndicator3 as Indicator
from gi.repository import Gdk, Gio, GLib, Gtk
from pathlib import Path
import os
import re
import tempfile
from .i18n import tr


class Tray:
    def __init__(self, show, hide, retry, quit_app, changed, about, toggle):
        self.changed = changed
        self.toggle = toggle
        self.using_sni = False
        self.stopped = False
        self.host_owner = None
        self.host_proxy = None
        self.xembed = None
        self.country = None
        self.ibus_ready = None
        self.icon_path = None
        self.menu = Gtk.Menu()
        for label, callback in [(tr('Open Blind Pew'), show), (tr('Hide to tray'), hide)]:
            self._item(label, callback)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.source_item = self._item(tr('Current layout'), None)
        self.status_item = self._item(tr('IBus: checking…'), None)
        self._item(tr('Check and start IBus'), retry)
        self.menu.append(Gtk.SeparatorMenuItem())
        self._item(tr('About'), about)
        self._item(tr('Quit'), quit_app)
        self.menu.show_all()
        self.indicator = Indicator.Indicator.new(
            'blind-pew', 'blind-pew', Indicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_title('Blind Pew')
        self.indicator.set_menu(self.menu)
        self.indicator.set_status(Indicator.IndicatorStatus.PASSIVE)
        self.indicator.connect('connection-changed', lambda *_: self._changed())
        self.indicator.connect('scroll-event', self._indicator_scroll)
        display = Gdk.Display.get_default()
        if display and 'X11' in display.__gtype__.name:
            self.xembed = Gtk.StatusIcon.new_from_icon_name('blind-pew')
            self.xembed.set_visible(False)
            self.xembed.set_tooltip_text('Blind Pew')
            self.xembed.connect('activate', lambda *_: show())
            self.xembed.connect('popup-menu', self._popup)
            self.xembed.connect('notify::embedded', lambda *_: self._changed())
            self.xembed.connect('scroll-event', self._xembed_scroll)
        self.watch = Gio.bus_watch_name(Gio.BusType.SESSION, 'org.kde.StatusNotifierWatcher',
                                       Gio.BusNameWatcherFlags.NONE,
                                       self._appeared, self._vanished)

    def _item(self, label, callback):
        item = Gtk.MenuItem(label=label)
        if callback is None:
            item.set_sensitive(False)
        else:
            item.connect('activate', lambda *_: callback())
        self.menu.append(item)
        return item

    def _popup(self, icon, button, activate_time):
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, activate_time)

    def _indicator_scroll(self, indicator, steps, direction):
        if not self.stopped and steps and direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN):
            self.toggle()

    def _xembed_scroll(self, icon, event):
        if self.stopped:
            return False
        if event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN):
            self.toggle()
            return True
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if ok and abs(dy) > abs(dx) and dy:
                self.toggle()
                return True
        return False

    def _appeared(self, connection, name, owner):
        if self.stopped:
            return
        self.host_owner = owner
        def ready(source, result):
            try:
                proxy = Gio.DBusProxy.new_finish(result)
            except GLib.Error:
                return
            if self.stopped or self.host_owner != owner:
                return
            self.host_proxy = proxy
            proxy.connect('g-properties-changed', lambda *_: self._host_changed(proxy, owner))
            self._host_changed(proxy, owner)
        Gio.DBusProxy.new(connection, Gio.DBusProxyFlags.DO_NOT_AUTO_START, None,
                          owner, '/StatusNotifierWatcher', 'org.kde.StatusNotifierWatcher', None, ready)

    def _host_changed(self, proxy, owner):
        if self.stopped or self.host_owner != owner:
            return
        value = proxy.get_cached_property('IsStatusNotifierHostRegistered')
        self.using_sni = bool(value and value.unpack())
        if self.xembed:
            self.xembed.set_visible(not self.using_sni)
        self.indicator.set_status(Indicator.IndicatorStatus.ACTIVE if self.using_sni
                                  else Indicator.IndicatorStatus.PASSIVE)
        self._changed()

    def _vanished(self, connection, name):
        if self.stopped:
            return
        self.host_owner = None
        self.host_proxy = None
        self.using_sni = False
        # Disable Ayatana's own xembed fallback, so exactly one icon is shown.
        self.indicator.set_status(Indicator.IndicatorStatus.PASSIVE)
        if self.xembed:
            self.xembed.set_visible(True)
        self._changed()

    def available(self):
        if self.stopped:
            return False
        if self.using_sni:
            return bool(self.indicator.get_property('connected'))
        return bool(self.xembed and self.xembed.get_visible() and self.xembed.is_embedded())

    def _changed(self):
        if not self.stopped:
            self.changed(self.available())

    def retranslate(self):
        items = self.menu.get_children()
        for index, message in ((0, 'Open Blind Pew'), (1, 'Hide to tray'),
                               (5, 'Check and start IBus'), (7, 'About'), (8, 'Quit')):
            items[index].set_label(tr(message))
        if self.ibus_ready is not None:
            self.set_ibus_status(self.ibus_ready)
        else:
            self.status_item.set_label(tr('IBus: checking…'))

    def set_ibus_status(self, ready):
        self.ibus_ready = ready
        self.status_item.set_label(tr('IBus: running') if ready else tr('IBus: not running'))

    def set_input(self, country, detail):
        if self.stopped:
            return
        self.source_item.set_label(detail)
        self.indicator.set_title('Blind Pew — ' + detail)
        if self.xembed:
            self.xembed.set_tooltip_text('Blind Pew — ' + detail)
        if country == self.country:
            return
        self.country = country
        if not country or not re.fullmatch(r'[A-Z]{2,4}', country):
            self.icon_path = None
            self.indicator.set_icon_full('blind-pew', detail)
            if self.xembed:
                self.xembed.set_from_icon_name('blind-pew')
            return
        directory = Path(GLib.get_user_cache_dir()) / 'blind-pew' / 'icons'
        try:
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = directory / ('country-' + country + '-011B46-FEE5AF.svg')
            size = 34 if len(country) == 2 else 25 if len(country) == 3 else 20
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
                       '<rect x="2" y="2" width="60" height="60" rx="13" fill="#011B46"/>'
                       f'<text x="32" y="44" text-anchor="middle" font-family="sans-serif" '
                       f'font-weight="bold" font-size="{size}" fill="#FEE5AF">{country}</text></svg>')
            # Never follow a pre-existing cache symlink or display cached SVG
            # contents supplied by another process. Publish only our own icon.
            fd, temp = tempfile.mkstemp(prefix='.country-', dir=directory)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                    handle.write(svg)
                os.replace(temp, path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)
            self.icon_path = str(path)
            self.indicator.set_icon_full(self.icon_path, detail)
            if self.xembed:
                self.xembed.set_from_file(self.icon_path)
        except OSError:
            self.country = None
            self.indicator.set_icon_full('blind-pew', detail)

    def stop(self):
        self.stopped = True
        Gio.bus_unwatch_name(self.watch)
        self.indicator.set_status(Indicator.IndicatorStatus.PASSIVE)
        if self.xembed:
            self.xembed.set_visible(False)
