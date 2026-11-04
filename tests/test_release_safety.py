# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Regressions for damaged preferences, bounded input and package contents."""
import io
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from blind_pew import cli, config, hotkey
from blind_pew.core import convert, convert_chunks, profiles


class Preferences(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        env = patch.dict(os.environ, XDG_CONFIG_HOME=str(self.root))
        env.start()
        self.addCleanup(env.stop)
        config.path().parent.mkdir(mode=0o700)

    def test_deeply_nested_json_and_invalid_utf8(self):
        for data in (b'[' * 2000 + b'0' + b']' * 2000, b'\xff\xfe'):
            config.path().write_bytes(data)
            self.assertEqual(config.load(), config.DEFAULTS)

    def test_fifo_is_not_opened_as_a_blocking_stream(self):
        os.mkfifo(config.path())
        self.assertEqual(config.load(), config.DEFAULTS)

    def test_symlink_is_not_read_and_save_does_not_overwrite_target(self):
        other = self.root / 'unrelated.json'
        other.write_text('{"favorite_profile":"il"}')
        config.path().symlink_to(other)
        self.assertEqual(config.load(), config.DEFAULTS)
        config.update(favorite_profile='ua')
        self.assertEqual(other.read_text(), '{"favorite_profile":"il"}')
        self.assertFalse(config.path().is_symlink())
        self.assertEqual(config.load()['favorite_profile'], 'ua')
        self.assertEqual(config.path().stat().st_mode & 0o777, 0o600)

    def test_failed_atomic_replace_preserves_preferences_and_cleans_temp(self):
        config.update(favorite_profile='ua')
        original = config.path().read_bytes()
        with patch.object(os, 'replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                config.update(favorite_profile='be')
        self.assertEqual(config.path().read_bytes(), original)
        self.assertEqual(list(config.path().parent.glob('.settings-*')), [])

    def test_invalid_shortcut_paths_and_strings_are_ignored(self):
        for suffix in ('../', 'bad\x00/', 'bad\n/', 'double//', ''):
            backup = {'gnome': {'entry': {'name': '', 'command': '', 'binding': ''},
                               'listed': False, 'displaced': [hotkey.GNOME_PREFIX + suffix]}}
            self.assertEqual(hotkey.valid_backup(backup), {})
        for value in ('bad\x00command', '\ud800'):
            data = {'hotkey_backup': {'xfce': {'command': value, 'wm': None}},
                    'session_backup': {'gnome': {'shortcut': [value], 'global': False}}}
            config.path().write_text(json.dumps(data))
            self.assertEqual(config.load()['hotkey_backup'], {})
            self.assertEqual(config.load()['session_backup'], {})


class FreshXfce(unittest.TestCase):
    def test_empty_channel_list_exit_status(self):
        result = subprocess.CompletedProcess([], 1, 'Channels:\n', '')
        with patch.object(subprocess, 'run', return_value=result) as run:
            self.assertIsNone(hotkey._xfget(hotkey.XFCE_KEY))
        self.assertEqual(run.call_args.kwargs['env']['LC_ALL'], 'C')

    def test_channel_list_errors_remain_errors(self):
        for output, error in (('', ''), ('Channels:\n', 'Connection lost')):
            result = subprocess.CompletedProcess([], 1, output, error)
            with patch.object(subprocess, 'run', return_value=result):
                with self.assertRaises(RuntimeError):
                    hotkey._xfget(hotkey.XFCE_KEY)

    def test_saved_shortcut_preserves_trailing_newline(self):
        result = subprocess.CompletedProcess([], 0, 'command\n\n', '')
        with patch.object(subprocess, 'run', return_value=result):
            self.assertEqual(hotkey._xfquery('-p', hotkey.XFCE_KEY), 'command\n')

    def test_absent_channel_has_no_saved_binding(self):
        with patch.object(hotkey, '_xfquery', return_value='Channels:') as query:
            self.assertIsNone(hotkey._xfget(hotkey.XFCE_KEY))
        query.assert_called_once_with('-l', channel=False)

    def test_connection_failure_is_not_treated_as_missing_binding(self):
        with patch.object(hotkey, '_xfquery', side_effect=RuntimeError('No session bus')):
            with self.assertRaises(RuntimeError):
                hotkey._xfget(hotkey.XFCE_KEY)


class Streaming(unittest.TestCase):
    def test_every_chunk_boundary_preserves_composition(self):
        for profile, data in profiles().items():
            sample = data['sample'] + " shh tsch i' \n s+h 🇺🇦 "
            for reverse in (False, True):
                expected = convert(sample, profile, reverse)
                for boundary in range(len(sample) + 1):
                    self.assertEqual(''.join(convert_chunks(
                        (sample[:boundary], sample[boundary:]), profile, reverse)), expected)

    def test_cli_reads_bounded_chunks_without_newlines(self):
        class BoundedReader(io.StringIO):
            def read(self, size=-1):
                if not 0 < size <= 8192:
                    raise AssertionError('Unbounded input read')
                return super().read(size)
        text = 's' * 8191 + 'h' + 'a' * 90000
        output = io.StringIO()
        with patch('sys.argv', ['blind-pew', 'convert']), patch('sys.stdin', BoundedReader(text)), \
                patch('sys.stdout', output), patch.object(config, 'load', return_value=config.DEFAULTS):
            self.assertEqual(cli.main(), 0)
        self.assertEqual(output.getvalue(), convert(text))


class Packaging(unittest.TestCase):
    def test_installed_readme_images_and_release_metadata(self):
        from tools.build import stage, VERSION, __version__
        import re
        self.assertTrue(VERSION.startswith(__version__ + '-'))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'package'
            stage(target)
            docs = target / 'usr/share/doc/blind-pew'
            for readme in docs.glob('README*.md'):
                text = readme.read_text()
                images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text)
                images += re.findall(r'<img[^>]+src="([^"]+)"', text)
                self.assertTrue(images)
                for image in images:
                    self.assertTrue((docs / image).is_file(), (readme, image))
            self.assertTrue((docs / 'SECURITY.md').is_file())
            self.assertTrue((docs / 'docs/RELEASE.md').is_file())
            compressed = (docs / 'changelog.gz').read_bytes()
            self.assertEqual(compressed[9], 255, 'Portable gzip OS header')
