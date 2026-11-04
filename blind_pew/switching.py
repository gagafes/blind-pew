# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Serialize global source changes so fast wheel events keep their order."""
def is_translit(source):
    return bool(source and source[0] == 'ibus' and source[1].startswith('blind-pew:'))


class TogglePair:
    """One remembered ordinary source and one selected transliteration."""
    def __init__(self, selected):
        self.selected = selected
        self.normal = None

    def observed(self, source):
        if source and (source[0] == 'xkb' or source[1].startswith('xkb:')):
            self.normal = tuple(source)

    def target(self, current, fallback):
        if is_translit(current):
            self.selected = tuple(current)
            return self.normal or fallback
        return self.selected


class SwitchQueue:
    def __init__(self, activate, error):
        self.activate, self.error = activate, error
        self.current = self.inflight = self.queued = None
        self.stopped = False

    @property
    def target(self):
        return self.queued or self.inflight or self.current

    def observed(self, source):
        if self.stopped or not source or not source[1]:
            return
        self.current = tuple(source)
        if self.inflight and self.current != self.inflight:
            self.queued = self.current

    def request(self, source):
        if self.stopped:
            return
        source = tuple(source)
        if self.inflight:
            self.queued = source
        elif self.current != source:
            self.inflight = source
            self.activate(source, self._done)

    def _done(self, ok, message=''):
        if self.stopped:
            return
        if ok:
            self.current = self.inflight
        elif message:
            self.error(message)
        self.inflight = None
        queued, self.queued = self.queued, None
        if queued:
            self.request(queued)

    def stop(self):
        self.stopped = True
        self.queued = None
