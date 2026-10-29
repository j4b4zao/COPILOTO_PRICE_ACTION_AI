import unittest
from dataclasses import replace
from tools.f3_int34_persistence_simulator import Authority
from tools.f3_int36_anchor_rollback_simulator import Anchor
from tools.f3_int37_coordinated_attack_simulator import ClaimedAnchor
from tools.f3_int38_credential_lifecycle_simulator import CredentialFixture, assess_credential, safe_to_promote


class CredentialLifecycleTests(unittest.TestCase):
    def setUp(self):
        authority = Authority()
        epoch = authority.lease('worker')
        for event in ('FENCE', 'JOB_EMPTY', 'CLEANUP'):
            authority.append('worker', epoch, event)
        self.records = authority.snapshot()
        self.claim = ClaimedAnchor(Anchor(3, self.records[-1].checksum), 'issuer', 7)
        self.credential = CredentialFixture('issuer', 'key-1', 7, 100, 200)

    def check(self, expected, **changes):
        result = assess_credential(self.records, self.claim, replace(self.credential, **changes), 150)
        self.assertEqual(result.status, expected)
        self.assertFalse(result.authenticated or result.authoritative or result.closure_authorized)

    def test_valid_fixture_still_not_authenticated(self):
        self.check('FIXTURE_ELIGIBLE_NOT_AUTHENTICATED')
        self.assertFalse(safe_to_promote(self.records, self.claim))

    def test_expired_boundary(self):
        self.assertEqual(assess_credential(self.records, self.claim, self.credential, 200).status, 'EXPIRED')

    def test_revoked_credential(self):
        self.check('REVOKED', revoked_at=125)

    def test_compromised_credential(self):
        self.check('COMPROMISED', compromised_at=120)

    def test_not_yet_valid(self):
        self.assertEqual(assess_credential(self.records, self.claim, self.credential, 99).status, 'NOT_YET_VALID')

    def test_generation_rollback(self):
        self.assertEqual(assess_credential(self.records, self.claim, self.credential, 150, min_generation=8).status, 'ROLLBACK_GENERATION')

    def test_identity_mismatch(self):
        self.check('IDENTITY_OR_GENERATION_MISMATCH', issuer='spoof')

    def test_corrupted_or_invalid_credential(self):
        self.check('INVALID_CREDENTIAL', expires_at=100)
        self.check('INVALID_CREDENTIAL', generation=True)

    def test_untrusted_reference_even_when_equal(self):
        result = assess_credential(self.records, self.claim, self.credential, 150, trusted_reference=self.claim)
        self.assertEqual(result.status, 'FIXTURE_ELIGIBLE_NOT_AUTHENTICATED')
        self.assertFalse(result.authenticated)

    def test_coordinated_rewrite_fails_reference(self):
        from tools.f3_int37_coordinated_attack_simulator import coordinated_rewrite
        altered = coordinated_rewrite(self.records, ('FENCE', 'FAKE_JOB_EMPTY', 'CLEANUP'))
        fake = replace(self.claim, anchor=Anchor(3, altered[-1].checksum))
        r = assess_credential(altered, fake, self.credential, 150, trusted_reference=self.claim)
        self.assertEqual(r.status, 'JOURNAL_OR_CLAIM_REJECTED')
        self.assertFalse(r.closure_authorized)


if __name__ == '__main__':
    unittest.main()
