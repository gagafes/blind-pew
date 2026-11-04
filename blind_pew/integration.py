"""Per-user IBus setup. Standard system layouts remain owned by the desktop."""
import os
from .core import engines
from .i18n import tr


def is_gnome():
    return 'gnome' in os.environ.get('XDG_CURRENT_DESKTOP', '').lower()


def _settings(schema):
    from gi.repository import Gio
    source = Gio.SettingsSchemaSource.get_default()
    if not source or not source.lookup(schema, True):
        raise RuntimeError(tr('Settings unavailable') + ': ' + schema)
    return Gio.Settings.new(schema)


def add_engine(engine_id):
    from gi.repository import Gio, GLib
    known = {name: base for name, _, base in engines()}
    if engine_id not in known:
        raise ValueError(tr('Unknown input source'))
    latin = known[engine_id]
    if is_gnome():
        settings = _settings('org.gnome.desktop.input-sources')
        sources = settings.get_value('sources').unpack() or [('xkb', latin)]
        item = ('ibus', engine_id)
        if item not in sources and not settings.set_value('sources', GLib.Variant('a(ss)', sources + [item])):
            raise RuntimeError(tr('Settings unavailable'))
    else:
        settings = _settings('org.freedesktop.ibus.general')
        values = settings.get_strv('preload-engines') or [f"xkb:{latin}::{'ger' if latin == 'de' else 'eng'}"]
        if engine_id not in values and not settings.set_strv('preload-engines', values + [engine_id]):
            raise RuntimeError(tr('Settings unavailable'))
    Gio.Settings.sync()


def normal_source(base='us'):
    """Fallback only when the app has not yet observed an ordinary source."""
    from gi.repository import Gio, GLib
    if is_gnome():
        settings = _settings('org.gnome.desktop.input-sources')
        sources = settings.get_value('sources').unpack()
        for source in sources:
            if source[0] == 'xkb':
                return tuple(source)
        source = ('xkb', base)
        if not settings.set_value('sources', GLib.Variant('a(ss)', sources + [source])):
            raise RuntimeError(tr('Settings unavailable'))
        Gio.Settings.sync()
        return source
    settings = _settings('org.freedesktop.ibus.general')
    sources = settings.get_strv('preload-engines')
    for name in sources:
        if name.startswith('xkb:'):
            return 'ibus', name
    name = f"xkb:{base}::{'ger' if base == 'de' else 'eng'}"
    if not settings.set_strv('preload-engines', sources + [name]):
        raise RuntimeError(tr('Settings unavailable'))
    Gio.Settings.sync()
    return 'ibus', name


def remove_our_engines():
    from gi.repository import Gio, GLib
    if is_gnome():
        settings = _settings('org.gnome.desktop.input-sources')
        original = settings.get_value('sources').unpack()
        kept = [s for s in original if not (s[0] == 'ibus' and s[1].startswith('blind-pew:'))]
        if kept != original and not settings.set_value('sources', GLib.Variant('a(ss)', kept or [('xkb', 'us')])):
            raise RuntimeError(tr('Settings unavailable'))
    else:
        settings = _settings('org.freedesktop.ibus.general')
        original = settings.get_strv('preload-engines')
        kept = [s for s in original if not s.startswith('blind-pew:')]
        if kept != original and not settings.set_strv('preload-engines', kept or ['xkb:us::eng']):
            raise RuntimeError(tr('Settings unavailable'))
    Gio.Settings.sync()
    restore_session()


def session_settings():
    if is_gnome():
        return 'gnome', (
            (_settings('org.gnome.desktop.wm.keybindings'), 'switch-input-source', [], 'shortcut'),
            (_settings('org.gnome.desktop.input-sources'), 'per-window', False, 'global'))
    general = _settings('org.freedesktop.ibus.general')
    return 'ibus', (
        (_settings('org.freedesktop.ibus.general.hotkey'), 'triggers', [], 'shortcut'),
        (general, 'use-global-engine', True, 'global'),
        (general, 'use-system-keyboard-layout', False, 'layout'))


def _write_session(values, save):
    """Keep desktop settings and their saved originals consistent on failure."""
    from gi.repository import Gio, GLib
    changes = [(settings, key, settings.get_value(key), value)
               for settings, key, value in values
               if settings.get_value(key).unpack() != value]
    if any(not settings.is_writable(key) for settings, key, _, _ in changes):
        raise RuntimeError(tr('Settings unavailable'))
    try:
        for settings, key, original, value in changes:
            if not settings.set_value(key, GLib.Variant(original.get_type_string(), value)):
                raise RuntimeError(tr('Settings unavailable'))
        save()
    except (OSError, ValueError, RuntimeError):
        for settings, key, original, _ in changes:
            settings.set_value(key, original)
        raise
    finally:
        Gio.Settings.sync()


def configure_session():
    """Global input; F12 is reserved for our explicit on/off desktop action."""
    from . import config
    desktop, targets = session_settings()
    backups = config.load()['session_backup']
    saved = backups.setdefault(desktop, {})
    for settings, key, _, field in targets:
        saved.setdefault(field, settings.get_value(key).unpack())
    _write_session([(settings, key, value) for settings, key, value, _ in targets],
                   lambda: config.update(session_backup=backups))


def restore_session():
    from . import config
    desktop, targets = session_settings()
    backups = config.load()['session_backup']
    saved = backups.get(desktop)
    if not saved:
        return
    # Leave settings alone if the user has changed them independently.
    values = [(settings, key, saved[field]) for settings, key, desired, field in targets
              if field in saved and settings.get_value(key).unpack() == desired]
    backups.pop(desktop)
    _write_session(values, lambda: config.update(session_backup=backups))


def doctor():
    print('XDG_CURRENT_DESKTOP:', os.environ.get('XDG_CURRENT_DESKTOP', tr('Unknown')))
    print('XDG_SESSION_TYPE:', os.environ.get('XDG_SESSION_TYPE', tr('Unknown')))
    try:
        import gi
        gi.require_version('IBus', '1.0')
        from gi.repository import IBus
        IBus.init()
        bus = IBus.Bus.new()
        if not bus.is_connected():
            print(tr('IBus: not running'))
            return 1
        registered = {e.get_name() for e in bus.list_engines()}
        expected = {name for name, _, _ in engines()}
        print(tr('IBus: running'), '— Blind Pew:', len(expected & registered), '/', len(expected))
        for key in ('GTK_IM_MODULE', 'QT_IM_MODULE'):
            print(key + ':', os.environ.get(key, tr('System language')))
        return int(not expected <= registered)
    except (ImportError, ValueError) as error:
        print(tr('Error') + ':', error)
        return 1
