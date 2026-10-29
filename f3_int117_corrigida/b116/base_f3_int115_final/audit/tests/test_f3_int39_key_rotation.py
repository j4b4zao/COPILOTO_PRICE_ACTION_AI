import unittest
from dataclasses import replace
from tools.f3_int34_persistence_simulator import Authority
from tools.f3_int36_anchor_rollback_simulator import Anchor
from tools.f3_int37_coordinated_attack_simulator import ClaimedAnchor
from tools.f3_int38_credential_lifecycle_simulator import CredentialFixture
from tools.f3_int39_key_rotation_simulator import RotationEvent as E, assess_rotation, safe_to_promote


class RotationTests(unittest.TestCase):
    def setUp(self):
        a = Authority(); epoch = a.lease('worker')
        for event in ('FENCE', 'JOB_EMPTY', 'CLEANUP'):
            a.append('worker', epoch, event)
        self.records = a.snapshot()
        self.claim = ClaimedAnchor(Anchor(3, self.records[-1].checksum), 'issuer', 7)
        self.old = CredentialFixture('issuer', 'old', 7, 100, 300)
        self.new = replace(self.old, key_id='new')
        self.events = (E('ACTIVATE', 'old', 100, 1), E('ACTIVATE', 'new', 150, 2))

    def check(self, expected, credential=None, events=None, observed_at=175, **kw):
        r = assess_rotation(self.records, self.claim, credential or self.new,
                            self.events if events is None else events, observed_at, **kw)
        self.assertEqual(r.status, expected)
        self.assertFalse(r.authenticated or r.authoritative or r.closure_authorized)
        return r

    def test_new_key_fixture_eligible_not_authenticated(self):
        self.assertTrue(self.check('FIXTURE_ROTATION_ELIGIBLE_NOT_AUTHENTICATED').fixture_eligible)
        self.assertFalse(safe_to_promote())

    def test_old_key_retired_on_rotation(self):
        self.check('KEY_RETIRED', self.old)

    def test_revocation_during_rotation(self):
        self.check('KEY_RETIRED', events=self.events + (E('REVOKE', 'new', 160, 3),))

    def test_compromise_during_rotation(self):
        self.check('KEY_RETIRED', events=self.events + (E('COMPROMISE', 'new', 160, 3),))

    def test_out_of_order_timestamp(self):
        self.check('OUT_OF_ORDER', events=(E('ACTIVATE', 'old', 150, 1), E('ACTIVATE', 'new', 120, 2)))

    def test_out_of_order_sequence(self):
        self.check('OUT_OF_ORDER', events=tuple(reversed(self.events)))

    def test_duplicate_sequence(self):
        self.check('DUPLICATE_SEQUENCE', events=(E('ACTIVATE', 'old', 100, 1), E('ACTIVATE', 'new', 150, 1)))

    def test_future_evidence(self):
        self.check('FUTURE_EVENT', observed_at=140)

    def test_reactivation_of_retired_key(self):
        self.check('REACTIVATION_FORBIDDEN', self.old, events=self.events + (E('ACTIVATE', 'old', 160, 3),))

    def test_generation_floor(self):
        self.check('BASE_ROLLBACK_GENERATION', min_generation=8)

    def test_missing_activation(self):
        self.check('KEY_NOT_ACTIVE', events=())

    def test_expired_credential(self):
        self.check('BASE_EXPIRED', credential=replace(self.new, expires_at=170))


if __name__ == '__main__':
    unittest.main()
