"""Fail-closed checks exercised in a real optimized Python subprocess."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRELUDE = '''
import copy, hashlib, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from tools import f3_int116_run_audit as audit
if __debug__:
    raise RuntimeError('Optimization was not enabled')
def rejected(call):
    try:
        call()
    except (audit.AuditError, OSError, KeyError, TypeError, ValueError):
        return
    raise RuntimeError('Unsafe input was accepted under -O')
def valid_run():
    return dict(exit_code=0, exception=None, timed_out=False,
        cleanup=dict(confirmed=True, active_processes=0, live_io_threads=[]))
def valid_counts():
    return dict(total=17, failures=0, errors=0, skipped=0)
'''


class PortableRunnerTests(unittest.TestCase):
    def optimized(self, code):
        result = subprocess.run([sys.executable, '-O', '-B', '-c', PRELUDE + textwrap.dedent(code), str(ROOT)],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_checks_survive_optimization(self):
        self.optimized('''
            rejected(lambda: audit.require(False, 'closed'))
            audit.require(True, 'valid')
        ''')

    def test_checkpoint_and_seven_flags_fail_closed_under_optimization(self):
        self.optimized('''
            with tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                (base/'audit').mkdir()
                (base/'evidence').write_bytes(b'local')
                item = dict(evidence_file='evidence', evidence_sha256=audit.sha(base/'evidence'))
                good = dict(stage='F3-INT-115', checkpoint_type='FINAL', f3='OPEN', offline=True,
                    simulation_only=True, certification=False, locks=dict.fromkeys(audit.LOCKS, False),
                    windows_specific_tests=item, windows_full_regression=item)
                def write(value):
                    raw = json.dumps(value).encode()
                    for name in ('ULTIMO_MARCO.json','CHECKPOINT_F3_INT115_FINAL.json'):
                        (base/'audit'/name).write_bytes(raw)
                write(good)
                audit.validate_checkpoint(base)
                for key, value in [('stage','F3-INT-116'),('checkpoint_type','CANDIDATE'),('f3','FINAL'),
                    ('offline',False),('simulation_only',False),('certification',True)]:
                    bad = copy.deepcopy(good); bad[key] = value; write(bad)
                    rejected(lambda: audit.validate_checkpoint(base))
                for flag in audit.LOCKS:
                    bad = copy.deepcopy(good); bad['locks'][flag] = True; write(bad)
                    rejected(lambda: audit.validate_checkpoint(base))
                bad = copy.deepcopy(good); bad['locks'].pop(next(iter(audit.LOCKS))); write(bad)
                rejected(lambda: audit.validate_checkpoint(base))
                write(good)
                (base/'audit/CHECKPOINT_F3_INT115_FINAL.json').write_bytes(b'changed')
                rejected(lambda: audit.validate_checkpoint(base))
                write(good); (base/'evidence').write_bytes(b'tampered')
                rejected(lambda: audit.validate_checkpoint(base))
        ''')

    def test_failed_exit_exception_and_timeout_under_optimization(self):
        self.optimized('''
            audit.validate_run(valid_run(), valid_counts(), 'ESPECIFICOS')
            for key, value in [('exit_code',1),('exception','failure'),('timed_out',True)]:
                bad=valid_run(); bad[key]=value
                rejected(lambda: audit.validate_run(bad,valid_counts(),'ESPECIFICOS'))
        ''')

    def test_cleanup_failures_under_optimization(self):
        self.optimized('''
            for cleanup in [None, {}, dict(confirmed=False,active_processes=0,live_io_threads=[]),
                dict(confirmed=True,active_processes=1,live_io_threads=[]),
                dict(confirmed=True,active_processes=0,live_io_threads=['orphan'])]:
                bad=valid_run(); bad['cleanup']=cleanup
                rejected(lambda: audit.validate_run(bad,valid_counts(),'ESPECIFICOS'))
        ''')

    def test_missing_failed_and_skipped_tests_under_optimization(self):
        self.optimized('''
            for key,value in [('total',None),('total',0),('total',8),('failures',1),('errors',1),('skipped',1)]:
                bad=valid_counts(); bad[key]=value
                rejected(lambda: audit.validate_run(valid_run(),bad,'ESPECIFICOS'))
        ''')

    def test_inventory_tampering_and_path_escape_under_optimization(self):
        self.optimized('''
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory); (root/'file').write_bytes(b'good')
                pins={'file':audit.sha(root/'file')}; audit.verify(pins,root)
                (root/'file').write_bytes(b'bad'); rejected(lambda:audit.verify(pins,root))
                (root/'file').unlink(); rejected(lambda:audit.verify(pins,root))
                rejected(lambda:audit.verify({},root))
                for name in ['../outside',str(root/'absolute'),'.']:
                    rejected(lambda:audit.relative_path(root,name))
        ''')

    def test_missing_base_and_existing_output_leave_history_untouched(self):
        self.optimized('''
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory); audit.PROJECT=root; audit.ROOT=root/'audit'; audit.ROOT.mkdir()
                rejected(lambda:audit.main([]))
                (root/'base_f3_int115_final').mkdir()
                out=audit.ROOT/'EVIDENCIAS_F3_INT116_CORRECAO'; out.mkdir()
                marker=out/'history'; marker.write_bytes(b'preserve')
                rejected(lambda:audit.main([]))
                if marker.read_bytes()!=b'preserve':raise RuntimeError('History changed')
        ''')

    def test_moved_runner_resolves_project_independently_of_cwd(self):
        with tempfile.TemporaryDirectory(prefix='f3 relocated ') as directory:
            moved=Path(directory)/'different project'
            shutil.copytree(ROOT/'tools',moved/'audit/tools')
            code = '''
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from tools import f3_int116_run_audit as audit
if __debug__ or audit.PROJECT != Path(sys.argv[2]):raise RuntimeError('Wrong relocated root')
if audit.relative_path(audit.PROJECT,'base_f3_int115_final') != Path(sys.argv[2])/'base_f3_int115_final':raise RuntimeError('Wrong relative base')
try:audit.main([])
except audit.AuditError as error:
    if 'base directory missing' not in str(error):raise
else:raise RuntimeError('Missing relocated base was accepted')
'''
            result=subprocess.run([sys.executable,'-O','-B','-c',code,str(moved/'audit'),str(moved)],
                cwd=directory,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_main_records_failure_and_never_runs_regression_after_rejection(self):
        self.optimized('''
            from unittest.mock import patch
            with tempfile.TemporaryDirectory() as directory:
                project=Path(directory); base=project/'base_f3_int115_final'; (base/'audit').mkdir(parents=True)
                (base/'evidence').write_bytes(b'local')
                item=dict(evidence_file='evidence',evidence_sha256=audit.sha(base/'evidence'))
                checkpoint=dict(stage='F3-INT-115',checkpoint_type='FINAL',f3='OPEN',offline=True,
                    simulation_only=True,certification=False,locks=dict.fromkeys(audit.LOCKS,False),
                    windows_specific_tests=item,windows_full_regression=item)
                for name in ('ULTIMO_MARCO.json','CHECKPOINT_F3_INT115_FINAL.json'):
                    (base/'audit'/name).write_text(json.dumps(checkpoint))
                (base/'audit/MANIFESTO_F3_INT115_FINAL.json').write_text(json.dumps(dict(files_sha256={'evidence':audit.sha(base/'evidence')})))
                import shutil
                for path in base.rglob('*'):
                    if path.is_file():
                        target=project/path.relative_to(base); target.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copy2(path,target)
                audit.PROJECT=project; audit.ROOT=project/'audit'
                for case in ('exit','cleanup','summary','sources'):
                    calls=[]
                    def fake(command,*,cwd,log,timeout):
                        calls.append(command)
                        log.write_text('Ran 17 tests in 0.001s\\n\\nOK\\n' if case!='summary' else 'incomplete')
                        result=valid_run()
                        if case=='exit':result['exit_code']=1
                        if case=='cleanup':result['cleanup']['confirmed']=False
                        return result
                    inventories=[{'code':'same'},{'code':'changed' if case=='sources' else 'same'}]
                    with patch.object(audit,'run_supervised',fake), patch.object(audit,'source_inventory',side_effect=inventories):
                        rejected(lambda:audit.main(['--output','run_'+case]))
                    evidence=json.loads((audit.ROOT/('run_'+case)/'RESULTADO.json').read_bytes())
                    if evidence['success'] or not evidence['exception'] or len(calls)!=1:
                        raise RuntimeError('Failure was approved or regression continued')
        ''')


if __name__=='__main__':unittest.main()
