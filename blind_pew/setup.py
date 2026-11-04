# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Compact GTK preferences for transliteration; IBus handles application input."""
import threading
import signal
import sys
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango
from . import __version__, AUTHOR, EMAIL, config, integration, startup, desktop, hotkey, i18n
from .i18n import tr
from .core import convert, profiles
from .catalog import profile_title, source_for, PROFILE_ORDER, LANGUAGE_NAMES
from .switching import SwitchQueue, TogglePair, is_translit


class AboutDialog(Gtk.Dialog):
    """All visible copy uses the same offline catalog as the main window."""
    def __init__(self, parent):
        super().__init__(title=tr('About'), transient_for=parent,
                         destroy_with_parent=True, modal=True, use_header_bar=False)
        self.get_style_context().add_class('blind-pew')
        self.set_icon_name('blind-pew')
        self.set_resizable(False)
        self.add_button(tr('Close'), Gtk.ResponseType.CLOSE)
        self.connect('response', lambda dialog, _response: dialog.destroy())
        box = self.get_content_area()
        box.set_border_width(20)
        box.set_spacing(10)
        logo = Path(__file__).resolve().parent.parent / 'docs' / 'blind-pew-logo.png'
        image = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(logo), 192, 192, True))
        image.get_accessible().set_name('Blind Pew')
        box.add(image)
        for text in (tr('Version') + ': ' + __version__,
                     tr('Author') + ': ' + AUTHOR,
                     tr('Transliteration') + ' · ' + tr('Offline'),
                     tr('Languages') + ': ' + ', '.join(tr(name) for name in LANGUAGE_NAMES.values()),
                     'F12 — ' + tr('Toggle transliteration'),
                     tr('License') + ': MIT'):
            label = Gtk.Label(label=text, justify=Gtk.Justification.CENTER)
            label.set_line_wrap(True)
            label.set_max_width_chars(46)
            label.set_selectable(True)
            box.add(label)
        contact = Gtk.LinkButton.new_with_label('mailto:' + EMAIL, EMAIL)
        contact.set_halign(Gtk.Align.CENTER)
        box.add(contact)


class Window(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title='Blind Pew')
        self.get_style_context().add_class('blind-pew')
        self.controller = application
        self.about = None
        self.set_icon_name('blind-pew')
        self.set_default_size(700, 650)
        self.set_border_width(12)
        self.connect('delete-event', self.on_close)
        self.connect('window-state-event', self.on_window_state)
        options = config.load()
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(root)
        outer = Gtk.ScrolledWindow()
        outer.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.pack_start(outer, True, True, 0)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_border_width(8)
        outer.add(box)
        title = Gtk.Label(xalign=0)
        title.set_markup('<span size="x-large" weight="bold">Blind Pew</span>')
        box.pack_start(title, False, False, 0)
        box.pack_start(Gtk.Label(label=tr('Transliteration') + ' · ' + tr('Languages') + ': 7 · ' + tr('Offline'), xalign=0), False, False, 0)
        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        box.pack_start(grid, False, False, 0)
        self.ui_language = Gtk.ComboBoxText()
        self.ui_language.append('system', tr('System language'))
        for code, name in i18n.LANGUAGES:
            self.ui_language.append(code, name)
        self.ui_language.set_active_id(options['ui_language'])
        self.ui_language.connect('changed', self.on_language)
        self.mode = Gtk.ComboBoxText()
        for ident in PROFILE_ORDER:
            self.mode.append(ident, profile_title(ident))
        self.base = Gtk.ComboBoxText()
        self.base.append('us', 'QWERTY — ' + tr('English (US)'))
        self.base.append('de', 'QWERTZ — ' + tr('German'))
        self.base.set_active_id(options['favorite_base'])
        for row, (label, widget) in enumerate((('Interface language', self.ui_language),
                ('Layout', self.mode), ('Keyboard base', self.base))):
            grid.attach(Gtk.Label(label=tr(label), xalign=0), 0, row, 1, 1)
            widget.set_hexpand(True)
            grid.attach(widget, 1, row, 1, 1)
        apply_button = Gtk.Button(label=tr('Apply'))
        apply_button.connect('clicked', self.on_add)
        grid.attach(apply_button, 1, 3, 1, 1)
        self.wheel_status = Gtk.Label(label=tr('Mouse wheel over tray icon') + ': ' +
            tr('Toggle transliteration'), xalign=0)
        self.wheel_status.set_line_wrap(True)
        box.pack_start(self.wheel_status, False, False, 0)
        self.hint = Gtk.Label(label='F12 — ' + tr('Toggle transliteration'), xalign=0)
        self.hint.set_line_wrap(True)
        box.pack_start(self.hint, False, False, 0)
        self.ibus_status = Gtk.Label(label=tr('IBus: checking…'), xalign=0)
        self.ibus_status.set_line_wrap(True)
        box.pack_start(self.ibus_status, False, False, 0)
        box.pack_start(Gtk.Separator(), False, False, 0)
        self.preview_label = Gtk.Label(label=tr('Type Latin text:'), xalign=0)
        box.pack_start(self.preview_label, False, False, 0)
        self.preview = Gtk.Entry()
        self.preview.set_max_length(2000)
        self.sample = ''
        self.preview.set_direction(Gtk.TextDirection.LTR)
        self.preview.set_property('im-module', 'gtk-im-context-simple')
        self.preview.connect('changed', self.on_preview)
        box.pack_start(self.preview, False, False, 0)
        self.result = Gtk.Label(xalign=0)
        self.result.set_selectable(True)
        self.result.set_line_wrap(True)
        box.pack_start(self.result, False, False, 0)
        expander = Gtk.Expander(label=tr('Input table'))
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(140)
        self.table = Gtk.TextView(editable=False, cursor_visible=False, monospace=True)
        self.table.set_direction(Gtk.TextDirection.LTR)
        self.table.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroll.add(self.table)
        expander.add(scroll)
        box.pack_start(expander, True, True, 0)
        self.status = Gtk.Label(xalign=0)
        self.status.set_line_wrap(True)
        root.pack_start(self.status, False, False, 0)
        self.tray_status = Gtk.Label(label=tr('Tray: connecting…'), xalign=0)
        self.tray_status.set_line_wrap(True)
        root.pack_start(self.tray_status, False, False, 0)
        bottom = Gtk.Box(spacing=8)
        self.about_button = Gtk.Button(label=tr('About'))
        self.about_button.connect('clicked', lambda *_: self.controller.show_about())
        bottom.pack_start(self.about_button, False, False, 0)
        for label, callback in [('Quit', self.controller.quit), ('Hide to tray', self.controller.hide_window)]:
            button = Gtk.Button(label=tr(label))
            button.connect('clicked', lambda _button, callback=callback: callback())
            bottom.pack_end(button, False, False, 0)
        root.pack_start(bottom, False, False, 0)
        self.mode.connect('changed', self.on_mode)
        favorite = options['favorite_profile'] if options['favorite_profile'] in profiles() else 'ru'
        self.mode.set_active_id(favorite)

    def show_about(self):
        if self.about is None:
            self.about = AboutDialog(self)
            self.about.connect('destroy', self.on_about_destroy)
        self.about.show_all()
        self.about.present()

    def on_about_destroy(self, *_):
        self.about = None

    def on_language(self, *_):
        self.controller.set_language(self.ui_language.get_active_id())

    def message(self, value):
        self.status.set_text(value)

    def on_close(self, *_):
        self.controller.hide_window()
        return True

    def on_window_state(self, window, event):
        if event.changed_mask & Gdk.WindowState.ICONIFIED and event.new_window_state & Gdk.WindowState.ICONIFIED:
            self.controller.hide_window()
        return False

    def on_preview(self, *_):
        ident = self.mode.get_active_id()
        if ident:
            self.result.set_text(convert(self.preview.get_text(), ident))

    def on_mode(self, *_):
        ident = self.mode.get_active_id()
        if not ident:
            return
        profile = profiles()[ident]
        self.result.set_direction(Gtk.TextDirection.RTL if profile['direction'] == 'rtl' else Gtk.TextDirection.LTR)
        self.result.set_xalign(0)
        rows = [f'\u2066{source}\u2069 → \u2068{target}\u2069' for target, source in profile['reverse'].items() if not target.isupper()]
        self.table.get_buffer().set_text('   '.join(rows) + '\n\n' + tr('Examples') + ':\n' +
                                       profile['sample'] + ' → ' + convert(profile['sample'], ident))
        if self.preview.get_text() in ('', self.sample):
            self.preview.set_text(profile['sample'])
        self.sample = profile['sample']
        self.on_preview()

    def on_add(self, *_):
        ident, base = self.mode.get_active_id(), self.base.get_active_id()
        if not ident:
            return
        try:
            self.controller.select_source(source_for(ident, base))
            self.message(tr('Saved') + ': ' + profile_title(ident))
        except (RuntimeError, OSError, ValueError) as error:
            self.message(str(error))


class Application(Gtk.Application):
    def __init__(self):
        i18n.configure(config.load()['ui_language'])
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL if i18n.current() in i18n.RTL else Gtk.TextDirection.LTR)
        super().__init__(application_id='org.blindpew.App', flags=Gio.ApplicationFlags.FLAGS_NONE)
        font = Pango.FontDescription.from_string(Gtk.Settings.get_default().get_property('gtk-font-name'))
        size = (font.get_size() / Pango.SCALE or 10) * 1.2
        unit = 'px' if font.get_size_is_absolute() else 'pt'
        self.font_style = Gtk.CssProvider()
        self.font_style.load_from_data(
            f'.blind-pew, .blind-pew * {{ font-size: {size:g}{unit}; }}'.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self.font_style,
                                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = self.tray = self.monitor = self.desktop = self.switches = None
        self.starting = self.closing = False
        self.last_startup = None
        options = config.load()
        self.pair = TogglePair(source_for(options['favorite_profile'], options['favorite_base']))
        action = Gio.SimpleAction.new('toggle', None)
        action.connect('activate', lambda *_: self.toggle())
        self.add_action(action)

    def do_activate(self):
        if self.window is None:
            self.hold()
            self.window = Window(self)
            try:
                from .tray import Tray
                self.tray = Tray(self.show_window, self.hide_window, self.start_ibus, self.quit,
                                 self.tray_changed, self.show_about, self.toggle)
            except (ImportError, ValueError, GLib.Error) as error:
                self.window.tray_status.set_text(tr('Error') + ': ' + str(error))
            from .monitor import InputMonitor
            self.switches = SwitchQueue(lambda source, done: self.desktop.activate(source, done),
                                        lambda message: self.window.message(message))
            self.monitor = InputMonitor(lambda *args: self.tray and self.tray.set_input(*args),
                                        source_changed=self.source_changed)
            self.desktop = desktop.DesktopBackend(self.monitor.bus, self.monitor.set_desktop_source)
            self.start_ibus()
        self.show_window()

    def set_language(self, choice):
        if not self.window or choice == config.load()['ui_language']:
            return
        try:
            config.update(ui_language=choice)
        except (OSError, ValueError) as error:
            self.window.message(tr('Error') + ': ' + str(error))
            return
        old = self.window
        about_open = bool(old.about and old.about.get_visible())
        snapshot = (old.mode.get_active_id(), old.base.get_active_id(), old.preview.get_text(),
                    old.get_size())
        i18n.configure(choice)
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL if i18n.current() in i18n.RTL else Gtk.TextDirection.LTR)
        self.window = Window(self)
        ident, base, preview, size = snapshot
        self.window.mode.set_active_id(ident)
        self.window.base.set_active_id(base)
        self.window.preview.set_text(preview)
        self.window.resize(*size)
        old.destroy()
        if self.tray:
            self.tray.retranslate()
        if self.monitor:
            self.monitor.last = None
            self.monitor._render()
        self.render_startup()
        self.tray_changed(bool(self.tray and self.tray.available()))
        self.show_window()
        if about_open:
            self.show_about()

    def source_changed(self, source):
        # GNOME's IBus xkb echo is not the actual desktop layout.
        if not integration.is_gnome() or source and source[0] == 'xkb':
            self.pair.observed(source)
        self.switches.observed(source)

    def toggle(self):
        if not self.switches or self.closing:
            return
        try:
            current = self.switches.target
            fallback = None
            if is_translit(current) and self.pair.normal is None:
                fallback = integration.normal_source(config.load()['favorite_base'])
            self.switches.request(self.pair.target(current, fallback))
        except (RuntimeError, OSError, ValueError) as error:
            self.window.message(str(error))

    def select_source(self, source):
        _, ident, base = source[1].split(':')
        config.update(favorite_profile=ident, favorite_base=base)
        self.pair.selected = source
        self.window.mode.set_active_id(ident)
        self.window.base.set_active_id(base)
        self.switches.request(source)

    def show_window(self):
        if self.window and not self.closing:
            self.window.show_all()
            self.window.deiconify()
            self.window.present()

    def show_about(self):
        if self.window and not self.closing:
            self.show_window()
            self.window.show_about()

    def hide_window(self):
        if self.tray and self.tray.available():
            if self.window.about:
                self.window.about.destroy()
            self.window.hide()
            return True
        self.tray_changed(False)
        return False

    def tray_changed(self, available):
        if not self.window or self.closing:
            return
        if available:
            text = tr('Close or minimize to hide in the tray.')
        else:
            text = (tr('Enable {name}.', name='GNOME AppIndicator and KStatusNotifierItem Support')
                if integration.is_gnome() else tr('Add {name} to the panel.', name='Xfce Status Tray Plugin'))
            text += ' ' + tr('The window stays open while no tray icon is available.')
            if not self.window.get_visible():
                self.show_window()
        self.window.tray_status.set_text(text)

    def start_ibus(self):
        if self.starting or self.closing:
            return
        self.starting = True
        self.window.ibus_status.set_text(tr('IBus: checking…'))
        def worker():
            try:
                result = startup.ensure_ibus()
                notice = desktop.enable_gnome_extension()
                if notice:
                    result = startup.Result(result.ready, True, result.message + ' ' + notice)
            except Exception as error:
                result = startup.Result(False, False, tr('Error') + ': ' + str(error))
            GLib.idle_add(self._started, result)
        threading.Thread(target=worker, name='ibus-startup', daemon=True).start()

    def render_startup(self):
        result = self.last_startup
        text = tr('IBus: checking…') if result is None else tr('IBus: running' if result.ready else 'IBus: not running')
        if result and result.needs_login:
            text += '. ' + tr('Log out and back in after installation.')
            if integration.is_gnome():
                text += ' ' + tr('Enable {name}.', name='Blind Pew Integration')
        self.window.ibus_status.set_text(text)

    def _started(self, result):
        self.starting = False
        self.last_startup = result
        if not self.closing:
            self.render_startup()
            if result.message:
                self.window.message(result.message)
            if self.tray:
                self.tray.set_ibus_status(result.ready)
            if self.monitor:
                self.monitor.refresh()
            if result.ready:
                try:
                    integration.configure_session()
                    try:
                        hotkey.install()
                    except (OSError, ValueError, RuntimeError):
                        integration.restore_session()
                        raise
                except (OSError, ValueError, RuntimeError) as error:
                    self.window.message(str(error))
            if self.desktop:
                self.desktop.refresh()
        return GLib.SOURCE_REMOVE

    def do_shutdown(self):
        self.closing = True
        for component in (self.switches, self.desktop, self.monitor, self.tray):
            if component:
                component.stop()
        for restore in (hotkey.restore, integration.restore_session):
            try:
                restore()
            except (OSError, ValueError, RuntimeError) as error:
                print('Blind Pew:', error, file=sys.stderr)
        Gtk.Application.do_shutdown(self)


def run():
    if not Gtk.init_check()[0]:
        raise RuntimeError(tr('Open Blind Pew in your desktop session.'))
    app = Application()
    for sig in (signal.SIGINT, signal.SIGTERM):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, lambda: (app.quit(), False)[1])
    return app.run(['blind-pew'])
