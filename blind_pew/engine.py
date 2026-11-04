"""IBus adapter. It never hooks devices, polls keys, or reads surrounding text."""
import itertools
import signal
import gi
gi.require_version('IBus', '1.0')
from gi.repository import GLib, IBus
from . import config, i18n
from .i18n import tr
from .core import Composer, engines

BUS_NAME = 'org.freedesktop.IBus.BlindPew'
ENGINE_IDS = {name: (profile, base) for name, profile, base in engines()}


class Engine(IBus.Engine):
    __gtype_name__ = 'BlindPewEngine'

    def __init__(self, connection, object_path, engine_name):
        super().__init__(connection=connection, object_path=object_path,
                         engine_name=engine_name)
        profile, _base = ENGINE_IDS[engine_name]
        self.profile = profile
        self.composer = Composer(profile['id'])
        self.sensitive = False
        self._prop = None

    def _commit(self, text):
        if text:
            self.commit_text(IBus.Text.new_from_string(text))

    def _preedit(self, value=None):
        if value is None:
            value = self.composer.pending
        text = IBus.Text.new_from_string(value)
        if value:
            text.append_attribute(IBus.AttrType.UNDERLINE, IBus.AttrUnderline.SINGLE,
                                  0, len(value))
        self.update_preedit_text_with_mode(text, len(value), bool(value),
                                           IBus.PreeditFocusMode.COMMIT)

    def _flush(self):
        value = self.composer.flush()
        self._preedit()
        self._commit(value)

    def do_focus_in(self):
        i18n.configure(config.load()['ui_language'])
        self._prop = IBus.Property.new(
            'InputMode', IBus.PropType.NORMAL,
            IBus.Text.new_from_string(tr('Transliteration')), '',
            IBus.Text.new_from_string('F12 — ' + tr('Toggle transliteration')),
            False, True, IBus.PropState.UNCHECKED, None)
        self._prop.set_symbol(IBus.Text.new_from_string(self.profile['symbol']))
        properties = IBus.PropList.new()
        properties.append(self._prop)
        self.register_properties(properties)

    def do_focus_out(self):
        # IBus commits the published preedit to its OLD input context before
        # FocusOut. A second commit here would duplicate it or leak to a new app.
        self.composer.clear()

    def do_reset(self):
        self.composer.clear()
        self._preedit()

    def do_enable(self):
        self.do_focus_in()

    def do_disable(self):
        self.composer.clear()

    def do_set_content_type(self, purpose, hints):
        private_hint = getattr(IBus.InputHints, 'PRIVATE', 0)
        sensitive = purpose in (IBus.InputPurpose.PASSWORD, IBus.InputPurpose.PIN)
        sensitive = sensitive or bool(hints & private_hint)
        if sensitive:
            self.composer.clear()
            self._preedit()
        self.sensitive = sensitive

    def do_process_key_event(self, keyval, keycode, state):
        if state & IBus.ModifierType.RELEASE_MASK:
            return False
        if self.sensitive:
            return False
        shortcuts = (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK |
                     IBus.ModifierType.SUPER_MASK | IBus.ModifierType.META_MASK |
                     IBus.ModifierType.HYPER_MASK)
        if state & shortcuts:
            self._flush()
            return False
        if keyval == IBus.KEY_BackSpace:
            if self.composer.backspace():
                self._preedit()
                return True
            return False
        if keyval in (IBus.KEY_Shift_L, IBus.KEY_Shift_R, IBus.KEY_Control_L,
                      IBus.KEY_Control_R, IBus.KEY_Alt_L, IBus.KEY_Alt_R,
                      IBus.KEY_Super_L, IBus.KEY_Super_R, IBus.KEY_Caps_Lock,
                      IBus.KEY_ISO_Level3_Shift, IBus.KEY_Num_Lock):
            return False
        char = IBus.keyval_to_unicode(keyval)
        if isinstance(char, int):
            char = chr(char) if char else ''
        if not char or not char.isprintable() or char.isspace():
            self._flush()
            return False
        committed = self.composer.feed(char)
        if committed:
            # Reset the client's preedit cursor before inserting a finalized
            # prefix, then publish the new pending suffix after the commit.
            self._preedit('')
            self._commit(committed)
        self._preedit()
        return True


class Factory(IBus.Factory):
    __gtype_name__ = 'BlindPewFactory'

    def __init__(self, bus):
        super().__init__(connection=bus.get_connection(), object_path=IBus.PATH_FACTORY)
        self.bus = bus
        self.serial = itertools.count(1)
        self.instances = set()

    def do_create_engine(self, engine_name):
        if engine_name not in ENGINE_IDS:
            raise ValueError('Unknown input method')
        engine = Engine(self.bus.get_connection(),
                        '/org/freedesktop/IBus/BlindPew/Engine' + str(next(self.serial)),
                        engine_name)
        self.instances.add(engine)
        engine.connect('destroy', lambda obj: self.instances.discard(obj))
        return engine


def run():
    IBus.init()
    bus = IBus.Bus.new()
    if not bus.is_connected():
        raise RuntimeError('IBus is not running. Log in again after enabling IBus.')
    loop = GLib.MainLoop()
    bus.connect('disconnected', lambda _: loop.quit())
    factory = Factory(bus)
    bus.request_name(BUS_NAME, 0)
    for sig in (signal.SIGTERM, signal.SIGINT):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, lambda: (loop.quit(), False)[1])
    try:
        loop.run()
    finally:
        factory.destroy()
