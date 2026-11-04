import random
import string
import unittest
from blind_pew.core import Composer, convert, engines, profiles


def whole_document_oracle(text, profile):
    """Reference editing model: replace a suffix in the WHOLE document.

    Deliberately independent of the production streaming/prefix optimization.
    """
    result = ''
    for char in text:
        before = result
        for tail, replacement in profile['rules'].get(char, []):
            if before.endswith(tail):
                result = before[:-len(tail)] + replacement if tail else before + replacement
                break
        else:
            result += char
    return result


class ReferenceCases(unittest.TestCase):
    def test_standard_examples(self):
        cases = {
            'Privet, mir!': 'Привет, мир!',
            'sh zh ch shh w jo yo ö je ä ju yu ü ja ya q': 'ш ж ч щ щ ё ё ё э э ю ю ю я я я',
            "tvz mjz # ## ' ''": "ъ ь ъ Ъ ь Ь",
            'rajon raj+on s+h s+hh': 'раён район сх щ',
            'Jo JO jo jO Sh SH sh sH': 'Ё Ё ё йО Ш Ш ш сХ',
            'qwerty QWERTY': 'ящерты ЯЩЕРТЫ',
            '123!? @€🙂\n': '123!? @€🙂\n',
            'йo': 'ё',
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(convert(text), expected)

    def test_german_site_rules_are_distinct(self):
        self.assertEqual(convert('w v z s c h x ei sch tsch', 'rude'), 'в ф ц з с ч кс ай ш ч')
        self.assertEqual(convert('ö ä ü Ö Ä Ü', 'rude'), 'ё э ю Ё Э Ю')

    def test_ukrainian_site_rules(self):
        self.assertEqual(convert("Pryvit! Ukrai'na je g'", 'ua'), 'Привіт! Україна є ґ')
        self.assertEqual(convert("ji Ji JI i' I' g' G' ye Ye YE", 'ua'), 'ї Ї Ї ї Ї ґ Ґ є Є Є')
        self.assertEqual(convert("y i je q ' ''", 'ua'), 'и і є щ ь Ь')

    def test_belarusian_site_rules(self):
        self.assertEqual(convert('Pryvitanne! w i jo je', 'be'), 'Прывітанне! ў і ё э')
        self.assertEqual(convert('w W i I y Y', 'be'), 'ў Ў і І ы Ы')
        self.assertEqual(convert("' \" \"\" ** ch cz sh sz j+o", 'be'),
                         "' ь Ь Ж ч ч ш ш йо")

    def test_lithuanian_accents_case_and_separator(self):
        self.assertEqual(convert('Labas! aa cx ee ex ii sx uu ux zx', 'li'),
                         'Labas! ą č ę ė į š ų ū ž')
        self.assertEqual(convert('Aa AA aA Cx CX cX a+a s+x', 'li'),
                         'Ą Ą aA Č Č cX aa sx')
        self.assertEqual(convert('ąčęėįšųūž ĄČĘĖĮŠŲŪŽ', 'li'),
                         'ąčęėįšųūž ĄČĘĖĮŠŲŪŽ')

    def test_georgian_site_rules(self):
        self.assertEqual(convert("gamarjoba! k' p' t' c' ch' sh gh dz", 'ge'),
                         'გამარჯობა! კ პ ტ წ ჭ შ ღ ძ')
        self.assertEqual(convert('sh Sh SH ch Ch CH', 'ge'), 'შ Შ Შ ჩ Ჩ Ჩ')

    def test_armenian_site_rules(self):
        self.assertEqual(convert('Barev! sh gh jh u &', 'am'), 'Բարեվ! շ ղ ժ ու և')
        self.assertEqual(convert("u U & && o' O' y' Y'", 'am'), 'ու ՈՒ և ԵՒ օ Օ ը Ը')

    def test_hebrew_order_case_and_explicit_final_forms(self):
        self.assertEqual(convert('shloms fs cs ms ns ks kas ha aa ka tt', 'il'),
                         'שלום ף ץ ם ן ך ך ה ע כ ט')
        self.assertEqual(convert('m n f c k SHALOM', 'il'), 'מ נ פ צ ק SHALOM')
        self.assertEqual([ord(c) for c in convert('shloms', 'il')],
                         [0x5E9, 0x5DC, 0x5D5, 0x5DD])

    def test_reverse_scripts(self):
        for mode, source, expected in [
            ('ua', 'Україна є ґ', "Ukrai'na je g'"),
            ('ge', 'გამარჯობა', 'gamarjoba'),
            ('am', 'շ ղ ժ', 'sh gh jh'),
            ('il', 'שלום', 'shlvms'),
            ('be', 'Ў і ь', 'W i "'),
            ('li', 'ą č ę ė į š ų ū ž', 'aa cx ee ex ii sx uu ux zx'),
        ]:
            with self.subTest(mode=mode):
                self.assertEqual(convert(source, mode, reverse=True), expected)

    def test_reverse(self):
        self.assertEqual(convert('Привет, мир!', reverse=True), 'Privet, mir!')

    def test_backspace_removes_visible_letter(self):
        c = Composer()
        self.assertEqual(c.feed('s'), '')
        self.assertEqual(c.feed('h'), '')
        self.assertEqual(c.pending, 'ш')
        self.assertTrue(c.backspace())
        self.assertEqual(c.pending, '')
        self.assertFalse(c.backspace())
        c.feed('j')
        c.feed('+')
        c.backspace()
        self.assertEqual(c.feed('o'), 'ё')

    def test_interruption_breaks_combination(self):
        c = Composer()
        c.feed('s')
        self.assertEqual(c.flush(), 'с')
        self.assertEqual(c.feed('h'), 'х')
        c.feed('s')
        c.clear()
        self.assertEqual(c.feed('h'), 'х')

    def test_engine_ids(self):
        names = [name for name, _, _ in engines()]
        self.assertEqual(len(names), 16)
        self.assertEqual(len(set(names)), len(names))
        for mode, language in [('ua', 'uk'), ('ge', 'ka'), ('am', 'hy'), ('il', 'he'),
                               ('be', 'be'), ('li', 'lt')]:
            self.assertEqual(profiles()[mode]['language'], language)
            for base in ('us', 'de'):
                self.assertIn(f'blind-pew:{mode}:{base}', names)

    def test_prefix_optimization_matches_document_model(self):
        rng = random.Random(21027)
        for mode, profile in profiles().items():
            alphabet = string.ascii_letters + "#+ '\"*!?.,\n1234öäüÖÄÜйысшзтвьъўіąčęėįšųūž🙂"
            for _ in range(1200):
                text = ''.join(rng.choice(alphabet) for _ in range(rng.randrange(1, 160)))
                self.assertEqual(convert(text, mode), whole_document_oracle(text, profile))

    def test_all_context_rules(self):
        for mode, p in profiles().items():
            for char, rules in p['rules'].items():
                for context, _ in rules:
                    text = '🙂' + context + char
                    self.assertEqual(convert(text, mode), whole_document_oracle(text, p))

    def test_buffer_is_bounded_for_long_input(self):
        c = Composer('rude')
        for ch in 'tsch+schx' * 15000:
            c.feed(ch)
            self.assertLessEqual(len(c.pending), 4)
        for mode in profiles():
            self.assertLessEqual(Composer(mode).max_pending, 4)


if __name__ == '__main__':
    unittest.main()
