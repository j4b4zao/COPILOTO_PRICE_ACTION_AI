import unittest
from tools.f3_int34_persistence_simulator import Authority
from tools.f3_int36_anchor_rollback_simulator import Anchor
from tools.f3_int37_coordinated_attack_simulator import (
    ClaimedAnchor, inspect_claim, coordinated_rewrite,
    requirements_for_authenticated_anchor, safe_to_promote,
)


class CoordinatedAnchorAttackTests(unittest.TestCase):
    def setUp(self):
        a = Authority()
        e = a.lease('original')
        for event in ('FENCE', 'JOB_EMPTY', 'CLEANUP'):
            a.append('original', e, event)
        self.records = a.snapshot()
        self.claim = ClaimedAnchor(Anchor(3, self.records[-1].checksum), 'issuer', 7)

    def test_self_consistent_coordinated_rewrite_does_not_authenticate(self):
        rewritten = coordinated_rewrite(self.records, ('FENCE', 'FAKE_JOB_EMPTY', 'CLEANUP'))
        fake = ClaimedAnchor(Anchor(3, rewritten[-1].checksum), 'issuer', 7)
        result = inspect_claim(rewritten, fake)
        self.assertTrue(result.journal_matches)
        self.assertEqual(result.status, 'UNAUTHENTICATED_CLAIM')
        self.assertFalse(result.authoritative or result.closure_authorized)

    def test_trusted_reference_rejects_coordinated_rewrite(self):
        rewritten = coordinated_rewrite(self.records, ('FENCE', 'FAKE_JOB_EMPTY', 'CLEANUP'))
        fake = ClaimedAnchor(Anchor(3, rewritten[-1].checksum), 'issuer', 7)
        self.assertEqual(inspect_claim(rewritten, fake, self.claim).status, 'REFERENCE_MISMATCH')

    def test_identical_reference_does_not_establish_authentication(self):
        r = inspect_claim(self.records, self.claim, self.claim)
        self.assertEqual(r.status, 'REFERENCE_MATCH_NOT_AUTHENTICATED')
        self.assertFalse(r.issuer_authenticated or r.authoritative)

    def test_replayed_generation_rejected_by_reference(self):
        old = ClaimedAnchor(self.claim.anchor, 'issuer', 6)
        self.assertEqual(inspect_claim(self.records, old, self.claim).status, 'REFERENCE_MISMATCH')

    def test_issuer_spoofing_rejected_by_reference(self):
        forged = ClaimedAnchor(self.claim.anchor, 'spoof', 7)
        self.assertEqual(inspect_claim(self.records, forged, self.claim).status, 'REFERENCE_MISMATCH')

    def test_boolean_generation_rejected(self):
        forged = ClaimedAnchor(self.claim.anchor, 'issuer', True)
        self.assertEqual(inspect_claim(self.records, forged).status, 'INVALID_GENERATION')

    def test_incomplete_chain_cannot_match_anchor(self):
        self.assertEqual(inspect_claim(self.records[:2], self.claim).status, 'ROLLBACK_OR_INCOMPLETE')

    def test_requirements_and_no_promotion(self):
        self.assertGreaterEqual(len(requirements_for_authenticated_anchor()), 6)
        self.assertFalse(safe_to_promote(self.records, self.claim, self.claim))


if __name__ == '__main__':
    unittest.main()
