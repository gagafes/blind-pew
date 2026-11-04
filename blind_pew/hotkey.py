"""One desktop shortcut: F12 invokes the running application's toggle action."""
import subprocess
from . import config, integration
from .i18n import tr

COMMAND = '/usr/bin/blind-pew toggle'
GNOME_SCHEMA = 'org.gnome.settings-daemon.plugins.media-keys'
GNOME_PREFIX = '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/'
GNOME_PATH = GNOME_PREFIX + 'blind-pew/'
XFCE_KEY = '/commands/custom/F12'
XFCE_WM_KEY = '/xfwm4/custom/F12'


def valid_backup(data):
    if not isinstance(data, dict):
        return {}
    result = {}
    gnome = data.get('gnome', {})
    if isinstance(gnome, dict):
        entry, displaced = gnome.get('entry'), gnome.get('displaced')
        if (isinstance(entry, dict) and set(entry) == {'name', 'command', 'binding'} and
                all(isinstance(v, str) and len(v) <= 2048 for v in entry.values()) and
                isinstance(gnome.get('listed'), bool) and isinstance(displaced, list) and
                len(displaced) <= 32 and all(isinstance(p, str) and
                    p.startswith(GNOME_PREFIX) and p.endswith('/') and '//' not in p and
                    len(p) <= 256 for p in displaced)):
            result['gnome'] = gnome
    xfce = data.get('xfce', {})
    if (isinstance(xfce, dict) and set(xfce) == {'command', 'wm'} and
            all(v is None or isinstance(v, str) and len(v) <= 2048 for v in xfce.values())):
        result['xfce'] = xfce
    return result


def _custom(path):
    from gi.repository import Gio
    integration._settings(GNOME_SCHEMA)  # check schema availability before constructing
    return Gio.Settings.new_with_path(GNOME_SCHEMA + '.custom-keybinding', path)


def _xfquery(*args):
    try:
        result = subprocess.run(['xfconf-query', '-c', 'xfce4-keyboard-shortcuts', *args],
                                capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(tr('Settings unavailable') + ': ' + str(error)) from error
    if result.returncode:
        raise RuntimeError(tr('Settings unavailable') + ': ' + result.stderr.strip()[:240])
    return result.stdout.rstrip('\n')


def _xfget(key):
    return _xfquery('-p', key) if key in _xfquery('-l').splitlines() else None


def _xfset(key, value):
    if value is None:
        if _xfget(key) is not None:
            _xfquery('-p', key, '-r')
    else:
        _xfquery('-p', key, '-n', '-t', 'string', '-s', value)


def install():
    backups = config.load()['hotkey_backup']
    if integration.is_gnome():
        root, own = integration._settings(GNOME_SCHEMA), _custom(GNOME_PATH)
        paths = root.get_strv('custom-keybindings')
        saved = backups.setdefault('gnome', dict(
            entry={key: own.get_string(key) for key in ('name', 'command', 'binding')},
            listed=GNOME_PATH in paths, displaced=[]))
        changes = [(own, key, value) for key, value in
                   (('name', 'Blind Pew'), ('command', COMMAND), ('binding', 'F12'))]
        for path in paths:
            if path != GNOME_PATH and _custom(path).get_string('binding') == 'F12':
                if path not in saved['displaced']:
                    saved['displaced'].append(path)
                changes.append((_custom(path), 'binding', ''))
        if GNOME_PATH not in paths:
            changes.append((root, 'custom-keybindings', paths + [GNOME_PATH]))
        if valid_backup(backups) != backups:
            raise RuntimeError(tr('Settings unavailable'))
        integration._write_session(changes, lambda: config.update(hotkey_backup=backups))
    else:
        original = {'command': _xfget(XFCE_KEY), 'wm': _xfget(XFCE_WM_KEY)}
        backups.setdefault('xfce', original)
        if valid_backup(backups) != backups:
            raise RuntimeError(tr('Settings unavailable'))
        # Save first: an interrupted desktop command must not lose its original.
        config.update(hotkey_backup=backups)
        try:
            if original['wm']:
                _xfset(XFCE_WM_KEY, '')
            _xfset(XFCE_KEY, COMMAND)
        except RuntimeError:
            _xfset(XFCE_KEY, original['command'])
            _xfset(XFCE_WM_KEY, original['wm'])
            raise


def restore():
    backups = config.load()['hotkey_backup']
    name = 'gnome' if integration.is_gnome() else 'xfce'
    saved = backups.get(name)
    if saved is None:
        return
    if name == 'gnome':
        root, own = integration._settings(GNOME_SCHEMA), _custom(GNOME_PATH)
        changes = []
        if own.get_string('command') == COMMAND and own.get_string('binding') == 'F12':
            changes.extend((own, key, value) for key, value in saved['entry'].items())
            if not saved['listed']:
                changes.append((root, 'custom-keybindings',
                                [p for p in root.get_strv('custom-keybindings') if p != GNOME_PATH]))
        for path in saved['displaced']:
            settings = _custom(path)
            if settings.get_string('binding') == '':
                changes.append((settings, 'binding', 'F12'))
        backups.pop(name)
        integration._write_session(changes, lambda: config.update(hotkey_backup=backups))
    else:
        if _xfget(XFCE_KEY) == COMMAND:
            _xfset(XFCE_KEY, saved['command'])
        if _xfget(XFCE_WM_KEY) == '' and saved['wm'] is not None:
            _xfset(XFCE_WM_KEY, saved['wm'])
        backups.pop(name)
        config.update(hotkey_backup=backups)


def invoke():
    """Send only an action; do not open or focus the preferences window."""
    from gi.repository import Gio, GLib
    try:
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        connection.call_sync('org.blindpew.App', '/org/blindpew/App', 'org.gtk.Actions',
                             'Activate', GLib.Variant('(sava{sv})', ('toggle', [], {})),
                             None, Gio.DBusCallFlags.NO_AUTO_START, 2000, None)
    except GLib.Error as error:
        raise RuntimeError(tr('Open Blind Pew in your desktop session.')) from error
