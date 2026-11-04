# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Validate independent JSON catalogs and emit portable GNU .mo files."""
import json
from pathlib import Path
import string
import struct
from blind_pew import i18n
from blind_pew.core import engines

ROOT = Path(__file__).resolve().parent.parent


def messages(language):
    data = json.loads((ROOT / 'po' / (language + '.json')).read_text(encoding='utf-8'))
    english = json.loads((ROOT / 'po/en.json').read_text(encoding='utf-8'))
    if data.keys() != english.keys():
        raise ValueError('Incomplete catalog: ' + language)
    def fields(text):
        return {key for _, key, _, _ in string.Formatter().parse(text) if key is not None}
    for key, value in data.items():
        if not isinstance(value, str) or not value.strip() or fields(key) != fields(value):
            raise ValueError('Invalid translation: ' + language + ': ' + key)
    for _, profile, base in engines():
        data[i18n.engine_title(profile['id'], base, 'en')] = i18n.engine_title(profile['id'], base, language)
    data[''] = 'Content-Type: text/plain; charset=UTF-8\nLanguage: ' + language + '\nMIME-Version: 1.0\n'
    return data


def compile_mo(data):
    pairs = sorted((key.encode('utf-8'), value.encode('utf-8')) for key, value in data.items())
    count = len(pairs)
    originals = b'\0'.join(key for key, _ in pairs) + b'\0'
    translated = b'\0'.join(value for _, value in pairs) + b'\0'
    key_offset = 28 + count * 16
    value_offset = key_offset + len(originals)
    keys, values = [], []
    for key, value in pairs:
        keys.extend((len(key), key_offset))
        values.extend((len(value), value_offset))
        key_offset += len(key) + 1
        value_offset += len(value) + 1
    return (struct.pack('<7I', 0x950412de, 0, count, 28, 28 + count * 8, 0, 0) +
            struct.pack('<' + 'I' * len(keys), *keys) + struct.pack('<' + 'I' * len(values), *values) +
            originals + translated)


def install(dest):
    for language, _ in i18n.LANGUAGES:
        target = dest / 'usr/share/locale' / language / 'LC_MESSAGES/blind-pew.mo'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(compile_mo(messages(language)))
