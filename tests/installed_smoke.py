#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
# The import order is intentional: GI versions, runtime checks or sys.path
# bootstrap must precede importing their dependent modules.
# ruff: noqa: E402
"""Inspect the installed payload, not the source checkout."""
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import blind_pew
from blind_pew import i18n
from blind_pew.core import engines

assert Path(blind_pew.__file__).resolve().is_relative_to('/usr/share/blind-pew')
assert subprocess.check_output(['blind-pew', '--version'], text=True).strip() == blind_pew.__version__
registered = subprocess.check_output(['blind-pew', 'list'], text=True).splitlines()
assert len(registered) == 16, registered
result = subprocess.run(['blind-pew', 'convert', '--profile', 'ua'],
                        input="Ukrai'na je g'\n", capture_output=True, text=True, check=True)
assert result.stdout == 'Україна є ґ\n', result
component = ET.parse('/usr/share/ibus/component/blind-pew.xml').getroot()
assert {node.findtext('name') for node in component.find('engines')} == {name for name, _, _ in engines()}
for language, _ in i18n.LANGUAGES:
    translator = i18n.translator(language)
    assert translator.gettext('Transliteration')
    assert Path('/usr/share/locale', language, 'LC_MESSAGES/blind-pew.mo').is_file(), language
metadata = json.loads(Path('/usr/share/gnome-shell/extensions/blind-pew@local/metadata.json').read_text())
assert metadata['shell-version'] == ['46', '47', '48']
for path in ('LICENSE', 'copyright', 'docs/screenshots/gnome-settings-en.png',
             'THIRD_PARTY_NOTICES.md', 'LICENSES/LGPL-3.0.txt'):
    assert Path('/usr/share/doc/blind-pew', path).is_file(), path
print('PASS installed CLI, 16 engines, 49 gettext catalogs, extension and documentation')

import os
env = {key: value for key, value in os.environ.items() if key not in ('DISPLAY', 'WAYLAND_DISPLAY')}
headless = subprocess.run(['blind-pew', 'setup'], env=env, capture_output=True, text=True, timeout=5)
assert headless.returncode == 1, headless
assert 'Traceback' not in headless.stderr, headless.stderr
print('PASS headless startup reports a controlled error')
