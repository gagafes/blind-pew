#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Refresh known functional tables from saved HTML without executing JavaScript.

Usage: import_reference.py reference_directory [profiles.json]
Only be.html, ua.html, li.html, ge.html, am.html, ru.html, rude.html and il.html
are recognized. Missing pages leave their profiles unchanged. No downloaded
HTML or website code is included in the output.
"""
import argparse
import ast
from datetime import date
import hashlib
import json
from pathlib import Path
import re


def arrays(text, name):
    pattern = rf"{name}\[((?:'(?:\\.|[^'])*')|(?:\"(?:\\.|[^\"])*\"))\] = new Array\s*\((.*?)\);"
    result = {}
    for key, body in re.findall(pattern, text):
        body = re.sub(r'String\.fromCharCode\((\d+)\)',
                      lambda m: repr(chr(int(m[1]))), body)
        values = ast.literal_eval('[' + body + ']')
        if not all(isinstance(v, str) for v in values):
            raise ValueError('Non-string mapping')
        result[ast.literal_eval(key)] = values
    return result


def extract_tables(path):
    html = path.read_text(encoding='utf-8')
    contexts, replacements = arrays(html, 'tra'), arrays(html, 'abc2')
    # Lithuanian only needs ten input keys for its nine accented letters.
    if len(contexts) < 10 or contexts.keys() != replacements.keys():
        raise ValueError(f'Missing or inconsistent tables: {path}')
    rules = {}
    for char, values in contexts.items():
        if len(char) != 1 or len(values) != len(replacements[char]):
            raise ValueError('Invalid input table')
        seen = set()
        rules[char] = []
        for context, replacement in zip(values, replacements[char]):
            if context not in seen:
                rules[char].append([context, replacement])
                seen.add(context)
    reverse = {}
    for key, value in re.findall(r"abc1\[('(?:\\.|[^'])*')\] = ('(?:\\.|[^'])*');", html):
        reverse[ast.literal_eval(key)] = ast.literal_eval(value)
    if len(reverse) < 15:
        raise ValueError('Missing reverse table')
    return dict(rules=rules, reverse=reverse,
                reference_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference_directory', type=Path)
    parser.add_argument('profiles', nargs='?', type=Path,
                        default=Path(__file__).resolve().parent.parent / 'data/profiles.json')
    args = parser.parse_args()
    data = json.loads(args.profiles.read_text(encoding='utf-8'))
    count = 0
    for profile in data['profiles']:
        page = args.reference_directory / (profile['id'] + '.html')
        if page.is_file():
            profile.update(extract_tables(page))
            profile['reference_date'] = date.today().isoformat()
            count += 1
    if not count:
        parser.error('No known reference pages found')
    data['updated_date'] = date.today().isoformat()
    args.profiles.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Refreshed {count} functional tables.')


if __name__ == '__main__':
    main()
