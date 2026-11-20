# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Andrey Popovich
import unittest
from unittest.mock import patch

from tools import collect_github_metrics as metrics


class GitHubMetrics(unittest.TestCase):
    def test_downloads_need_a_previous_observation_of_the_asset(self):
        snapshots = {
            '2026-11-01': {'first': {'downloads': 4}},
            '2026-11-02': {'second': {'downloads': 7}},
            '2026-11-03': {'second': {'downloads': 7}},
            '2026-11-04': {'second': {'downloads': 9}},
        }
        self.assertEqual(metrics.download_deltas(snapshots), {
            '2026-11-01': '', '2026-11-02': '', '2026-11-03': 0, '2026-11-04': 2,
        })

    def test_monthly_totals_distinguish_absent_values_from_zero(self):
        rows = [
            {'date': '2026-10-31', 'views': '', 'clones': 0, 'observed_new_downloads': ''},
            {'date': '2026-11-01', 'views': 4, 'clones': '', 'observed_new_downloads': 0},
        ]
        months = metrics.monthly(rows)
        self.assertEqual(months, [
            {'month': '2026-10', 'views': None, 'clones': 0, 'observed_new_downloads': None},
            {'month': '2026-11', 'views': 4, 'clones': None, 'observed_new_downloads': 0},
        ])
        self.assertNotIn('No recorded data', metrics.svg_chart(months, 'clones', 'Clones'))

    def test_draft_release_assets_are_not_counted(self):
        asset = {'id': 1, 'name': 'package.deb', 'download_count': 4}
        draft = {'draft': True, 'tag_name': 'v0.2.0-1', 'assets': [asset]}
        release = {'draft': False, 'tag_name': 'v0.1.0-2', 'assets': [{**asset, 'id': 2}]}
        with patch.object(metrics, 'request', return_value=[draft, release]):
            self.assertEqual(metrics.releases('owner/repo', 'token'), {
                '2': {'release': 'v0.1.0-2', 'name': 'package.deb', 'downloads': 4},
            })
