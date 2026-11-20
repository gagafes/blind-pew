# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
import unittest
from blind_pew.catalog import profiles, source_for, country_for, profile_title, PROFILE_ORDER


class Catalogue(unittest.TestCase):
    def test_only_transliteration_is_registered(self):
        self.assertEqual(set(profiles()), set(PROFILE_ORDER))
        self.assertEqual(len({p['language'] for p in profiles().values()}), 8)
        for unknown in ('unknown', 'invalid:source', ''):
            with self.assertRaises(ValueError):
                source_for(unknown)

    def test_arabic_profile_labels(self):
        self.assertEqual(profile_title('ar', 'en'), 'Arabic — Transliteration')
        self.assertEqual(profile_title('ar', 'ru'), 'Арабский — Транслит')
        for base in ('us', 'de'):
            self.assertEqual(country_for(*source_for('ar', base)), 'ARA')

    def test_country_tracks_global_source(self):
        for ident, expected in [('ru','RU'),('ua','UA'),('be','BY'),('li','LT'),('ge','GE'),('am','AM'),('il','IL')]:
            for base in ('us', 'de'):
                self.assertEqual(country_for(*source_for(ident,base)), expected)
        self.assertEqual(country_for('xkb','be'), 'BE')
        self.assertEqual(country_for('ibus','xkb:de::ger'), 'DE')
        self.assertIsNone(country_for('ibus','unknown'))

