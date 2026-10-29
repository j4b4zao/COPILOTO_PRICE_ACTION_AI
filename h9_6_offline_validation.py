"""Offline tests/audit runner. Never constructs ComWorker or ExistingExcel."""
import hashlib
import io
import json
import unittest
from pathlib import Path
from h9_6_observational_monitor import Config, Journal, dependency, monitor
from test_h9_6_observational_monitor import Clock, Fake, evidence

ROOT=Path(__file__).resolve().parent
TARGET=Path('C:/COPILOTO_GIT_SYNC')

class OfflineJournal(Journal):
    def emit(self,event): super().emit(dict(event,mode='OFFLINE_HISTORICAL_REPLAY_SYNTHETIC_CLOCK'))
    def finish(self,summary): super().finish(dict(summary,mode='OFFLINE_HISTORICAL_REPLAY_SYNTHETIC_CLOCK'))

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

if __name__=='__main__':
    import sys
    # Read test modules from the delivery tree without altering any of them.
    sys.path.insert(0,str(TARGET))
    import test_h9_5_readonly, test_h9_5_1_readonly, test_h9_6_observational_monitor
    suites=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in (test_h9_5_readonly,test_h9_5_1_readonly,test_h9_6_observational_monitor))
    stream=io.StringIO(); result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suites)
    with (ROOT/'h9_6_offline_tests.txt').open('x',encoding='utf-8') as f: f.write(stream.getvalue())
    if not result.wasSuccessful(): raise SystemExit('OFFLINE_TESTS_FAILED')
    clock=Clock(); client=Fake(evidence(),clock); journal=OfflineJournal(ROOT/'h9_6_offline_audit')
    summary=monitor(client,journal,Config(duration=12,interval=5),clock,clock.sleep)
    before=json.loads((ROOT/'h9_6_before.json').read_text(encoding='utf-8'))
    changed=[]; inaccessible=[]
    for path,expected in before.items():
        try:
            if sha(path)!=expected: changed.append(path)
        except OSError: inaccessible.append(path)
    validation={'result':'H9_6_OFFLINE_TESTS_PASSED' if not changed and not inaccessible else 'BLOCKED_WITH_REASONS',
                'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                'preexisting_files_checked':len(before),'changed':changed,'inaccessible':inaccessible,
                'live_monitor_started':False,'orders_allowed':False,'live_certified':False,
                'historical_evidence_hashes':{str(TARGET/f'h9_5_real_evidence_{n}.json'):sha(TARGET/f'h9_5_real_evidence_{n}.json') for n in ('03','05')},
                'h9_5_2_reference':'NOT_FOUND_BY_FILENAME; no claimed audit of H.9.5.2',
                'offline_replay_samples':summary['samples']}
    with (ROOT/'h9_6_offline_validation.json').open('x',encoding='utf-8') as f: json.dump(validation,f,ensure_ascii=False,indent=2)
    print(json.dumps(validation,ensure_ascii=False,indent=2))
    paths=[ROOT/name for name in ('h9_6_observational_monitor.py','test_h9_6_observational_monitor.py','h9_6_offline_validation.py','h9_6_before.json','h9_6_offline_tests.txt','h9_6_offline_validation.json')]
    paths+=list((ROOT/'h9_6_offline_audit').glob('*'))
    for path in paths: print(path.relative_to(ROOT),sha(path))
