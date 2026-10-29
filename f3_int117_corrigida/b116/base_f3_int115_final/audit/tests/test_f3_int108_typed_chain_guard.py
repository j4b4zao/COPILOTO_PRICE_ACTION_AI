import unittest
from dataclasses import replace
import test_f3_int107_typed_batch_chain as prior
from tools.f3_int106_typed_batch_manifest import TypedBatchEntry
from tools.f3_int107_typed_batch_chain import ChainBatch, build_typed_chain
from tools.f3_int108_typed_chain_guard import verify_typed_chain, safe_to_promote


class ChainGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.TypedBatchChainTests.setUpClass()
        cls.segments = (prior.TypedBatchChainTests.segment,)
        cls.batches = tuple(ChainBatch((TypedBatchEntry('audit', x),), i)
                            for i, x in enumerate(('x', 'y', 'z'), 1))
        cls.args = dict(context='audit:fixture/A', purpose='evidence-review',
                        run_id='run:1', batches=cls.batches)
        cls.pin = build_typed_chain(cls.segments, **cls.args).digest

    def call(self, **changes):
        args = dict(self.args, expected_digest=self.pin, minimum_revision=1,
                    consumed_chain_digests=frozenset())
        args.update(changes)
        return verify_typed_chain(self.segments, **args)

    def test_complete(self):
        self.assertEqual(self.call().status, 'CHAIN_FIXTURE_UNAUTHENTICATED')

    def test_prefix_truncation(self):
        self.assertEqual(self.call(batches=self.batches[1:]).status, 'CHAIN_DIGEST_MISMATCH')

    def test_suffix_truncation(self):
        self.assertEqual(self.call(batches=self.batches[:-1]).status, 'CHAIN_DIGEST_MISMATCH')

    def test_middle_removal(self):
        self.assertEqual(self.call(batches=self.batches[::2]).status, 'CHAIN_DIGEST_MISMATCH')

    def test_middle_substitution(self):
        altered = (self.batches[0], ChainBatch((TypedBatchEntry('report','other'),),2), self.batches[2])
        self.assertEqual(self.call(batches=altered).status, 'CHAIN_DIGEST_MISMATCH')

    def test_consumed_replay(self):
        self.assertEqual(self.call(consumed_chain_digests=frozenset((self.pin,))).status,
                         'CHAIN_ALREADY_CONSUMED')

    def test_old_chain_with_matching_old_pin(self):
        self.assertEqual(self.call(minimum_revision=4).status, 'STALE_CHAIN_REVISION')

    def test_floor_checks_first_revision(self):
        self.assertEqual(self.call(minimum_revision=2).status, 'STALE_CHAIN_REVISION')

    def test_unrelated_consumed_chain(self):
        self.assertEqual(self.call(consumed_chain_digests=frozenset(('0'*64,))).digest, self.pin)

    def test_context_purpose_run_and_revision_mismatch(self):
        for change in (dict(context='audit:B'), dict(purpose='other'), dict(run_id='run:2'),
                       dict(batches=tuple(replace(b, revision=b.revision+3) for b in self.batches))):
            with self.subTest(change=change):
                self.assertEqual(self.call(**change).status, 'CHAIN_DIGEST_MISMATCH')

    def test_required_pin(self):
        for pin in (None, True, 'bad', 'G'*64):
            with self.subTest(pin=pin):
                self.assertEqual(self.call(expected_digest=pin).status, 'INVALID_REQUIRED_CHAIN_PIN')

    def test_invalid_floor(self):
        for floor in (True, -1, 1.0, '1', 2147483648):
            with self.subTest(floor=floor):
                self.assertEqual(self.call(minimum_revision=floor).status, 'INVALID_MINIMUM_REVISION')

    def test_invalid_history(self):
        for history in (None, (), set(), frozenset((True,)), frozenset(('bad',)),
                        frozenset(format(i,'064x') for i in range(4097))):
            with self.subTest(history=str(history)[:40]):
                self.assertEqual(self.call(consumed_chain_digests=history).status,
                                 'INVALID_CONSUMED_CHAIN_DIGESTS')

    def test_existing_validation_delegated(self):
        for batches, status in (((), 'INVALID_BATCHES'),
                                ((self.batches[1],self.batches[0]), 'INVALID_REVISION_SEQUENCE')):
            with self.subTest(status=status):
                self.assertEqual(self.call(batches=batches).status, status)

    def test_required_arguments_cannot_be_omitted(self):
        for key in ('expected_digest','minimum_revision','consumed_chain_digests'):
            args = dict(self.args, expected_digest=self.pin, minimum_revision=1,
                        consumed_chain_digests=frozenset())
            del args[key]
            with self.subTest(key=key), self.assertRaises(TypeError):
                verify_typed_chain(self.segments, **args)

    def test_locks_and_no_state_mutation(self):
        history = frozenset()
        for result in (self.call(consumed_chain_digests=history), self.call(expected_digest=None)):
            self.assertEqual(result.f3, 'OPEN')
            self.assertFalse(safe_to_promote(result))
            for key in ('orders_allowed','live_certified','flow_complete','f3_resolved',
                        'native_prototype_authorized','strict_deadline_guaranteed',
                        'authenticated_witness_verified'):
                self.assertIs(getattr(result,key), False)
        self.assertEqual(history, frozenset())


if __name__ == '__main__':
    unittest.main()
