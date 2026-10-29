"""Optimized subprocess checks and explicit dependency injection, no patching."""
import json
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest
ROOT = Path(__file__).resolve().parents[1]
PRELUDE = '''
import copy, importlib.util, json, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from tools import f3_int117_run_audit as audit
from tools import f3_int117_sqlite_write_faults as probe
if __debug__:raise RuntimeError('Expected -O')
def rejected(call):
    try:call()
    except (audit.AuditError, probe.ProbeError, OSError, KeyError, TypeError, ValueError):return
    raise RuntimeError('Unsafe input was accepted')
def good_result():
    return dict(exit_code=0, exception=None, timed_out=False,
        cleanup=dict(confirmed=True,active_processes=0,live_io_threads=[]))
def good_counts():
    return dict(total=len(audit.EXPECTED_IDS),passed=len(audit.EXPECTED_IDS),failures=0,errors=0,skipped=0)
def good_text():
    return '\\n'.join(n.rsplit('.',1)[1]+' ('+n+') ... ok' for n in sorted(audit.EXPECTED_IDS))
def load_moved(root):
    shutil.copytree(Path(sys.argv[1])/'tools',root/'audit/tools')
    spec=importlib.util.spec_from_file_location('moved_audit',root/'audit/tools/f3_int117_run_audit.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
'''


class RunnerTests(unittest.TestCase):
    def optimized(self, code, timeout=90):
        result = subprocess.run([sys.executable, '-O', '-B', '-c', PRELUDE + textwrap.dedent(code), str(ROOT)],
            cwd=ROOT.parent, capture_output=True, text=True, timeout=timeout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_checks_survive_optimization(self):
        self.optimized('''
            rejected(lambda:audit.require(False,'closed'))
            rejected(lambda:probe.require(False,'closed'))
            rejected(lambda:probe.validate_attempt('full',dict(events=['connection_closed'],error=None,committed=True)))
            audit.require(True,'positive')
        ''')

    def test_native_faults_under_optimization(self):
        self.optimized('''
            sys.path.insert(0,str(Path(sys.argv[1])/'tests'))
            import test_f3_int109_offline_consumption_store as prior
            prior.ConsumptionStoreTests.setUpClass();source=prior.ConsumptionStoreTests
            for mode,code in [('full',13),('readonly',8)]:
                result=probe.run_experiment(mode,segments=source.segments,previous_batches=source.batches,
                    batches=source.next_batches,scope=source.scope)
                if result['attempt']['error']['primary_code']!=code or not result['fixture_removed']:
                    raise RuntimeError('Optimized native fault experiment failed')
                if result['automatic_retries']!=0 or result['retry_allowed']:
                    raise RuntimeError('Retry authority leaked')
        ''', timeout=240)

    def test_execution_and_cleanup_fail_closed(self):
        self.optimized('''
            audit.validate_run(good_result(),good_counts(),'ESPECIFICOS',good_text())
            for key,value in [('exit_code',1),('exception','failed'),('timed_out',True)]:
                bad=good_result();bad[key]=value
                rejected(lambda:audit.validate_run(bad,good_counts(),'ESPECIFICOS',good_text()))
            for cleanup in [None,{},dict(confirmed=False,active_processes=0,live_io_threads=[]),
                dict(confirmed=True,active_processes=1,live_io_threads=[]),
                dict(confirmed=True,active_processes=0,live_io_threads=['orphan'])]:
                bad=good_result();bad['cleanup']=cleanup
                rejected(lambda:audit.validate_run(bad,good_counts(),'ESPECIFICOS',good_text()))
        ''')

    def test_missing_test_ids_and_invalid_summaries_rejected(self):
        self.optimized('''
            for key,value in [('total',0),('total',None),('passed',0),('failures',1),('errors',1),('skipped',1)]:
                bad=good_counts();bad[key]=value
                rejected(lambda:audit.validate_run(good_result(),bad,'ESPECIFICOS',good_text()))
            for text in ['',good_text().split('\\n',1)[1],good_text()+'\\n'+good_text()]:
                rejected(lambda:audit.validate_run(good_result(),good_counts(),'ESPECIFICOS',text))
        ''')

    def test_path_escape_and_inventory_tamper_rejected(self):
        self.optimized('''
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);p=root/'source';p.write_bytes(b'good')
                pins={'source':audit.sha(p)};audit.verify(pins,root)
                p.write_bytes(b'changed');rejected(lambda:audit.verify(pins,root))
                p.unlink();rejected(lambda:audit.verify(pins,root))
                rejected(lambda:audit.verify({},root))
                for name in ['../outside',str(root/'absolute'),'.']:
                    rejected(lambda:audit.relative_path(root,name))
        ''')

    def test_checkpoint_safety_rejected_under_optimization(self):
        self.optimized('''
            good=dict(stage='F3-INT-116',checkpoint_type='FINAL',f3='OPEN',offline=True,
                simulation_only=True,certification=False,real_operations_authorized=False,
                locks=dict.fromkeys(audit.LOCKS,False))
            audit.validate_checkpoint(good)
            for key,value in [('stage','F3-INT-117'),('checkpoint_type','CANDIDATE'),('f3','FINAL'),
                ('offline',False),('simulation_only',False),('certification',True),('real_operations_authorized',True)]:
                bad=copy.deepcopy(good);bad[key]=value
                rejected(lambda:audit.validate_checkpoint(bad))
            for flag in audit.LOCKS:
                bad=copy.deepcopy(good);bad['locks'][flag]=True
                rejected(lambda:audit.validate_checkpoint(bad))
        ''')

    def test_relocated_runner_is_cwd_independent(self):
        self.optimized('''
            with tempfile.TemporaryDirectory(prefix='f117 moved ') as directory:
                root=Path(directory)/'project with spaces';module=load_moved(root)
                if module.PROJECT!=root or module.ROOT!=root/'audit':raise RuntimeError('Wrong relocated root')
                if module.relative_path(module.PROJECT,'b116')!=root/'b116':raise RuntimeError('Wrong relative base')
                try:module.main([])
                except module.AuditError as error:
                    if 'FINAL base missing' not in str(error):raise
                else:raise RuntimeError('Missing relocated base was accepted')
        ''')

    def test_existing_output_is_preserved(self):
        self.optimized('''
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'project';module=load_moved(root);(root/'b116').mkdir()
                out=root/'audit/EVIDENCIAS_F3_INT117_CORRECAO';out.mkdir();marker=out/'history';marker.write_bytes(b'preserve')
                try:module.main([])
                except module.AuditError as error:
                    if 'Historical output already exists' not in str(error):raise
                else:raise RuntimeError('Existing output was accepted')
                if marker.read_bytes()!=b'preserve':raise RuntimeError('History changed')
        ''')

    def test_main_stops_after_failure_without_regression(self):
        self.optimized('''
            for case in ('exit','cleanup','summary','source'):
                with tempfile.TemporaryDirectory() as directory:
                    project=Path(directory);root=project/'audit';root.mkdir();base=project/'b116';(base/'audit').mkdir(parents=True)
                    mf=base/'audit/MANIFESTO_F3_INT116_FINAL.json';mf.write_bytes(b'fixture')
                    source=root/'source.py';source.write_bytes(b'# unchanged')
                    baseline={'audit/MANIFESTO_F3_INT116_FINAL.json':audit.sha(mf)}
                    calls=[]
                    def supervisor(command,*,cwd,log,timeout):
                        calls.append(command)
                        log.write_text(good_text()+f'\\nRan {len(audit.EXPECTED_IDS)} tests in 0.001s\\n\\nOK\\n' if case!='summary' else 'incomplete')
                        result=good_result()
                        if case=='exit':result['exit_code']=1
                        if case=='cleanup':result['cleanup']['active_processes']=1
                        if case=='source':source.write_bytes(b'# tampered')
                        return result
                    out=root/'evidence'
                    rejected(lambda:audit.execute(out,base,baseline,root=root,project=project,supervisor=supervisor))
                    evidence=json.loads((out/'RESULTADO.json').read_bytes())
                    if evidence['success'] or not evidence['exception'] or len(calls)!=1:
                        raise RuntimeError('Failure approved or regression continued')
        ''')


if __name__ == '__main__':
    unittest.main()
