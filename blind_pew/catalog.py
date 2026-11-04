# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Transliteration profiles, stable IBus IDs and country indicators."""
from .core import profiles
from . import i18n

COUNTRIES = {'be': 'BY', 'uk': 'UA', 'lt': 'LT', 'ka': 'GE', 'hy': 'AM', 'ru': 'RU', 'he': 'IL'}
LANGUAGE_NAMES = dict(be='Belarusian', uk='Ukrainian', lt='Lithuanian',
                      ka='Georgian', hy='Armenian', ru='Russian', he='Hebrew')
PROFILE_ORDER = ('be', 'ua', 'li', 'ge', 'am', 'ru', 'rude', 'il')


def profile_title(ident, language=None):
    translate = i18n.translator(language or i18n.current()).gettext
    name = translate(LANGUAGE_NAMES[profiles()[ident]['language']])
    return name + ' — ' + translate('Transliteration') + (' (DE)' if ident == 'rude' else '')


def source_for(ident, base='us'):
    if ident not in profiles() or base not in ('us', 'de'):
        raise ValueError(i18n.tr('Unknown input source'))
    return 'ibus', f'blind-pew:{ident}:{base}'


def country_for(source_type, source_id):
    if source_type == 'ibus' and source_id.startswith('blind-pew:'):
        parts = source_id.split(':')
        if len(parts) != 3 or parts[1] not in profiles():
            return None
        return COUNTRIES[profiles()[parts[1]]['language']]
    if source_type == 'ibus' and source_id.startswith('xkb:'):
        source_id = source_id.split(':')[1]
        source_type = 'xkb'
    if source_type == 'xkb':
        code = source_id.split('+')[0]
        if code.isascii() and code.isalpha() and 2 <= len(code) <= 4:
            return code.upper()
    return None
