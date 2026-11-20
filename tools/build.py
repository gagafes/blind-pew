#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
# The import order is intentional: GI versions, runtime checks or sys.path
# bootstrap must precede importing their dependent modules.
# ruff: noqa: E402
"""Build a small architecture-independent .deb without downloading anything."""
import argparse
import gzip
import hashlib
import io
import os
from email.utils import parsedate_to_datetime
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
# This builder only creates and serializes our own XML; it never parses input XML.
import xml.etree.ElementTree as ET  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from blind_pew.core import engines
from blind_pew import __version__, AUTHOR, EMAIL
from blind_pew.i18n import engine_title
from tools.translations import install as install_translations

CHANGELOG = (ROOT / 'debian/changelog').read_text(encoding='utf-8')
VERSION = CHANGELOG.splitlines()[0].split('(', 1)[1].split(')', 1)[0]
if VERSION.rsplit('-', 1)[0] != __version__:
    raise ValueError('Application version and Debian changelog disagree')
RELEASE_DATE = next(line.rsplit('  ', 1)[1] for line in CHANGELOG.splitlines()
                    if line.startswith(' -- '))
DEFAULT_EPOCH = int(parsedate_to_datetime(RELEASE_DATE).timestamp())
HOMEPAGE = 'https://github.com/gagafes/blind-pew'
PACKAGE_NAME = f'blind-pew_{VERSION}_all.deb'


def component_xml():
    component = ET.Element('component')
    fields = {'name': 'org.freedesktop.IBus.BlindPew',
              'description': 'Offline multilingual transliteration',
              'exec': '/usr/bin/blind-pew --ibus',
              'version': __version__, 'license': 'MIT',
              'author': AUTHOR,
              'homepage': HOMEPAGE, 'textdomain': 'blind-pew'}
    for key, value in fields.items():
        ET.SubElement(component, key).text = value
    container = ET.SubElement(component, 'engines')
    for name, profile, base in engines():
        engine = ET.SubElement(container, 'engine')
        fields = {'name': name,
                  'longname': engine_title(profile['id'], base, 'en'),
                  'description': 'Transliteration', 'textdomain': 'blind-pew',
                  'language': profile['language'], 'license': 'MIT',
                  'author': AUTHOR,
                  'icon': 'input-keyboard',
                  'layout': base, 'symbol': profile['symbol'],
                  'setup': '/usr/bin/blind-pew setup', 'rank': '0'}
        for key, value in fields.items():
            ET.SubElement(engine, key).text = value
    ET.indent(component)
    return ET.tostring(component, encoding='utf-8', xml_declaration=True)


def compressed(data):
    # GzipFile writes a portable OS header, unlike older gzip.compress().
    buffer = io.BytesIO()
    with gzip.GzipFile(filename='', fileobj=buffer, mode='wb', mtime=0) as handle:
        handle.write(data)
    return buffer.getvalue()


def stage(dest):
    install_translations(dest)
    dest.chmod(0o755)
    share = dest / 'usr/share/blind-pew'
    modules = share / 'blind_pew'
    modules.mkdir(parents=True)
    for source in (ROOT / 'blind_pew').glob('*.py'):
        shutil.copyfile(source, modules / source.name)
    for source, target in [
        ('assets/blind-pew', 'usr/bin/blind-pew'),
        ('data/profiles.json', 'usr/share/blind-pew/data/profiles.json'),
        ('assets/blind-pew.desktop', 'usr/share/applications/blind-pew.desktop'),
        ('docs/blind-pew-logo.png', 'usr/share/blind-pew/docs/blind-pew-logo.png'),
        ('LICENSE', 'usr/share/doc/blind-pew/LICENSE'),
        ('assets/gnome-extension/LICENSE', 'usr/share/gnome-shell/extensions/blind-pew@local/LICENSE'),
        ('assets/gnome-extension/metadata.json', 'usr/share/gnome-shell/extensions/blind-pew@local/metadata.json'),
        ('assets/gnome-extension/extension.js', 'usr/share/gnome-shell/extensions/blind-pew@local/extension.js'),
    ]:
        target = dest / target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, target)
    (dest / 'usr/bin/blind-pew').chmod(0o755)
    xml = dest / 'usr/share/ibus/component/blind-pew.xml'
    xml.parent.mkdir(parents=True, exist_ok=True)
    xml.write_bytes(component_xml())
    doc = dest / 'usr/share/doc/blind-pew'
    (doc / 'docs').mkdir(exist_ok=True)
    for name in ('README.be.md', 'README.uk.md', 'README.de.md', 'README.ru.md', 'README.md'):
        shutil.copyfile(ROOT / name, doc / name)
    for name in ('TESTING.md', 'REFERENCE.md', 'RELEASE.md', 'LEGAL_REVIEW.md', 'COMPARISON.md'):
        content = (ROOT / 'docs' / name).read_text(encoding='utf-8')
        (doc / 'docs' / name).write_text(content.replace('../CHANGELOG.md', '../changelog.gz'),
                                        encoding='utf-8')
    shutil.copytree(ROOT / 'docs/screenshots', doc / 'docs/screenshots')
    shutil.copyfile(ROOT / 'SECURITY.md', doc / 'SECURITY.md')
    shutil.copyfile(ROOT / 'THIRD_PARTY_NOTICES.md', doc / 'THIRD_PARTY_NOTICES.md')
    shutil.copytree(ROOT / 'LICENSES', doc / 'LICENSES')
    shutil.copyfile(ROOT / 'LICENSE', doc / 'copyright')
    (doc / 'data').symlink_to('../../blind-pew/data')
    (doc / 'docs/blind-pew-logo.png').symlink_to('../../../blind-pew/docs/blind-pew-logo.png')
    (doc / 'changelog.Debian.gz').write_bytes(compressed(CHANGELOG.encode('utf-8')))
    (doc / 'changelog.gz').write_bytes(compressed((ROOT / 'CHANGELOG.md').read_bytes()))
    manual = dest / 'usr/share/man/man1'
    manual.mkdir(parents=True)
    (manual / 'blind-pew.1.gz').write_bytes(compressed((ROOT / 'docs/blind-pew.1').read_bytes()))


def build():
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='blind-pew-build-') as tmp:
        dest = Path(tmp) / 'package'
        stage(dest)
        payload = sorted(p for p in dest.rglob('*') if p.is_file() and not p.is_symlink())
        size = (sum(p.stat().st_size for p in payload) + 1023) // 1024
        control = dest / 'DEBIAN'
        control.mkdir()
        (control / 'control').write_text(
            f'Package: blind-pew\nVersion: {VERSION}\nArchitecture: all\n'
            f'Maintainer: {AUTHOR} <{EMAIL}>\n'
            f'Homepage: {HOMEPAGE}\n'
            'Section: utils\nPriority: optional\n'
            f'Installed-Size: {size}\n'
            'Depends: python3 (>= 3.10), python3-gi, gir1.2-ibus-1.0, gir1.2-gtk-3.0, '
            'ibus (>= 1.5.29), ibus-gtk3, ibus-gtk4, im-config, xfconf, libxfconf-0-3, gir1.2-ayatanaappindicator3-0.1\n'
            'Suggests: gnome-shell-extension-appindicator\n'
            'Description: Blind Pew keyboard switcher and offline transliteration\n'
            ' Independent IBus engine implementing functional input tables of\n'
            ' Translit.ru for Belarusian, Ukrainian, Lithuanian, Georgian,\n'
            ' Armenian, Russian and Hebrew. An Arabic phonetic profile is also included.\n'
            ' Supports input in GTK3 and GTK4 applications.\n'
            ' Includes eight transliteration languages, global F12 and mouse-wheel\n'
            ' on/off switching and automatic IBus startup.\n'
            ' Native GTK preferences include a live input-source tray indicator.\n'
            ' Designed for Debian 13 and Ubuntu 24.04, GNOME and Xfce.\n', encoding='utf-8')
        # Debian's md5sums format is for installed-file checks. Published
        # downloads use SHA-256; no security decision relies on this MD5.
        (control / 'md5sums').write_text(''.join(
            f'{hashlib.md5(p.read_bytes(), usedforsecurity=False).hexdigest()}  {p.relative_to(dest)}\n'  # nosec B303
            for p in payload), encoding='utf-8')
        for p in dest.rglob('*'):
            if p.is_dir():
                p.chmod(0o755)
            elif not p.is_symlink() and p != dest / 'usr/bin/blind-pew':
                p.chmod(0o644)
        epoch = int(os.environ.get('SOURCE_DATE_EPOCH', str(DEFAULT_EPOCH)))
        for p in sorted(dest.rglob('*'), reverse=True):
            os.utime(p, (epoch, epoch), follow_symlinks=False)
        os.utime(dest, (epoch, epoch))
        artifact = output / PACKAGE_NAME
        subprocess.run(['dpkg-deb', '--root-owner-group', '-Zxz', '-z9', '--build',
                        str(dest), str(artifact)], check=True,
                       env={**os.environ, 'SOURCE_DATE_EPOCH': str(epoch)})
        print(f'{artifact}: {artifact.stat().st_size} bytes; payload {size} KiB')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--print-package-name', action='store_true',
                        help='print the expected DEB filename without building')
    if parser.parse_args().print_package_name:
        print(PACKAGE_NAME)
    else:
        build()
