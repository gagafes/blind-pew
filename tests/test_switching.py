import unittest
from blind_pew.switching import SwitchQueue, TogglePair
from blind_pew.catalog import source_for


class GlobalSwitching(unittest.TestCase):
    def setUp(self):
        self.calls, self.errors = [], []
        self.queue = SwitchQueue(lambda source, done: self.calls.append((source,done)),self.errors.append)
        self.queue.observed(source_for('ru','de'))
        self.native = ('ibus', 'xkb:de::ger')
        self.pair = TogglePair(source_for('ru', 'de'))
        self.pair.observed(self.native)

    def finish(self, ok=True):
        source, done = self.calls[-1]
        if ok:self.queue.observed(source)
        done(ok,'' if ok else 'failed')

    def test_three_fast_toggles_end_with_native_source(self):
        for _ in range(3):self.queue.request(self.pair.target(self.queue.target, None))
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.queue.target,self.native)
        self.finish()
        self.assertEqual(self.queue.current,self.native)
        self.assertIsNone(self.queue.inflight)

    def test_reverse_while_busy_returns_to_start(self):
        self.queue.request(self.pair.target(self.queue.target, None))
        self.queue.request(self.pair.target(self.queue.target, None))
        self.finish(); self.finish()
        self.assertEqual(self.queue.current,source_for('ru','de'))

    def test_external_selection_wins_over_queued_switch(self):
        self.queue.request(source_for('ua','de'))
        self.queue.request(source_for('be','de'))
        self.queue.observed(('ibus','xkb:de::ger'))
        self.finish(); self.finish()
        self.assertEqual(self.queue.current,('ibus','xkb:de::ger'))

    def test_failed_switch_preserves_current_source(self):
        self.queue.request(source_for('ua','de'))
        self.finish(False)
        self.assertEqual(self.queue.current,source_for('ru','de'))
        self.assertEqual(self.errors,['failed'])

    def test_shutdown_ignores_late_callback(self):
        self.queue.request(source_for('ua','de'))
        self.queue.stop();self.finish(False)
        self.assertFalse(self.errors)


class OnOff(unittest.TestCase):
    def test_toggle_keeps_one_selected_translit_and_last_native(self):
        selected, native = source_for('ua', 'de'), ('xkb', 'de+nodeadkeys')
        pair = TogglePair(selected)
        pair.observed(native)
        self.assertEqual(pair.target(native, None), selected)
        pair.observed(selected)
        self.assertEqual(pair.target(selected, None), native)
        self.assertEqual(pair.target(native, None), selected)

    def test_changing_selected_translit_keeps_the_native_source(self):
        pair = TogglePair(source_for('ua', 'de'))
        native = ('ibus', 'xkb:de::ger')
        pair.observed(native)
        for ident in ('ua', 'be', 'li', 'ge'):
            selected = source_for(ident, 'de')
            pair.observed(selected)
            pair.selected = selected
            self.assertEqual(pair.target(selected, None), native)
            self.assertEqual(pair.target(native, None), selected)

    def test_start_with_translit_uses_native_fallback(self):
        pair = TogglePair(source_for('ua'))
        self.assertEqual(pair.target(source_for('il'), ('xkb', 'us')), ('xkb', 'us'))
        self.assertEqual(pair.target(('xkb', 'us'), None), source_for('il'))

    def test_two_rapid_toggles_end_off(self):
        native, selected = ('ibus', 'xkb:de::ger'), source_for('ua', 'de')
        calls = []
        pair = TogglePair(selected)
        pair.observed(native)
        queue = SwitchQueue(lambda source, done: calls.append((source, done)), self.fail)
        queue.observed(native)
        queue.request(pair.target(queue.target, None))
        queue.request(pair.target(queue.target, None))
        self.assertEqual(queue.target, native)
        queue.observed(selected); calls[0][1](True)
        queue.observed(native); calls[1][1](True)
        self.assertEqual(queue.current, native)
