"""Small, validated per-user preferences, written atomically."""
import json
import os
import stat
from pathlib import Path
import tempfile
from .i18n import SUPPORTED

DEFAULTS = {'favorite_profile': 'ru', 'favorite_base': 'us',
            'ui_language': 'system', 'session_backup': {}, 'hotkey_backup': {}}
MAX_BYTES = 16384


def path():
    root = os.environ.get('XDG_CONFIG_HOME', '')
    base = Path(root) if root and Path(root).is_absolute() else Path.home() / '.config'
    return base / 'blind-pew' / 'settings.json'


def load():
    result = {**DEFAULTS, 'session_backup': {}, 'hotkey_backup': {}}
    try:
        # Bound the actual read, not an earlier stat: files can grow between
        # the two. Refuse links/devices/FIFOs so a damaged preference cannot
        # block startup or make us read an unrelated file.
        fd = os.open(path(), os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                return result
            contents = handle.read(MAX_BYTES + 1)
        if len(contents) > MAX_BYTES:
            return result
        data = json.loads(contents.decode('utf-8'))
        if not isinstance(data, dict):
            return result
        language = data.get('ui_language')
        if isinstance(language, str) and language in SUPPORTED | {'system'}:
            result['ui_language'] = language
        from .core import profiles
        profile = data.get('favorite_profile')
        if isinstance(profile, str) and profile in profiles():
            result['favorite_profile'] = profile
        if data.get('favorite_base') in ('us', 'de'):
            result['favorite_base'] = data['favorite_base']
        from .hotkey import valid_backup, valid_text
        backup = data.get('session_backup', {})
        if isinstance(backup, dict):
            for desktop, values in backup.items():
                if desktop not in ('gnome', 'ibus') or not isinstance(values, dict):
                    continue
                keys, global_mode = values.get('shortcut'), values.get('global')
                if (isinstance(keys, list) and len(keys) <= 32 and
                        all(valid_text(v, 199) for v in keys) and
                        isinstance(global_mode, bool)):
                    result['session_backup'][desktop] = {'shortcut': keys, 'global': global_mode}
                    if desktop == 'ibus' and isinstance(values.get('layout'), bool):
                        result['session_backup'][desktop]['layout'] = values['layout']
        result['hotkey_backup'] = valid_backup(data.get('hotkey_backup'))
        return result
    except (OSError, ValueError, RecursionError):
        return result


def update(**values):
    data = load()
    data.update({key: value for key, value in values.items() if key in DEFAULTS})
    contents = json.dumps(data) + '\n'
    if len(contents.encode('utf-8')) > MAX_BYTES:
        raise ValueError('Settings exceed 16 KiB')
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix='.settings-', dir=target.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
        directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
