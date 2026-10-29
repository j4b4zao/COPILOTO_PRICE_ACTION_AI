"""Pre-fix INT-108 integration counterexamples; storage adapters are explicit fixtures."""
import json
from pathlib import Path
import tempfile
import unittest
import test_f3_int107_typed_batch_chain as prior
from tools.f3_int106_typed_batch_manifest import TypedBatchEntry
from tools.f3_int107_typed_batch_chain import ChainBatch, build_typed_chain
from tools.f3_int108_typed_chain_guard import verify_typed_chain


class BeforePersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.TypedBatchChainTests.setUpClass()
        cls.segments = (prior.TypedBatchChainTests.segment,)
        cls.args = dict(context='audit:A',purpose='review',run_id='run:1',
                        batches=(ChainBatch((TypedBatchEntry('audit','x'),),1),))
        cls.pin = build_typed_chain(cls.segments, **cls.args).digest

    def check(self, state):
        return verify_typed_chain(self.segments, **self.args, expected_digest=self.pin,
                                  minimum_revision=state['floor'],
                                  consumed_chain_digests=frozenset(state['consumed']))

    def test_rollback_of_entire_caller_state(self):
        old = dict(floor=1,consumed=[])
        self.assertEqual(self.check(old).status,'CHAIN_FIXTURE_UNAUTHENTICATED')
        current = dict(floor=2,consumed=[self.pin])
        self.assertNotEqual(self.check(current).status,'CHAIN_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.check(json.loads(json.dumps(old))).status,'CHAIN_FIXTURE_UNAUTHENTICATED')

    def test_restart_loses_memory_history(self):
        self.assertEqual(self.check(dict(floor=1,consumed=[])).status,'CHAIN_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.check(dict(floor=1,consumed=[])).status,'CHAIN_FIXTURE_UNAUTHENTICATED')

    def test_two_consumers_same_snapshot(self):
        state = dict(floor=1,consumed=[])
        a,b = self.check(state),self.check(state)
        self.assertEqual((a.status,b.status),('CHAIN_FIXTURE_UNAUTHENTICATED',)*2)

    def test_interrupted_naive_json_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.json'
            path.write_text('{"floor":2,"consumed":[')
            with self.assertRaises(json.JSONDecodeError):
                json.loads(path.read_text())
            # Explicitly demonstrate the UNSAFE caller fallback, not INT-108 IO.
            self.assertEqual(self.check(dict(floor=1,consumed=[])).status,'CHAIN_FIXTURE_UNAUTHENTICATED')

    def test_parseable_corruption_erases_consumption(self):
        corrupted=json.loads('{"floor":1,"consumed":[]}')
        self.assertEqual(self.check(corrupted).status,'CHAIN_FIXTURE_UNAUTHENTICATED')


if __name__=='__main__':
    unittest.main(verbosity=2)
