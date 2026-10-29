import unittest
from tools.f3_int41_worker_handoff_simulator import Transfer as T, assess_transfers, safe_to_promote

class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.a=T('ACQUIRE','a',1,0,'t1'); self.release=T('RELEASE','a',1,1,'r1')
        self.b=T('ACQUIRE','b',2,1,'t2'); self.write=T('WRITE','b',2,2,'w2')
    def check(self, status, events, **kw):
        r=assess_transfers(events,**kw)
        self.assertEqual(r.status,status)
        self.assertFalse(r.authenticated or r.authoritative or r.closure_authorized)
        self.assertFalse(safe_to_promote(r))
        return r
    def test_valid_simulated_handoff(self):
        self.assertTrue(self.check('FIXTURE_HANDOFF_CONSISTENT_NOT_AUTHENTICATED',[self.a,self.release,self.b,self.write],expected_worker='b',expected_generation=2).fixture_consistent)
    def test_no_release_fails_closed(self): self.check('UNFENCED_HANDOFF',[self.a,self.b])
    def test_old_worker_fenced(self): self.check('FENCED_OR_STALE_WRITE',[self.a,self.release,self.b,T('WRITE','a',1,2,'late')])
    def test_generation_skip(self): self.check('INVALID_GENERATION_ADVANCE',[self.a,self.release,T('ACQUIRE','b',3,1,'t3')])
    def test_replayed_token(self): self.check('REPLAYED_TRANSFER_TOKEN',[self.a,self.release,T('ACQUIRE','b',2,1,'t1')])
    def test_duplicate_release(self): self.check('STALE_OR_DUPLICATE_RELEASE',[self.a,self.release,self.release])
    def test_wrong_parent(self): self.check('CAUSAL_PARENT_MISMATCH',[self.a,self.release,T('ACQUIRE','b',2,0,'t2')])
    def test_writer_conflict(self): self.check('WRITER_MISMATCH',[self.a],expected_worker='b')
    def test_stale_expected_generation(self): self.check('GENERATION_MISMATCH',[self.a],expected_generation=2)
    def test_release_without_successor(self): self.check('NO_ACTIVE_WRITER',[self.a,self.release])
    def test_write_after_release(self): self.check('FENCED_OR_STALE_WRITE',[self.a,self.release,T('WRITE','a',1,1,'w')])
    def test_empty_history(self): self.check('MISSING_TRANSFER_HISTORY',[])
    def test_invalid_event(self): self.check('INVALID_EVENTS',[T('ACQUIRE','a',True,0,'t')])
    def test_write_before_acquire(self): self.check('FENCED_OR_STALE_WRITE',[T('WRITE','a',1,0,'w')])

if __name__ == '__main__': unittest.main()
