# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Offline interface translation; system selection follows Malferma Libro.

English message IDs are a safe fallback. Language changes never alter the
process environment, the entered text, or an input source's persistent ID.
"""
import gettext
import json
import os
from functools import lru_cache
from pathlib import Path

DOMAIN = 'blind-pew'
ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = (
    ('be', 'Беларуская'),
    ('uk', 'Українська'),
    ('en', 'English'),
    ('eo', 'Esperanto'),
    ('ar', 'العربية'),
    ('he', 'עברית'),
    ('de', 'Deutsch'),
    ('kk', 'Қазақша'),
    ('fa', 'فارسی'),
    ('lt', 'Lietuvių'),
    ('lv', 'Latviešu'),
    ('et', 'Eesti'),
    ('es', 'Español'),
    ('fr', 'Français'),
    ('it', 'Italiano'),
    ('pt', 'Português'),
    ('ro', 'Română'),
    ('ca', 'Català'),
    ('nl', 'Nederlands'),
    ('sv', 'Svenska'),
    ('da', 'Dansk'),
    ('nb', 'Norsk bokmål'),
    ('nn', 'Norsk nynorsk'),
    ('is', 'Íslenska'),
    ('tr', 'Türkçe'),
    ('az', 'Azərbaycanca'),
    ('uz', 'Oʻzbekcha'),
    ('ky', 'Кыргызча'),
    ('tt', 'Татарча'),
    ('tk', 'Türkmençe'),
    ('am', 'አማርኛ'),
    ('mt', 'Malti'),
    ('yi', 'ייִדיש'),
    ('pl', 'Polski'),
    ('cs', 'Čeština'),
    ('sk', 'Slovenčina'),
    ('sl', 'Slovenščina'),
    ('hr', 'Hrvatski'),
    ('bs', 'Bosanski'),
    ('sr', 'Српски'),
    ('sr_Latn', 'Srpski (latinica)'),
    ('mk', 'Македонски'),
    ('bg', 'Български'),
    ('eu', 'Euskara'),
    ('sq', 'Shqip'),
    ('hsb', 'Hornjoserbšćina'),
    ('dsb', 'Dolnoserbšćina'),
    ('ru', 'Русский'),
    ('rue', 'Русиньскый'),
)
SUPPORTED = frozenset(code for code, name in LANGUAGES)
RTL = frozenset(('ar','he','fa','yi'))
_language = 'en'
_translator = gettext.NullTranslations()


def normalize(value):
    tag, _, modifier = value.strip().lower().replace('-', '_').partition('@')
    parts = tag.split('.', 1)[0].split('_')
    base = {'iw':'he', 'ji':'yi', 'no':'nb', 'mo':'ro'}.get(parts[0], parts[0])
    if base in ('c', 'posix'):
        return 'en'
    if base == 'sr' and (parts[1:2] == ['latn'] or modifier in ('latin','latn')):
        return 'sr_Latn'
    return base if base in SUPPORTED else None


def resolve(choice='system', environ=None):
    if choice != 'system':
        return normalize(choice) or 'en'
    env = os.environ if environ is None else environ
    for value in env.get('LANGUAGE', '').split(':'):
        if code := normalize(value):
            return code
    for key in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        if value := env.get(key, '').strip():
            return normalize(value) or 'en'
    return 'en'


@lru_cache(maxsize=64)
def translator(language):
    # Source checkout: editable catalogs. Installed app: standard GNU gettext.
    source = ROOT / 'po' / (language + '.json')
    if source.is_file():
        messages = json.loads(source.read_text(encoding='utf-8'))
        class SourceCatalog(gettext.NullTranslations):
            def gettext(self, message):
                return messages.get(message, message)
        return SourceCatalog()
    return gettext.translation(DOMAIN, localedir='/usr/share/locale', languages=[language], fallback=True)


def configure(choice='system', environ=None):
    global _language, _translator
    selected = resolve(choice, environ)
    _translator = translator(selected)
    _language = selected
    return selected


def current():
    return _language


def tr(message, **values):
    text = _translator.gettext(message)
    return text.format(**values) if values else text


def engine_title(profile_id, base, language=None):
    from .catalog import profile_title
    label = profile_title(profile_id, language=language)
    return 'Blind Pew — ' + label + ' (' + ('QWERTZ' if base == 'de' else 'QWERTY') + ')'
