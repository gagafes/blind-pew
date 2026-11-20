# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
"""Offline tests for the release workflow's artifact and CI guards."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / '.github/scripts/publish-release.py'
SPEC = importlib.util.spec_from_file_location('publish_release', SCRIPT)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class ReleaseChecks(unittest.TestCase):
    def test_ci_run_must_match_successful_main_checkout_and_workflow(self):
        commit = 'a' * 40
        run = {
            'head_sha': commit, 'head_branch': 'main',
            'head_repository': {'full_name': publisher.REPO},
            'path': publisher.WORKFLOW + '@main', 'event': 'push',
            'status': 'completed', 'conclusion': 'success',
        }
        publisher.verify_run(run, commit)
        for key, value in {
            'head_sha': 'b' * 40, 'head_branch': 'feature',
            'head_repository': {'full_name': 'another/repo'},
            'path': '.github/workflows/other.yml', 'event': 'pull_request',
            'status': 'in_progress', 'conclusion': 'failure',
        }.items():
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                publisher.verify_run({**run, key: value}, commit)

    def test_only_matching_artifact_metadata_and_checksum_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / 'blind-pew_0.2.0-1_all.deb'
            sums = Path(tmp) / 'SHA256SUMS'
            package.write_bytes(b'package from CI')
            digest = hashlib.sha256(package.read_bytes()).hexdigest()
            sums.write_text(f'{digest}  {package.name}\n', encoding='utf-8')
            fields = 'Package: blind-pew\nVersion: 0.2.0-1\nArchitecture: all\n'
            with patch.object(publisher.subprocess, 'check_output', return_value=fields):
                self.assertEqual(publisher.verify_package(package, sums, '0.2.0-1'), digest)
                with self.assertRaisesRegex(RuntimeError, 'metadata'):
                    publisher.verify_package(package, sums, '0.3.0-1')
                package.write_bytes(b'different bytes')
                with self.assertRaisesRegex(RuntimeError, 'checksum'):
                    publisher.verify_package(package, sums, '0.2.0-1')
