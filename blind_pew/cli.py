# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
import argparse
import sys
from . import __version__, config, i18n
from .i18n import tr
from .catalog import profile_title
from .core import convert_chunks, engines, profiles


def main():
    i18n.configure(config.load()['ui_language'])
    parser = argparse.ArgumentParser(description='Blind Pew — ' + tr('Transliteration'))
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--ibus', action='store_true', help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('setup', help=tr('Open Blind Pew'))
    commands.add_parser('doctor', help=tr('Check and start IBus'))
    commands.add_parser('list', help=tr('Layout'))
    commands.add_parser('disconnect', help='Remove only Blind Pew sources from your desktop')
    commands.add_parser('toggle', help=tr('Toggle transliteration'))
    converter = commands.add_parser('convert', help=tr('Conversion'))
    converter.add_argument('--profile', choices=list(profiles()), default='ru')
    converter.add_argument('--reverse', action='store_true', help='Selected script to Latin (transliteration profiles)')
    args = parser.parse_args()
    try:
        if args.ibus:
            from .engine import run
            run()
        elif args.command == 'list':
            for name, profile, base in engines():
                print(name, '\t', profile_title(profile['id']), 'QWERTZ' if base == 'de' else 'QWERTY')
        elif args.command == 'convert':
            chunks = iter(lambda: sys.stdin.read(8192), '')
            for text in convert_chunks(chunks, args.profile, args.reverse):
                sys.stdout.write(text)
        elif args.command == 'doctor':
            from .integration import doctor
            return doctor()
        elif args.command == 'disconnect':
            from .hotkey import restore
            restore()
            from .integration import remove_our_engines
            remove_our_engines()
            print(tr('Saved'))
        elif args.command == 'toggle':
            from .hotkey import invoke
            invoke()
        else:
            from .setup import run
            return run()
    except (ImportError, ValueError, RuntimeError, OSError) as error:
        print('Blind Pew:', error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
