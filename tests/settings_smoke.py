#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Run with GSETTINGS_BACKEND=memory; never modify a user's real settings."""
import os
import tempfile
assert os.environ.get('GSETTINGS_BACKEND') == 'memory'
from gi.repository import Gio, GLib
from blind_pew import integration
from blind_pew import config
from unittest.mock import patch

for desktop in ('GNOME', 'XFCE'):
    os.environ['XDG_CURRENT_DESKTOP'] = desktop
    if desktop == 'GNOME':
        schema, key, initial = 'org.gnome.desktop.input-sources', 'sources', [('xkb', 'de'), ('xkb', 'us')]
        s = Gio.Settings.new(schema)
        s.set_value(key, GLib.Variant('a(ss)', initial))
        expected = initial + [('ibus', 'blind-pew:ru:de')]
    else:
        schema, key, initial = 'org.freedesktop.ibus.general', 'preload-engines', ['xkb:de::ger', 'xkb:us::eng']
        s = Gio.Settings.new(schema)
        s.set_strv(key, initial)
        expected = initial + ['blind-pew:ru:de']
    integration.add_engine('blind-pew:ru:de')
    integration.add_engine('blind-pew:ru:de')
    assert s.get_value(key).unpack() == expected
    try:
        integration.add_engine('unknown')
        raise AssertionError('Unknown ID accepted')
    except ValueError:
        pass

    assert s.get_value(key).unpack() == expected
    integration.remove_our_engines()
    assert s.get_value(key).unpack() == initial
    only_translit = [('ibus', 'blind-pew:ru:de')] if desktop == 'GNOME' else ['blind-pew:ru:de']
    s.set_value(key, GLib.Variant('a(ss)' if desktop == 'GNOME' else 'as', only_translit))
    native = integration.normal_source('de')
    assert native == (('xkb', 'de') if desktop == 'GNOME' else ('ibus', 'xkb:de::ger'))
    assert s.get_value(key).unpack() == only_translit + ([native] if desktop == 'GNOME' else [native[1]])
    s.set_value(key, GLib.Variant('a(ss)' if desktop == 'GNOME' else 'as', initial))
    print('PASS', desktop, 'source settings: append, idempotence, reject unknown, remove preserving others')

with tempfile.TemporaryDirectory() as tmp:
    os.environ['XDG_CONFIG_HOME'] = tmp
    for desktop in ('GNOME','XFCE'):
        os.environ['XDG_CURRENT_DESKTOP'] = desktop
        name, targets = integration.session_settings()
        keys, key, _, _ = targets[0]
        original = ['<Alt>F6']
        originals = {}
        for settings, setting, desired, field in targets:
            value = original if field == 'shortcut' else not desired
            originals[field] = value
            settings.set_value(setting, GLib.Variant(settings.get_value(setting).get_type_string(), value))
        real_set = Gio.Settings.set_value
        def checked_set(settings, setting, value):
            assert config.load()['session_backup'][name] == originals, 'Backup saved too late'
            return real_set(settings, setting, value)
        with patch.object(Gio.Settings, 'set_value', checked_set):
            integration.configure_session()
        for settings, setting, desired, _ in targets:
            assert settings.get_value(setting).unpack() == desired
        integration.configure_session()
        config.update(ui_language='uk')
        assert config.load()['session_backup'][name] == originals
        with patch.object(config, 'update', side_effect=OSError('Cannot save preferences')):
            try:
                integration.restore_session()
                raise AssertionError('Restore save failure was ignored')
            except OSError:
                pass
        assert config.load()['session_backup'][name] == originals
        for settings, setting, desired, _ in targets:
            assert settings.get_value(setting).unpack() == desired
        with patch.object(Gio.Settings, 'is_writable', return_value=False):
            try:
                integration.restore_session()
                raise AssertionError('Locked setting was ignored')
            except RuntimeError:
                pass
        assert config.load()['session_backup'][name] == originals
        integration.restore_session()
        for settings, setting, _, field in targets:
            assert settings.get_value(setting).unpack() == originals[field]
        assert name not in config.load()['session_backup']
        integration.configure_session()
        keys.set_strv(key,['<Alt>F7'])
        integration.restore_session()
        assert keys.get_strv(key) == ['<Alt>F7']
        keys.set_strv(key,original)
        with patch.object(config,'update',side_effect=OSError('Cannot save preferences')):
            try:
                integration.configure_session()
                raise AssertionError('Save failure was ignored')
            except OSError:
                pass
        assert keys.get_strv(key) == original
        for settings, setting, _, field in targets:
            assert settings.get_value(setting).unpack() == originals[field]
        print('PASS', desktop, 'F12/global/keyboard-base: preserve originals, locked settings, rollback and restore')
