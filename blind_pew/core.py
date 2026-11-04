# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Bounded, rendered-suffix transducer; no desktop or network dependencies."""
from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def profiles():
    path = Path(__file__).resolve().parent.parent / 'data' / 'profiles.json'
    return {p['id']: p for p in json.loads(path.read_text(encoding='utf-8'))['profiles']}


def engines():
    for profile in profiles().values():
        for base in ('us', 'de'):
            yield f"blind-pew:{profile['id']}:{base}", profile, base


class Composer:
    """Hold only a suffix a later character can still change (at most 4 chars).

    The pending string is rendered text, so Backspace removes a visible letter,
    including a letter produced from multiple input keys. Finalized text is
    never read back from the client or edited through synthetic Backspaces.
    """
    def __init__(self, profile_id='ru'):
        self.profile = profiles()[profile_id]
        self.pending = ''
        self.prefixes = set()
        for rules in self.profile.get('rules', {}).values():
            for context, _ in rules:
                self.prefixes.update(context[:i] for i in range(1, len(context) + 1))
        self.max_pending = max(map(len, self.prefixes), default=0)

    def feed(self, char):
        if len(char) != 1:
            raise ValueError('feed requires one Unicode character')
        rendered = self.pending + char
        for context, replacement in self.profile['rules'].get(char, ()):
            if self.pending.endswith(context):
                rendered = self.pending[:len(self.pending) - len(context)] + replacement
                break
        keep = 0
        for size in range(1, min(len(rendered), self.max_pending) + 1):
            if rendered[-size:] in self.prefixes:
                keep = size
        cut = len(rendered) - keep
        committed, self.pending = rendered[:cut], rendered[cut:]
        return committed

    def backspace(self):
        if not self.pending:
            return False
        self.pending = self.pending[:-1]
        return True

    def flush(self):
        text, self.pending = self.pending, ''
        return text

    def clear(self):
        self.pending = ''


def convert(text, profile_id='ru', reverse=False):
    return ''.join(convert_chunks((text,), profile_id, reverse))


def convert_chunks(chunks, profile_id='ru', reverse=False):
    """Convert bounded chunks without losing combinations at their boundaries."""
    profile = profiles()[profile_id]
    if reverse:
        for chunk in chunks:
            yield ''.join(profile['reverse'].get(ch, ch) for ch in chunk)
    else:
        composer = Composer(profile_id)
        for chunk in chunks:
            yield ''.join(composer.feed(ch) for ch in chunk)
        yield composer.flush()
