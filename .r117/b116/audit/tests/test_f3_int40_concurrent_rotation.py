import unittest
from tools.f3_int34_persistence_simulator import Authority
from tools.f3_int36_anchor_rollback_simulator import Anchor
from tools.f3_int37_coordinated_attack_simulator import ClaimedAnchor
from tools.f3_int38_credential_lifecycle_simulator import CredentialFixture
from tools.f3_int39_key_rotation_simulator import RotationEvent as E
from tools.f3_int40_concurrent_rotation_simulator import AuthorityEvent as A, assess_concurrent_rotation, safe_to_promote

class ConcurrentRotationTests(unittest.TestCase):
    def setUp(self):
        a=Authority(); lease=a.lease('w')
        for event in ('FENCE','JOB_EMPTY','CLEANUP'): a.append('w',lease,event)
        self.records=a.snapshot()
        self.claim=ClaimedAnchor(Anchor(3,self.records[-1].checksum),'issuer',7)
        self.credential=CredentialFixture('issuer','new',7,100,300)
        self.base=(A('writer','','e1',E('ACTIVATE','old',100,1)),
                   A('writer','e1','e2',E('ACTIVATE','new',150,2)))
    def check(self,status,events=None):
        result=assess_concurrent_rotation(self.records,self.claim,self.credential,
                                           self.base if events is None else events,175)
        self.assertEqual(result.status,status)
        self.assertFalse(result.authenticated or result.authoritative or result.closure_authorized)
        self.assertFalse(safe_to_promote())
        return result
    def test_single_writer_chain_fixture_only(self):
        self.assertTrue(self.check('FIXTURE_ROTATION_ELIGIBLE_NOT_AUTHENTICATED').fixture_eligible)
    def test_concurrent_revocation_and_activation_fork(self):
        self.check('DIVERGENT_AUTHORITY_HISTORY',self.base+(A('writer','e1','e3',E('REVOKE','new',151,3)),))
    def test_two_authorities_same_parent_fork(self):
        self.check('DIVERGENT_AUTHORITY_HISTORY',self.base+(A('other','e1','e3',E('COMPROMISE','new',151,3)),))
    def test_unproven_handoff(self):
        self.check('UNPROVEN_AUTHORITY_HANDOFF',(self.base[0],A('other','e1','e2',E('ACTIVATE','new',150,2))))
    def test_missing_parent(self):
        self.check('MISSING_CAUSAL_PARENT',(self.base[0],A('writer','absent','e2',E('ACTIVATE','new',150,2))))
    def test_duplicate_id(self):
        self.check('DUPLICATE_EVENT_ID',(self.base[0],A('writer','e1','e1',E('ACTIVATE','new',150,2))))
    def test_revoked_after_rotation(self):
        self.check('KEY_RETIRED',self.base+(A('writer','e2','e3',E('REVOKE','new',160,3)),))
    def test_compromised_after_rotation(self):
        self.check('KEY_RETIRED',self.base+(A('writer','e2','e3',E('COMPROMISE','new',160,3)),))
    def test_out_of_order_sequence(self):
        self.check('DUPLICATE_SEQUENCE',(self.base[0],A('writer','e1','e2',E('ACTIVATE','new',150,1))))
    def test_causal_order_independent_of_delivery_order(self):
        self.assertTrue(self.check('FIXTURE_ROTATION_ELIGIBLE_NOT_AUTHENTICATED',tuple(reversed(self.base))).fixture_eligible)
    def test_empty_history_not_authorized(self):
        self.check('DIVERGENT_AUTHORITY_HISTORY',())
    def test_two_disconnected_roots(self):
        self.check('DIVERGENT_AUTHORITY_HISTORY',(self.base[0],A('writer','','e3',E('ACTIVATE','new',150,2))))

if __name__=='__main__': unittest.main()
