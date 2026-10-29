"""Identity-pinned tests for surviving and concurrently created descendants."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import time
from tools.f3_int115_process_control import Peer
from tools.f3_int115_process_identity import ProcessRef,identity_matches

ROOT=Path(__file__).resolve().parents[1]
STALL='import threading; threading.Event().wait(600)'


class ProcessIdentityTests(unittest.TestCase):
    def spawn_family(self,count=1):
        code=("import subprocess,sys,json,os; children=[subprocess.Popen([sys.executable,'-B','-c',"+
              repr(STALL)+"]) for _ in range("+str(count)+")]; "
              "print(json.dumps({'pids':[p.pid for p in children],'ppid':os.getpid()}),flush=True); sys.stdin.readline()")
        p=Peer([sys.executable,'-B','-c',code],cwd=ROOT,timeout=15)
        self.addCleanup(p.close)
        family=p.recv()
        refs=[ProcessRef(pid,p.job.handle) for pid in family['pids']]
        for ref in refs:self.addCleanup(ref.close)
        return p,family,refs

    def evidence(self,p,refs,label):
        rows=[dict(identity=r.identity,signalled=r.signalled()) for r in refs]
        print(json.dumps(dict(test=label,root_pid=p.pid,processes=rows,cleanup=p.cleanup)),flush=True)
        self.assertTrue(p.cleanup['confirmed'])
        self.assertEqual(p.cleanup['active_processes'],0)
        self.assertEqual(p.cleanup['live_io_threads'],[])
        self.assertTrue(all(r.signalled() for r in refs))
        self.assertTrue(all(r['exit_confirmed'] for r in p.cleanup['processes']))

    def test_descendants_survive_root_then_all_handles_signal(self):
        p,family,refs=self.spawn_family(3)
        self.assertTrue(all(not r.signalled() for r in refs))
        p.send('EXIT');self.assertEqual(p.wait(),0)
        self.assertTrue(all(not r.signalled() for r in refs))
        p.close()
        self.evidence(p,refs,self.id())

    def test_cleanup_while_descendants_are_being_created(self):
        # Build a real multiline program, avoiding a timing/sleep barrier.
        code="import subprocess,sys,json\nfor i in range(1000):\n p=subprocess.Popen([sys.executable,'-B','-c',"+repr(STALL)+"])\n print(json.dumps({'pid':p.pid}),flush=True)\n"
        p=Peer([sys.executable,'-B','-c',code],cwd=ROOT,timeout=15)
        self.addCleanup(p.close)
        first=p.recv()
        ref=ProcessRef(first['pid'],p.job.handle);self.addCleanup(ref.close)
        self.assertFalse(ref.signalled())
        p.close()
        self.evidence(p,[ref],self.id())

    def test_identity_divergence_does_not_prove_original_survival(self):
        ref=ProcessRef(os.getpid());self.addCleanup(ref.close)
        expected=dict(ref.identity,creation_100ns=ref.identity['creation_100ns']-1)
        self.assertEqual(expected['pid'],ref.identity['pid'])
        self.assertFalse(identity_matches(expected,ref.identity))
        self.assertFalse(ref.signalled())  # An active reused/different instance is not the expected one.
        self.assertTrue(identity_matches(ref.identity,dict(ref.identity)))

    def test_delayed_handle_confirmation_fails_closed(self):
        p,family,refs=self.spawn_family()
        from tools import f3_int115_process_identity as identities
        original=identities.ProcessRef.wait_until
        def no_confirmation(ref,deadline):
            raise TimeoutError('controlled missing exit confirmation')
        with patch.object(identities.ProcessRef,'wait_until',no_confirmation):
            with self.assertRaises(RuntimeError):p.close()
        self.assertFalse(p.cleanup['confirmed'])
        self.assertIn('controlled missing exit confirmation',p.cleanup['error'])
        for ref in refs:original(ref,time.monotonic()+5)
        # The intentional failure remains recorded; avoid registering a false
        # successful second cleanup on this already-closed peer.
        self._cleanups=[item for item in self._cleanups if item[0]!=p.close]

    def test_repeated_root_exit_identity_checks(self):
        for iteration in range(20):
            with self.subTest(iteration=iteration):
                p,family,refs=self.spawn_family()
                p.send('EXIT');self.assertEqual(p.wait(),0)
                self.assertFalse(refs[0].signalled())
                p.close()
                self.evidence(p,refs,self.id()+':'+str(iteration))


if __name__=='__main__':unittest.main()
