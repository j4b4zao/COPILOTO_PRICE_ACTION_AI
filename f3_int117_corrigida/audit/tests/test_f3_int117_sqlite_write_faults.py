"""Native SQLite write failures, fresh disposable fixtures and retained anchors."""
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import unittest
import test_f3_int109_offline_consumption_store as prior
from tools import f3_int109_offline_consumption_store as store
from tools.f3_int114_custody_recovery import LOCKS
from tools.f3_int117_sqlite_write_faults import ProbeError, run_experiment, validate_attempt, safe_to_promote


class WriteFaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.ConsumptionStoreTests.setUpClass()
        source = prior.ConsumptionStoreTests
        cls.inputs = dict(segments=source.segments, previous_batches=source.batches,
                          batches=source.next_batches, scope=source.scope)
        cls.original_connect = store._connect
        cls.original_consume = store.consume_chain
        cls.results = {mode: run_experiment(mode, **cls.inputs) for mode in ('normal', 'full', 'readonly')}
        for result in cls.results.values():
            print(json.dumps(dict(experiment='F3-INT-117', **result)), flush=True)

    def test_sqlite_full_native_error(self):
        result = self.results['full']
        self.assertEqual(result['attempt']['error']['primary_code'], sqlite3.SQLITE_FULL)
        self.assertEqual(result['attempt']['error']['sqlite_errorname'], 'SQLITE_FULL')
        self.assertFalse(result['attempt']['committed'])

    def test_sqlite_readonly_native_error(self):
        result = self.results['readonly']
        self.assertEqual(result['attempt']['error']['primary_code'], sqlite3.SQLITE_READONLY)
        self.assertEqual(result['attempt']['configuration']['access'], 'ro')
        self.assertEqual(result['attempt']['configuration']['query_only'], 0)
        self.assertFalse(result['attempt']['committed'])

    def test_growth_and_effective_same_connection_page_limit(self):
        result = self.results['full']; control = result['growth_control']
        self.assertGreater(control['pages_after'], control['pages_before'])
        self.assertTrue(control['same_initial_bytes'])
        self.assertEqual(result['attempt']['configuration']['max_page_count'], control['pages_before'])
        self.assertEqual(result['attempt']['configuration']['page_count'], control['pages_before'])
        self.assertEqual(result['reopened_pages'], control['pages_before'])

    def test_exact_api_failure_phases_and_no_commit_after_error(self):
        for mode in ('full', 'readonly'):
            attempt = self.results[mode]['attempt']
            self.assertEqual(attempt['error']['phase'], 'UPDATE')
            self.assertIn('update_entered', attempt['events'])
            self.assertIn('sqlite_error_UPDATE', attempt['events'])
            self.assertNotIn('update_returned', attempt['events'])
            self.assertNotIn('commit_entered', attempt['events'])
            self.assertEqual(attempt['events'][-1], 'connection_closed')

    def test_normal_control_commits_expected_state(self):
        result = self.results['normal']
        self.assertIsNone(result['attempt']['error'])
        self.assertTrue(result['attempt']['committed'])
        self.assertEqual(result['reopened_state'], result['expected_after'])
        self.assertIn('commit_returned', result['attempt']['events'])

    def test_reopened_integrity_and_exact_failure_state(self):
        for mode, result in self.results.items():
            self.assertEqual(result['integrity_check'], 'ok')
            self.assertEqual(result['reopened_state'], result['expected_after' if mode == 'normal' else 'expected_before'])
            if mode != 'normal':
                self.assertTrue(result['database_unchanged_on_failure'])

    def test_reconciliation_and_no_automatic_retry(self):
        for mode, result in self.results.items():
            expected = ('COMMITTED' if mode == 'normal' else 'NOT_COMMITTED') + '_OBSERVED_UNAUTHENTICATED'
            self.assertEqual(result['reconciliation']['status'], expected)
            self.assertFalse(result['reconciliation']['retry_allowed'])
            self.assertFalse(result['retry_allowed'])
            self.assertEqual(result['automatic_retries'], 0)

    def test_prior_and_newly_committed_replays_rejected(self):
        for mode, result in self.results.items():
            expected = ['STATE_ANCHOR_MISMATCH', 'STALE_CHAIN_REVISION'] * (2 if mode == 'normal' else 1)
            self.assertEqual([r['status'] for r in result['replays']], expected)

    def test_divergent_missing_and_retained_anchors(self):
        for result in self.results.values():
            self.assertEqual(result['divergent_anchors']['status'], 'RECONCILIATION_UNRESOLVED')
            self.assertFalse(result['divergent_anchors']['retry_allowed'])
            self.assertEqual(result['missing_anchor']['status'], 'INVALID_RECONCILIATION_PIN')
            self.assertFalse(result['missing_anchor']['retry_allowed'])
            self.assertEqual(result['retained_sha256_before'], result['retained_sha256_after'])

    def test_resources_removed_and_global_functions_unchanged(self):
        self.assertIs(store._connect, type(self).original_connect)
        self.assertIs(store.consume_chain, type(self).original_consume)
        for result in self.results.values():
            self.assertTrue(result['fixture_removed'])
            self.assertFalse(Path(result['fixture_directory']).exists())
            self.assertEqual(result['attempt']['events'][-1], 'connection_closed')

    def test_safety_locks_and_promotion_blocked(self):
        for result in self.results.values():
            self.assertEqual(result['f3'], 'OPEN')
            self.assertEqual(set(result['locks']), set(LOCKS))
            self.assertTrue(all(value is False for value in result['locks'].values()))
            self.assertFalse(result['certification'])
            self.assertFalse(result['promoted'])
        self.assertFalse(safe_to_promote())

    def test_invalid_inputs_or_missing_fault_evidence_fail_closed(self):
        for mode in ('unsupported', '', None):
            with self.assertRaises(ProbeError):
                run_experiment(mode, **self.inputs)
        with self.assertRaises(ProbeError):
            run_experiment('full', **self.inputs, page_size=True)
        for mode in ('full', 'readonly'):
            with self.assertRaises(ProbeError):
                validate_attempt(mode, self.results['normal']['attempt'])


if __name__ == '__main__':
    unittest.main()
