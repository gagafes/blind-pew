#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Publish the package from a successful CI run on the selected main commit."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

REPO = 'gagafes/blind-pew'
WORKFLOW = '.github/workflows/ci.yml'
ARTIFACT = 'blind-pew-ubuntu-24.04'


def gh(*args):
    result = subprocess.run(['gh', *args], check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('GitHub CLI failed: ' + result.stderr.strip())
    return result.stdout


def api(path):
    return json.loads(gh('api', 'repos/' + REPO + '/' + path))


def find_release(tag):
    pages = json.loads(gh('api', '--paginate', '--slurp',
                          'repos/' + REPO + '/releases?per_page=100'))
    matches = [release for page in pages for release in page if release['tag_name'] == tag]
    require(len(matches) <= 1, 'Multiple releases use the selected tag')
    return matches[0] if matches else None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_run(run, commit):
    require(run['head_sha'] == commit and run['head_branch'] == 'main'
            and run['head_repository']['full_name'] == REPO
            and run['path'].split('@', 1)[0] == WORKFLOW
            and run['event'] in ('push', 'workflow_dispatch')
            and run['status'] == 'completed' and run['conclusion'] == 'success',
            'Select a successful full CI run on this exact main commit')


def verify_tag(tag, commit):
    obj = api('git/ref/tags/' + tag)['object']
    for _ in range(4):
        if obj['type'] != 'tag':
            break
        obj = api('git/tags/' + obj['sha'])['object']
    require(obj['type'] == 'commit' and obj['sha'] == commit,
            'The release tag does not point to the tested commit')


def verify_package(package, checksums, version):
    fields = subprocess.check_output(
        ['dpkg-deb', '--field', str(package), 'Package', 'Version', 'Architecture'],
        text=True,
    ).splitlines()
    require(set(fields) == {'Package: blind-pew', f'Version: {version}', 'Architecture: all'},
            'The CI package metadata does not match this release')
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    require(checksums.read_text(encoding='utf-8') == f'{digest}  {package.name}\n',
            'The CI package checksum does not match SHA256SUMS')
    return digest


def verify_release_assets(tag, assets, directory):
    directory.mkdir()
    args = [option for asset in assets for option in ('--pattern', asset.name)]
    gh('release', 'download', tag, '--repo', REPO, '--dir', str(directory), *args)
    for asset in assets:
        require((directory / asset.name).read_bytes() == asset.read_bytes(),
                'Release download differs from the tested CI asset: ' + asset.name)


def main():
    ci_run_id = os.environ['CI_RUN_ID']
    require(ci_run_id.isascii() and ci_run_id.isdecimal(), 'CI run ID must be a number')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    require(commit == os.environ['GITHUB_SHA'], 'The checkout is not the selected main commit')
    verify_run(api('actions/runs/' + ci_run_id), commit)

    package_name = subprocess.check_output(
        ['python3', 'tools/build.py', '--print-package-name'], text=True).strip()
    match = re.fullmatch(r'blind-pew_([0-9]+\.[0-9]+\.[0-9]+-[0-9]+)_all\.deb', package_name)
    require(match is not None, 'Unsupported release package version')
    version = match.group(1)
    tag = 'v' + version
    notes = Path('.github/release-notes') / (tag + '.md')
    require(notes.is_file(), 'Release notes are missing: ' + str(notes))
    notes_body = notes.read_text(encoding='utf-8').strip()
    require(notes_body, 'Release notes are empty')
    tags = api('git/matching-refs/tags/' + tag)
    if any(ref['ref'] == 'refs/tags/' + tag for ref in tags):
        verify_tag(tag, commit)

    with tempfile.TemporaryDirectory(prefix='blind-pew-release-', dir=os.environ['RUNNER_TEMP']) as tmp:
        root = Path(tmp)
        ci = root / 'ci'
        gh('run', 'download', ci_run_id, '--repo', REPO, '--name', ARTIFACT, '--dir', str(ci))
        assets = [ci / package_name, ci / 'SHA256SUMS']
        digest = verify_package(*assets, version)
        release = find_release(tag)
        if release is None:
            gh('release', 'create', tag, '--repo', REPO, '--target', commit,
               '--title', 'Blind Pew ' + version, '--draft', '--notes-file', str(notes),
               *map(str, assets))
            release = find_release(tag)
        require(release is not None, 'The release was not created')
        require(not release['prerelease'], 'An unexpected prerelease already uses this tag')
        if release['draft']:
            require(release['target_commitish'] == commit, 'The draft targets another commit')
            require((release['body'] or '').strip() == notes_body,
                    'The draft contains different release notes')
            expected = {asset.name for asset in assets}
            present = {asset['name'] for asset in release['assets']}
            require(present <= expected, 'The draft contains unexpected assets')
            missing = [str(asset) for asset in assets if asset.name not in present]
            if missing:
                gh('release', 'upload', tag, '--repo', REPO, *missing)
        else:
            verify_tag(tag, commit)

        verify_release_assets(tag, assets, root / 'downloaded')
        if release['draft']:
            gh('release', 'edit', tag, '--repo', REPO, '--draft=false', '--latest')
        published = api('releases/tags/' + tag)
        require(not published['draft'] and not published['prerelease']
                and published['published_at'], 'The release is not public')
        verify_tag(tag, commit)
        verify_release_assets(tag, assets, root / 'published')
        print('Published:', published['html_url'])
        print('Commit:', commit)
        print('DEB SHA-256:', digest)


if __name__ == '__main__':
    main()
