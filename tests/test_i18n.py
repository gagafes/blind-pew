# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
import gettext
import io
import os
import unittest
from blind_pew import i18n
from blind_pew.catalog import profile_title
from blind_pew.core import convert, engines
from tools.translations import compile_mo, messages


class Languages(unittest.TestCase):
    def tearDown(self):
        i18n.configure('en')

    def test_system_locale_priority(self):
        cases = [({'LANGUAGE':'xx:uk_UA:de','LC_ALL':'ru_RU'},'uk'),
                 ({'LANGUAGE':'xx','LC_ALL':'xx','LANG':'de_DE'},'en'),
                 ({'LC_MESSAGES':'de_DE.UTF-8','LANG':'ru_RU'},'de'),
                 ({'LANG':'uk_UA.UTF-8'},'uk'), ({'LC_ALL':'C.UTF-8','LANG':'ru_RU'},'en'),
                 ({'LANG':'POSIX'},'en'), ({},'en')]
        for env, expected in cases:
            with self.subTest(env=env): self.assertEqual(i18n.resolve(environ=env), expected)

    def test_aliases_and_serbian_scripts(self):
        for value, expected in [('iw_IL','he'),('ji','yi'),('no_NO','nb'),('mo','ro'),
                ('sr-Latn-RS','sr_Latn'),('sr_RS.UTF-8@latin','sr_Latn'),
                ('sr-Cyrl-RS-u-nu-latn','sr'),('xx','en')]:
            self.assertEqual(i18n.resolve(value),expected)

    def test_live_translation_preserves_environment_and_text(self):
        before = dict(os.environ)
        text = convert("Pryvit! Ukrai'na je g'", 'ua')
        for language, word in [('de','Ukrainisch'),('uk','Українська'),('en','Ukrainian')]:
            i18n.configure(language)
            self.assertTrue(profile_title('ua').startswith(word), profile_title('ua'))
            self.assertEqual(convert("Pryvit! Ukrai'na je g'", 'ua'),text)
        self.assertEqual(dict(os.environ),before)

    def test_all_49_catalogs_compile_and_translate_engine_names(self):
        self.assertEqual(len(i18n.LANGUAGES),49)
        for language, _ in i18n.LANGUAGES:
            catalog=messages(language)
            mo=gettext.GNUTranslations(io.BytesIO(compile_mo(catalog)))
            for key,value in catalog.items():
                if key: self.assertEqual(mo.gettext(key),value)
            for _,profile,base in engines():
                self.assertEqual(mo.gettext(i18n.engine_title(profile['id'],base,'en')),
                                 i18n.engine_title(profile['id'],base,language))
            self.assertEqual(mo.gettext('Unknown future message'),'Unknown future message')
