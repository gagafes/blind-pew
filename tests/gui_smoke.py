#!/usr/bin/python3
"""GTK application + real AppIndicator + a protocol-level test panel.

The test panel checks registration and lifecycle; it is not GNOME/Xfce Shell.
IBus startup is stubbed here to avoid changing the test user's input settings.
"""
import os
import subprocess
import time
from types import SimpleNamespace
from unittest.mock import patch
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk
from blind_pew import startup, config, hotkey, i18n
from blind_pew.setup import Application
from blind_pew.catalog import PROFILE_ORDER
from blind_pew.monitor import InputMonitor

main = GLib.MainContext.default()


def wait_for(predicate, timeout=4):
    limit = time.monotonic() + timeout
    while time.monotonic() < limit:
        while main.pending():
            main.iteration(False)
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError('Timed out waiting for GUI state')


XML = '''<node><interface name="org.kde.StatusNotifierWatcher">
<method name="RegisterStatusNotifierItem"><arg type="s" direction="in"/></method>
<method name="RegisterStatusNotifierHost"><arg type="s" direction="in"/></method>
<property name="IsStatusNotifierHostRegistered" type="b" access="read"/>
<property name="RegisteredStatusNotifierItems" type="as" access="read"/>
<property name="ProtocolVersion" type="i" access="read"/>
<signal name="StatusNotifierItemRegistered"><arg type="s"/></signal>
<signal name="StatusNotifierHostRegistered"/>
</interface></node>'''


class Panel:
    def __init__(self):
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.items = []
        self.host = False
        interface = Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0]
        self.registration = self.connection.register_object('/StatusNotifierWatcher', interface,
                                                           self.method, self.prop, None)
        self.owner = None

    def start(self):
        self.owner = Gio.bus_own_name_on_connection(self.connection, 'org.kde.StatusNotifierWatcher',
                                                  Gio.BusNameOwnerFlags.NONE, None, None)

    def stop(self):
        if self.owner is not None:
            Gio.bus_unown_name(self.owner)
            self.owner = None

    def method(self, connection, sender, path, interface, name, params, invocation):
        if name == 'RegisterStatusNotifierItem':
            self.items.append((sender, params.unpack()[0]))
        invocation.return_value(None)

    def prop(self, connection, sender, path, interface, name):
        if name == 'IsStatusNotifierHostRegistered':
            return GLib.Variant('b', self.host)
        if name == 'RegisteredStatusNotifierItems':
            return GLib.Variant('as', [s + p for s, p in self.items])
        return GLib.Variant('i', 0)

    def set_host(self, present):
        self.host = present
        self.connection.emit_signal(None, '/StatusNotifierWatcher',
                                    'org.freedesktop.DBus.Properties', 'PropertiesChanged',
                                    GLib.Variant('(sa{sv}as)', ('org.kde.StatusNotifierWatcher',
                                        {'IsStatusNotifierHostRegistered': GLib.Variant('b', present)}, [])))


class TestBus:
    """IBus bus event source; engine and session-D-Bus communication stay real."""
    def __init__(self, name):
        self.name, self.connected, self.callbacks = name, True, {}
    def connect(self, signal, callback):
        ident = len(self.callbacks) + 1
        self.callbacks[ident] = signal, callback
        return ident
    def disconnect(self, ident):
        self.callbacks.pop(ident, None)
    def set_watch_ibus_signal(self, value):
        pass
    def is_connected(self):
        return self.connected
    def emit(self, signal, *args):
        for kind, callback in list(self.callbacks.values()):
            if kind == signal:
                callback(self, *args)
    def select(self, name):
        self.name = name
        self.emit('global-engine-changed', name)
    def get_global_engine_async(self, timeout, cancel, callback, data):
        snapshot = self.name
        GLib.idle_add(lambda: (callback(self, snapshot, data), False)[1])
    def get_global_engine_async_finish(self, result):
        return SimpleNamespace(get_name=lambda: result)
    def set_global_engine_async(self, name, timeout, cancel, callback, data):
        def apply():
            self.select(name)
            callback(self, True, data)
            return False
        GLib.idle_add(apply)
    def set_global_engine_async_finish(self, result):
        return result


app = Application()
errors = []
starts = []
panel = Panel()

def fake_start():
    starts.append(True)
    time.sleep(0.08)
    return startup.Result(True, False, '')


def exercise():
    try:
        wait_for(lambda: app.window is not None and not app.starting)
        assert len(starts) == 1
        assert app.window.get_visible()
        assert app.window.get_icon_name() == 'blind-pew'
        for mode, expected in [('be', 'Прывітанне! ў і ё э'),
                               ('li', 'Labas! ą č ę ė į š ų ū ž'),
                               ('ua', 'Привіт! Україна є ґ'),
                               ('ge', 'გამარჯობა! კ პ ტ ჭ'),
                               ('am', 'Բարեվ! շ ղ ժ ու և'),
                               ('il', 'שלום ף ץ ם ן ך')]:
            app.window.mode.set_active_id(mode)
            assert app.window.result.get_text() == expected, (mode, app.window.result.get_text())
            assert app.window.base.get_sensitive()
        assert app.window.result.get_direction() == Gtk.TextDirection.RTL
        wait_for(lambda: app.window.result.get_layout_offsets()[0] +
                 app.window.result.get_layout().get_pixel_extents()[0].x >
                 app.window.result.get_allocated_width() / 2)
        table = app.window.table.get_buffer()
        assert 'א' in table.get_text(table.get_start_iter(), table.get_end_iter(), True)
        app.window.preview.set_text('my own text')
        app.window.mode.set_active_id('ua')
        assert app.window.preview.get_text() == 'my own text'
        assert app.window.result.get_direction() == Gtk.TextDirection.LTR
        assert app.window.result.get_xalign() == 0
        app.window.preview.set_text('')
        app.window.mode.set_active_id('il')
        print('PASS transliteration previews; Hebrew RTL/table; preserve user-entered text')
        assert app.window.hint.get_text() == 'F12 — ' + i18n.tr('Toggle transliteration')
        assert Gio.Settings.new('org.freedesktop.ibus.general.hotkey').get_strv('triggers') == []
        assert hotkey._xfget(hotkey.XFCE_KEY) == hotkey.COMMAND
        assert Gio.Settings.new('org.freedesktop.ibus.general').get_boolean('use-global-engine')
        assert len(app.window.mode.get_model()) == 8  # 7 languages + Russian DE rules
        app.window.mode.set_active_id('ua')
        app.window.base.set_active_id('de')
        app.window.preview.set_text("my own text")
        old_monitor, old_tray = app.monitor, app.tray
        app.window.about_button.clicked()
        original_about = app.window.about
        app.show_about()
        assert app.window.about is original_about  # one dialog per window
        for language in ('de', 'uk', 'he', 'system'):
            app.window.ui_language.set_active_id(language)
            assert app.window.mode.get_active_id() == 'ua'
            assert app.window.base.get_active_id() == 'de'
            assert app.window.preview.get_text() == 'my own text'
            assert app.monitor is old_monitor and app.tray is old_tray
            assert app.tray.menu.get_children()[0].get_label() == i18n.tr('Open Blind Pew')
            assert app.window.ui_language.get_active_id() == language
            assert app.window.mode.get_active_text().startswith(i18n.tr('Ukrainian'))
            assert config.load()['ui_language'] == language
            assert app.window.about and app.window.about.get_visible()
            assert app.window.about.get_title() == i18n.tr('About')
            assert app.window.about.get_transient_for() is app.window
            assert app.window.about.get_widget_for_response(Gtk.ResponseType.CLOSE).get_label() == i18n.tr('Close')
            assert app.window.about.get_direction() == (Gtk.TextDirection.RTL if i18n.current() in i18n.RTL else Gtk.TextDirection.LTR)
            assert app.tray.menu.get_children()[-2].get_label() == i18n.tr('About')
        app.window.about.response(Gtk.ResponseType.CLOSE)
        assert app.window.about is None
        app.tray.menu.get_children()[-2].activate()
        assert app.window.about and app.window.about.get_visible()
        app.window.about.close()
        wait_for(lambda: app.window.about is None)
        app._started(startup.Result(True, False, 'Custom configuration preserved'))
        assert app.window.status.get_text() == 'Custom configuration preserved'
        print('PASS translated About: button/tray access, one dialog, live language, RTL and close; startup diagnostics')
        print('PASS transliteration-only UI; live German/Ukrainian/Hebrew/system language; input state preserved')
        assert not app.tray.available()
        assert not app.hide_window()
        assert app.window.get_visible()
        app.window.on_close()
        assert app.window.get_visible()
        print('PASS missing panel: close/hide cannot strand the window')

        panel.start()
        wait_for(lambda: app.tray.host_proxy is not None)
        assert not app.tray.available()
        assert not app.hide_window()
        panel.set_host(True)
        wait_for(lambda: app.tray.available() and bool(panel.items))
        assert panel.items
        app.show_about()
        assert app.hide_window()
        assert app.window.about is None
        assert not app.window.get_visible()
        app.tray.menu.get_children()[0].activate()
        assert app.window.get_visible()
        app.window.on_close()
        assert not app.window.get_visible()
        app.show_window()
        app.window.on_window_state(app.window, SimpleNamespace(
            changed_mask=Gdk.WindowState.ICONIFIED, new_window_state=Gdk.WindowState.ICONIFIED))
        assert not app.window.get_visible()
        print('PASS real AppIndicator registration; tray menu, close and minimize hide/restore')

        app.monitor.stop()
        test_bus = TestBus('blind-pew:ru:us')
        app.monitor = InputMonitor(app.tray.set_input, bus=test_bus, source_changed=app.source_changed)
        app.desktop.bus = test_bus
        wait_for(lambda: app.tray.country == 'RU')
        from pathlib import Path
        cached = Path(app.tray.icon_path)
        victim = cached.parent / 'unrelated.txt'
        victim.write_text('do not overwrite')
        cached.unlink()
        cached.symlink_to(victim)
        app.tray.country = None
        app.tray.set_input('RU', 'regenerated icon')
        assert victim.read_text() == 'do not overwrite'
        assert not cached.is_symlink()
        assert cached.read_text().startswith('<svg')
        print('PASS tray cache symlink replaced without touching target')
        for name, country in [('ua', 'UA'), ('be', 'BY'), ('li', 'LT'), ('ge', 'GE'), ('am', 'AM'), ('il', 'IL')]:
            test_bus.select(f'blind-pew:{name}:us')
            wait_for(lambda: app.tray.country == country)
            assert app.tray.indicator.get_icon() == app.tray.icon_path
            assert country in app.tray.source_item.get_label()
        test_bus.select('xkb:de::ger')
        wait_for(lambda: app.tray.country == 'DE')
        test_bus.select('blind-pew:ua:de')
        wait_for(lambda: app.tray.country == 'UA')
        test_bus.select('xkb:lt:std:lit')
        wait_for(lambda: app.tray.country == 'LT')
        test_bus.connected = False
        test_bus.emit('disconnected')
        assert app.tray.country is None
        test_bus.connected = True
        test_bus.emit('connected')
        wait_for(lambda: app.tray.country == 'LT')
        print('PASS active global source, native/translit country indicators and reconnect')

        test_bus.select('xkb:de::ger')
        wait_for(lambda: app.tray.country == 'DE')
        sender, path = panel.items[-1]
        def scroll(delta, orientation='vertical'):
            replies = []
            def done(conn, result):
                replies.append(conn.call_finish(result))
            panel.connection.call(sender, path, 'org.kde.StatusNotifierItem', 'Scroll',
                GLib.Variant('(is)', (delta, orientation)), None, Gio.DBusCallFlags.NONE, 2000, None, done)
            wait_for(lambda: bool(replies))
        # Both directions toggle the same chosen language, including Russian DE.
        for base in ('us', 'de'):
            app.window.base.set_active_id(base)
            for ident in PROFILE_ORDER:
                app.window.mode.set_active_id(ident)
                app.window.on_add()
                selected = f'blind-pew:{ident}:{base}'
                wait_for(lambda: test_bus.name == selected and not app.switches.inflight)
                for delta, expected in ((-120, 'xkb:de::ger'), (-120, selected),
                                        (120, 'xkb:de::ger'), (120, selected)):
                    scroll(delta)
                    wait_for(lambda: test_bus.name == expected and not app.switches.inflight)
                    assert config.load()['favorite_profile'] == ident
                    assert config.load()['favorite_base'] == base
                    assert app.window.mode.get_active_id() == ident
        scroll(120, 'horizontal')
        scroll(0)
        assert test_bus.name == selected
        # Consecutive events arrive before the async first switch completes.
        for direction in (Gdk.ScrollDirection.DOWN, Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN):
            app.tray.indicator.emit('scroll-event', 1, direction)
        wait_for(lambda: test_bus.name == 'xkb:de::ger' and not app.switches.inflight)
        assert app.tray.icon_path.endswith('.svg')
        assert app.tray.country == 'DE'
        if app.tray.xembed:
            for direction, expected in ((Gdk.ScrollDirection.UP, selected),
                                        (Gdk.ScrollDirection.DOWN, 'xkb:de::ger')):
                event = Gdk.Event.new(Gdk.EventType.SCROLL)
                event.direction = direction
                app.tray.xembed.emit('scroll-event', event)
                wait_for(lambda: test_bus.name == expected and not app.switches.inflight)
        print('PASS real SNI wheel and XEmbed events: on/off, both directions, all profiles/bases, rapid events and SVG')

        test_bus.select('xkb:de::ger')
        wait_for(lambda: app.tray.country == 'DE')
        app.window.mode.set_active_id('ua')
        app.window.on_add()
        wait_for(lambda: test_bus.name == 'blind-pew:ua:de' and not app.switches.inflight)
        assert app.hide_window()
        for expected in ('xkb:de::ger', 'blind-pew:ua:de', 'xkb:de::ger', 'blind-pew:ua:de'):
            child = subprocess.Popen(['/usr/bin/python3', '-m', 'blind_pew.cli', 'toggle'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            wait_for(lambda: child.poll() is not None)
            out, err = child.communicate()
            assert child.returncode == 0, (out, err)
            wait_for(lambda: test_bus.name == expected and not app.switches.inflight)
            assert not app.window.get_visible(), 'F12 must not open preferences'
        scroll(-120)
        wait_for(lambda: test_bus.name == 'xkb:de::ger' and not app.switches.inflight)
        app.activate_action('toggle', None)
        wait_for(lambda: test_bus.name == 'blind-pew:ua:de' and not app.switches.inflight)
        scroll(120)
        wait_for(lambda: test_bus.name == 'xkb:de::ger' and not app.switches.inflight)
        app.activate_action('toggle', None)
        wait_for(lambda: test_bus.name == 'blind-pew:ua:de' and not app.switches.inflight)
        assert config.load()['favorite_profile'] == 'ua'
        assert not app.window.get_visible()
        print('PASS real remote F12 action and alternating wheel: same on/off pair, retained language, no window focus')

        # A second process must activate the existing window and exit.
        child = subprocess.Popen(['/usr/bin/python3', '-m', 'blind_pew.cli', 'setup'],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        wait_for(lambda: child.poll() is not None, timeout=5)
        out, err = child.communicate()
        assert child.returncode == 0, (out, err)
        assert app.window.get_visible()
        assert len(starts) == 1
        print('PASS second process reopens same application; no second IBus startup')

        app.hide_window()
        panel.stop()
        wait_for(lambda: not app.tray.available() and app.window.get_visible())
        print('PASS panel disappearance restores hidden window')
        panel.start()
        wait_for(lambda: app.tray.available())
        wait_for(lambda: i18n.tr('Close or minimize to hide in the tray.') in app.window.tray_status.get_text())
        painted = time.monotonic() + 0.1
        wait_for(lambda: time.monotonic() >= painted)
        target = os.environ.get('BLIND_PEW_TEST_SCREENSHOT')
        if target:
            image = Gdk.pixbuf_get_from_window(app.window.get_window(), 0, 0,
                                              app.window.get_allocated_width(), app.window.get_allocated_height())
            image.savev(target, 'png', [], [])
        app.tray.menu.get_children()[-1].activate()
        print('PASS explicit tray Quit')
    except Exception as error:
        errors.append(error)
        app.quit()
    return GLib.SOURCE_REMOVE


with patch.object(startup, 'ensure_ibus', fake_start):
    GLib.idle_add(exercise)
    app.run(['blind-pew'])
panel.stop()
assert app.closing
assert not config.load()['hotkey_backup']
assert not config.load()['session_backup']
if errors:
    raise errors[0]
print('ALL GUI / TRAY CHECKS PASSED')
