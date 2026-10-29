import unittest
from tools.f3_int114_custody_recovery import (assess_custody, assess_commit_recovery,
    assess_durability, LOCKS, safe_to_promote)

D = 'a' * 64
E = 'b' * 64
C = dict(retained_digest=D, observed_digest=D, custody_state='ACTIVE',
         generation=4, expected_generation=4)
R = dict(ack_state='RECEIVED', store_state='COMMITTED', retained_pin_state='MATCH',
         stable_snapshot=True)

class CustodyRecoveryTests(unittest.TestCase):
    def test_match_unauthenticated(self):
        self.assertEqual(assess_custody(**C).status, 'UNAUTHENTICATED_MATCH')
    def test_self_claim_does_not_authenticate(self):
        self.assertEqual(assess_custody(**C, independent_proof={'self_attested': True}).status,
                         'UNVERIFIED_PROVENANCE')
    def test_revocation(self):
        self.assertEqual(assess_custody(**(C | {'custody_state': 'REVOKED'})).status,
                         'CUSTODY_UNAVAILABLE')
    def test_missing_and_recovery(self):
        for state in ('MISSING','RECOVERY_PENDING'):
            self.assertEqual(assess_custody(**(C | {'custody_state': state})).status,
                             'CUSTODY_UNAVAILABLE')
    def test_digest_mismatch(self):
        self.assertEqual(assess_custody(**(C | {'observed_digest': E})).status,
                         'REFERENCE_MISMATCH')
    def test_invalid_digest(self):
        self.assertEqual(assess_custody(**(C | {'observed_digest': 'bad'})).status,
                         'INVALID_DIGEST')
    def test_stale_generation(self):
        self.assertEqual(assess_custody(**(C | {'generation': 3})).status,
                         'STALE_REFERENCE')
    def test_bool_generation_rejected(self):
        self.assertEqual(assess_custody(**(C | {'generation': True})).status,
                         'INVALID_GENERATION')
    def test_lost_ack(self):
        self.assertEqual(assess_commit_recovery(**(R | {'ack_state':'LOST'})).status,
                         'ACK_UNRESOLVED')
    def test_lost_ack_not_committed_still_no_retry(self):
        self.assertEqual(assess_commit_recovery(**(R | {'ack_state':'LOST',
                         'store_state':'NOT_COMMITTED'})).status, 'ACK_UNRESOLVED')
    def test_pin_retention_failure(self):
        for pin in ('MISSING','STALE','REVOKED','UNKNOWN'):
            self.assertEqual(assess_commit_recovery(**(R | {'retained_pin_state':pin})).status,
                             'PIN_UNRESOLVED')
    def test_competing_writer(self):
        self.assertEqual(assess_commit_recovery(**(R | {'competing_writer':True})).status,
                         'CONCURRENT_OR_TOCTOU_UNRESOLVED')
    def test_snapshot_gap(self):
        self.assertEqual(assess_commit_recovery(**(R | {'stable_snapshot':False})).status,
                         'CONCURRENT_OR_TOCTOU_UNRESOLVED')
    def test_commit_observed_not_authorized(self):
        self.assertEqual(assess_commit_recovery(**R).status,
                         'COMMIT_OBSERVED_UNAUTHENTICATED')
    def test_unavailable_store(self):
        self.assertEqual(assess_commit_recovery(**(R | {'store_state':'UNAVAILABLE'})).status,
                         'STORE_UNRESOLVED')
    def test_physical_failure_distinction(self):
        for event in ('OS_SHUTDOWN','POWER_LOSS','MEDIA_LOSS'):
            self.assertEqual(assess_durability(event=event).status,
                             'PHYSICAL_DURABILITY_UNPROVEN')
    def test_process_crash_not_durability(self):
        self.assertEqual(assess_durability(event='PROCESS_CRASH').status,
                         'PROCESS_RECOVERY_UNATTESTED')
    def test_all_locks_false(self):
        outputs = [assess_custody(**C), assess_commit_recovery(**R),
                   assess_durability(event='MEDIA_LOSS')]
        for result in outputs:
            self.assertTrue(all(getattr(result, lock) is False for lock in LOCKS))
        self.assertFalse(safe_to_promote())
