# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
import os
import tempfile
import unittest
from unittest.mock import patch
from blind_pew import config


class Settings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, {'XDG_CONFIG_HOME': self.tmp.name})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_defaults_are_small_and_global(self):
        self.assertEqual(config.load(), {'favorite_profile':'ru','favorite_base':'us',
            'ui_language':'system','session_backup':{},'hotkey_backup':{}})

    def test_language_change_preserves_session_backup(self):
        backup={'gnome': {'shortcut':['<Alt>space'], 'global':True},
                'ibus': {'shortcut':['<Super>space'], 'global':False, 'layout':True}}
        config.update(session_backup=backup)
        config.update(ui_language='uk')
        self.assertEqual(config.load()['session_backup'],backup)
        self.assertEqual(config.load()['ui_language'],'uk')

    def test_corrupt_and_oversized_settings_have_safe_defaults(self):
        config.path().parent.mkdir(parents=True)
        for text in ('not json','null','[]','{"favorite_profile":9}', ' '*17000):
            config.path().write_text(text)
            self.assertEqual(config.load()['favorite_profile'],'ru')

    def test_valid_preferences_and_unknown_values(self):
        config.update(ui_language='uk',favorite_base='de',favorite_profile='rude')
        self.assertEqual(config.load()['favorite_profile'],'rude')
        config.update(ui_language=['invalid'],favorite_profile='unknown')
        self.assertEqual(config.load()['ui_language'],'system')
        self.assertEqual(config.load()['favorite_profile'],'ru')
        self.assertEqual(config.load()['favorite_base'],'de')

    def test_oversized_backup_cannot_overwrite_working_preferences(self):
        config.update(favorite_profile='ua')
        original = config.path().read_bytes()
        with self.assertRaises(ValueError):
            config.update(session_backup={'gnome': {'shortcut': ['я' * 180] * 32, 'global': True}})
        self.assertEqual(config.path().read_bytes(), original)
