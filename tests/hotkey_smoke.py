# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Real Xfconf and Gio settings; run only in the isolated GUI test session."""
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
from gi.repository import Gio
from blind_pew import config, hotkey, integration

assert os.environ.get('GSETTINGS_BACKEND') == 'memory'
os.environ['XDG_CURRENT_DESKTOP'] = 'XFCE'
hotkey._xfset(hotkey.XFCE_KEY, 'original-command')
hotkey._xfset(hotkey.XFCE_WM_KEY, 'original-window-action')
hotkey.install(); hotkey.install()
assert hotkey._xfget(hotkey.XFCE_KEY) == hotkey.COMMAND
assert hotkey._xfget(hotkey.XFCE_WM_KEY) == ''
assert config.load()['hotkey_backup']['xfce'] == {
    'command': 'original-command', 'wm': 'original-window-action'}
hotkey.restore()
assert hotkey._xfget(hotkey.XFCE_KEY) == 'original-command'
assert hotkey._xfget(hotkey.XFCE_WM_KEY) == 'original-window-action'
hotkey._xfset(hotkey.XFCE_KEY, None)
hotkey._xfset(hotkey.XFCE_WM_KEY, None)
hotkey.install()
hotkey._xfset(hotkey.XFCE_KEY, 'user-changed-command')
hotkey.restore()
assert hotkey._xfget(hotkey.XFCE_KEY) == 'user-changed-command'
with patch.object(config, 'update', side_effect=OSError('Cannot save')):
    try:
        hotkey.install()
        raise AssertionError('Ignored save error')
    except OSError:
        pass
assert hotkey._xfget(hotkey.XFCE_KEY) == 'user-changed-command'
print('PASS real Xfconf: F12 only, idempotence, restore, external edits, safe save failure')

# Minimal definitions of the public GNOME schema keys, for CI without GNOME.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root/'hotkey.gschema.xml').write_text('''<schemalist>
    <schema id="org.gnome.settings-daemon.plugins.media-keys" path="/org/gnome/settings-daemon/plugins/media-keys/">
      <key name="custom-keybindings" type="as"><default>[]</default></key>
    </schema>
    <schema id="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding">
      <key name="name" type="s"><default>''</default></key>
      <key name="command" type="s"><default>''</default></key>
      <key name="binding" type="s"><default>''</default></key>
    </schema></schemalist>''')
    compiler = shutil.which('glib-compile-schemas') or str(next(Path('/usr/lib').glob('*/glib-2.0/glib-compile-schemas')))
    subprocess.run([compiler, str(root)], check=True)
    schemas = Gio.SettingsSchemaSource.new_from_directory(str(root), Gio.SettingsSchemaSource.get_default(), False)
    def settings(name):
        return Gio.Settings.new_full(schemas.lookup(name, True), None, None)
    def custom(path):
        return Gio.Settings.new_full(schemas.lookup(hotkey.GNOME_SCHEMA+'.custom-keybinding', True), None, path)
    os.environ['XDG_CURRENT_DESKTOP'] = 'GNOME'
    with patch.object(integration, '_settings', settings), patch.object(hotkey, '_custom', custom):
        parent = settings(hotkey.GNOME_SCHEMA)
        original_path = hotkey.GNOME_PREFIX + 'personal/'
        personal = custom(original_path)
        personal.set_string('binding', 'F12')
        personal.set_string('command', 'original-command')
        parent.set_strv('custom-keybindings', [original_path])
        hotkey.install(); hotkey.install()
        own = custom(hotkey.GNOME_PATH)
        assert own.get_string('binding') == 'F12'
        assert own.get_string('command') == hotkey.COMMAND
        assert personal.get_string('binding') == ''
        assert parent.get_strv('custom-keybindings') == [original_path, hotkey.GNOME_PATH]
        hotkey.restore()
        assert parent.get_strv('custom-keybindings') == [original_path]
        assert personal.get_string('binding') == 'F12'
        assert own.get_string('command') == ''
        with patch.object(config, 'update', side_effect=OSError('Cannot save')):
            try:
                hotkey.install()
                raise AssertionError('Ignored save error')
            except OSError:
                pass
        assert personal.get_string('binding') == 'F12'
        assert parent.get_strv('custom-keybindings') == [original_path]
        assert own.get_string('command') == ''
print('PASS GNOME settings fixture: F12 command, preserve other bindings, restore and rollback')
