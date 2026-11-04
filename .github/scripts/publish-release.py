#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Publish only the maintainer-approved 0.1.0-2 commit and verified assets."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

REPO = 'gagafes/blind-pew'
TAG = 'v0.1.0-2'
COMMIT = 'fcd66d7577e4053a6a2c1b71c2374ecd8190f940'
CI_RUN = 41887476222
DEB = 'blind-pew_0.1.0-2_all.deb'
DIGEST = '2dd3c0177a11809d89a15f039d54fec3fe2775a751f3a9fa6484a8e242da28a6'


def gh(*args):
    result = subprocess.run(['gh', *args], check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('GitHub CLI failed: ' + result.stderr.strip())
    return result.stdout


def api(path):
    return json.loads(gh('api', 'repos/' + REPO + '/' + path))


def find_release():
    matches = [release for release in api('releases?per_page=100')
               if release['tag_name'] == TAG]
    if len(matches) > 1:
        raise RuntimeError('Multiple releases use the approved tag')
    return matches[0] if matches else None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_tag():
    obj = api('git/ref/tags/' + TAG)['object']
    for _ in range(4):
        if obj['type'] != 'tag':
            break
        obj = api('git/tags/' + obj['sha'])['object']
    require(obj['type'] == 'commit' and obj['sha'] == COMMIT,
            'The release tag does not point to the approved commit')


def main():
    source = Path('.release-source')
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    require(actual == COMMIT, 'The source checkout is not the approved commit')
    run = api('actions/runs/' + str(CI_RUN))
    require(run['head_sha'] == COMMIT and run['head_branch'] == 'main'
            and run['status'] == 'completed' and run['conclusion'] == 'success',
            'The approved source commit has not passed its complete CI run')
    package = source / 'downloads' / DEB
    require(hashlib.sha256(package.read_bytes()).hexdigest() == DIGEST,
            'The release package checksum does not match the tested artifact')
    notes = Path('.github/release-notes') / (TAG + '.md')
    require(notes.is_file() and notes.stat().st_size > 100, 'Release notes are missing')
    tags = api('git/matching-refs/tags/' + TAG)
    if any(tag['ref'] == 'refs/tags/' + TAG for tag in tags):
        verify_tag()

    with tempfile.TemporaryDirectory(prefix='blind-pew-release-', dir=os.environ['RUNNER_TEMP']) as tmp:
        root = Path(tmp)
        shutil.copyfile(package, root / DEB)
        (root / 'SHA256SUMS').write_text(DIGEST + '  ' + DEB + '\n', encoding='utf-8')
        assets = [root / DEB, root / 'SHA256SUMS']
        release = find_release()
        if release is None:
            gh('release', 'create', TAG, '--repo', REPO, '--target', COMMIT,
               '--title', 'Blind Pew 0.1.0-2', '--draft', '--notes-file', str(notes),
               *map(str, assets))
            release = find_release()
        require(release is not None, 'The release was not created')
        require(not release['prerelease'], 'An unexpected prerelease already uses this tag')
        if release['draft']:
            require(release['target_commitish'] == COMMIT, 'The draft targets another commit')
            require(release['body'].strip() == notes.read_text(encoding='utf-8').strip(),
                    'An existing draft contains different release notes')
            present = {asset['name'] for asset in release['assets']}
            missing = [str(asset) for asset in assets if asset.name not in present]
            if missing:
                gh('release', 'upload', TAG, '--repo', REPO, *missing)
        else:
            verify_tag()

        # Download the actual uploaded bytes before making the draft public.
        verify = root / 'downloaded'
        verify.mkdir()
        gh('release', 'download', TAG, '--repo', REPO, '--dir', str(verify),
           '--pattern', DEB, '--pattern', 'SHA256SUMS')
        for asset in assets:
            require((verify / asset.name).read_bytes() == asset.read_bytes(),
                    'Uploaded release asset differs: ' + asset.name)
        if release['draft']:
            gh('release', 'edit', TAG, '--repo', REPO, '--draft=false', '--latest')
        published = api('releases/tags/' + TAG)
        require(not published['draft'] and not published['prerelease']
                and published['published_at'], 'The release is not public')
        require({DEB, 'SHA256SUMS'} <= {asset['name'] for asset in published['assets']},
                'Published release assets are missing')
        verify_tag()
        public_download = root / 'published'
        public_download.mkdir()
        gh('release', 'download', TAG, '--repo', REPO, '--dir', str(public_download),
           '--pattern', DEB, '--pattern', 'SHA256SUMS')
        for asset in assets:
            require((public_download / asset.name).read_bytes() == asset.read_bytes(),
                    'Published release download differs: ' + asset.name)
        print('Published:', published['html_url'])
        print('Commit:', COMMIT)
        print('DEB SHA-256:', DIGEST)


if __name__ == '__main__':
    main()
