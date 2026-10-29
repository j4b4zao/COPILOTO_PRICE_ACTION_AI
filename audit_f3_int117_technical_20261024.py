"""Read-only candidate audit plus disposable adversarial fixtures; no promotion."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

WORK=Path(__file__).resolve().parent
PROJECT=WORK/'f3_int117_work'
ROOT=PROJECT/'audit'
OUT=WORK/'audit/AUDITORIA_F3_INT117_20261024'
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from tools import f3_int117_sqlite_write_faults as probe
from tools import f3_int109_offline_consumption_store as store
from tools.f3_int115_process_control import run_supervised
from tools.f3_int115_run_candidate import summarize
import test_f3_int109_offline_consumption_store as fixtures


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}
def mismatch(pins,root):return [n for n,d in pins.items() if not (root/n).is_file() or sha(root/n)!=d]
def require(ok,message):
    if not ok:raise RuntimeError(message)


def integrity():
    m=read(ROOT/'MANIFESTO_F3_INT117_CANDIDATA.json');e=ROOT/'EVIDENCIAS_F3_INT117'
    a=read(e/'ANTES.json');r=read(e/'RESULTADO.json');checks={};details={}
    def check(n,v):checks[n]=bool(v)
    check('manifest_7129',len(m['files_sha256'])==7129)
    check('manifest_all_pins',not mismatch(m['files_sha256'],PROJECT))
    check('manifest_sidecar',sha(ROOT/'MANIFESTO_F3_INT117_CANDIDATA.json')==(ROOT/'MANIFESTO_F3_INT117_CANDIDATA.json.sha256').read_text().split()[0])
    baseline=a['base_files_sha256']
    check('historical_count_3559',len(baseline)==3559)
    for label,location in [('original_final',WORK/'f3_int116_final'),('candidate',PROJECT),('relative_base',PROJECT/'b116'),('relocated_base',WORK/'.r117/b116')]:
        check(label+'_3559_hashes',not mismatch(baseline,location))
    src={n:d for n,d in inventory(ROOT).items() if n.endswith('.py')}
    check('all_229_sources_match_execution',len(src)==229 and src==a['sources_before']==r['sources_before'])
    check('relocated_229_sources_match',src=={n:d for n,d in inventory(WORK/'.r117/audit').items() if n.endswith('.py')})
    check('executed_sources_manifest_covered',all(m['files_sha256'].get('audit/'+n)==d for n,d in src.items()))
    check('optimized_candidate_success',a['optimized'] is True and r['optimized'] is True and r['success'] is True and r['exception'] is None)
    check('preexisting_execution_files_preserved',not mismatch(a['historical_before'],PROJECT))
    for n in ('tools/f3_int117_sqlite_write_faults.py','tools/f3_int117_run_audit.py',
              'tests/test_f3_int117_sqlite_write_faults.py','tests/test_f3_int117_runner.py'):
        details[n]=sha(ROOT/n)
    for n in ('tools/f3_int117_sqlite_write_faults.py','tools/f3_int117_run_audit.py'):
        tree=ast.parse((ROOT/n).read_text());check(n+'_no_assert',not any(isinstance(x,ast.Assert) for x in ast.walk(tree)))
        check(n+'_no_mock_import',not any(isinstance(x,ast.ImportFrom) and x.module=='unittest.mock' for x in ast.walk(tree)))
    check('two_runs',[v['label'] for v in r['runs']]==['ESPECIFICOS','REGRESSAO_COMPLETA'])
    report=(ROOT/'RELATORIO_F3_INT117_CANDIDATA.md').read_text(encoding='utf8')
    expected_ids=set(a['expected_test_ids'])
    for run,total,skip in zip(r['runs'],(21,1459),(0,1)):
        label=run['label'];x=read(e/(label+'.log.execution.json'));text=(e/(label+'.log')).read_text(encoding='utf8')
        check(label+'_execution_record',all(run.get(k)==v for k,v in x.items()))
        check(label+'_successful',x['exit_code']==0 and x['exception'] is None and x['timed_out'] is False)
        check(label+'_summary',run['total']==total and run['passed']==total-skip and run['skipped']==skip and run['failures']==run['errors']==0)
        check(label+'_log_footer',re.findall(r'^Ran (\d+) tests in [\d.]+s$',text,re.M)==[str(total)] and
              re.search(r'^OK'+(r' \(skipped=1\)' if skip else '')+r'\s*$',text,re.M))
        ids=re.findall(r'^test_\w+ \((test_f3_int117_[^)]+)\) \.\.\.',text,re.M)
        check(label+'_all_21_ids',len(ids)==21 and set(ids)==expected_ids)
        c=x['cleanup'];check(label+'_cleanup',c['confirmed'] is True and c['active_processes']==0 and c['live_io_threads']==[] and all(p['exit_confirmed'] for p in c['processes']))
        check(label+'_relocated_log_same',(WORK/'.r117/audit/EVIDENCIAS_F3_INT117'/(label+'.log')).read_bytes()==(e/(label+'.log')).read_bytes())
        check(label+'_report_matches',f"{total} testes, {total-skip} aprovados, {skip} skipped" in report and f"{run['seconds']} s." in report)
        details[label]=dict(log_sha256=sha(e/(label+'.log')),execution_sha256=sha(e/(label+'.log.execution.json')),total=total,passed=total-skip,skipped=skip)
        experiments=[json.loads(line) for line in text.splitlines() if line.startswith('{"experiment": "F3-INT-117"')]
        check(label+'_three_native_experiments',len(experiments)==3 and {v['mode'] for v in experiments}=={'normal','full','readonly'})
        for v in experiments:
            mode=v['mode'];check(label+'_'+mode+'_integrity',v['integrity_check']=='ok' and v['reopened_state']==v['expected_after' if mode=='normal' else 'expected_before'])
            check(label+'_'+mode+'_cleanup_and_no_retry',v['fixture_removed'] is True and v['automatic_retries']==0 and v['retry_allowed'] is False)
            check(label+'_'+mode+'_anchors_preserved',v['retained_sha256_before']==v['retained_sha256_after'])
            if mode!='normal':
                check(label+'_'+mode+'_native_phase',v['attempt']['error']['primary_code']==(13 if mode=='full' else 8) and v['attempt']['error']['phase']=='UPDATE' and 'commit_entered' not in v['attempt']['events'] and v['database_unchanged_on_failure'] is True)
    check('security_metadata',all(v['f3']=='OPEN' and len(v['locks'])==7 and all(flag is False for flag in v['locks'].values()) and v['promoted'] is False for v in (m,a,r)))
    marker=read(WORK/'ULTIMO_MARCO.json');check('marker_remains_116_final',marker['stage']=='F3-INT-116' and marker['checkpoint_type']=='FINAL')
    zpath=WORK/'audit/F3_INT117_CANDIDATA_COMPLETA_20261024.zip'
    check('zip_expected_sha256',sha(zpath)=='ef2c88a9b28dfda119eeb78524b3f00c0fc523d2f7878cf97a58e7bbe92b08ae')
    with zipfile.ZipFile(zpath) as z:
        payload=json.loads(z.read('MANIFESTO_PACOTE.json'))['files_sha256']
        check('zip_crc',z.testzip() is None)
        check('zip_all_members_sha256',all(hashlib.sha256(z.read(n)).hexdigest()==d for n,d in payload.items()))
        check('zip_manifest_same',z.read('f3_int117_work/audit/MANIFESTO_F3_INT117_CANDIDATA.json')==(ROOT/'MANIFESTO_F3_INT117_CANDIDATA.json').read_bytes())
        check('zip_229_executed_sources',all(hashlib.sha256(z.read('f3_int117_work/audit/'+n)).hexdigest()==d for n,d in src.items()))
    return dict(checks=checks,details=details,passed=sum(checks.values()),total=len(checks),failed=[n for n,v in checks.items() if not v])


def adversarial_capacity():
    fixtures.ConsumptionStoreTests.setUpClass();f=fixtures.ConsumptionStoreTests
    with tempfile.TemporaryDirectory(prefix='audit117_') as directory:
        path=Path(directory)/'probe.sqlite';original=Path(directory)/'original.sqlite'
        history=[format(i,'064x') for i in range(4096)]
        before=dict(version=1,generation=4096,next_revision=2,scope=list(f.scope.values()),consumed=history)
        proposed=probe.build_typed_chain(f.segments,**f.scope,batches=f.next_batches)
        require(proposed.digest not in history,'Fixture collision')
        after=dict(before,generation=4097,next_revision=3,consumed=sorted(history+[proposed.digest]))
        probe.seed(path,before,512);shutil.copy2(path,original)
        pins=dict(before_state_digest=store._digest(before),after_state_digest=store._digest(after),expected_chain_digest=proposed.digest)
        original_result=store.consume_chain(original,f.segments,expected_state_digest=pins['before_state_digest'],expected_digest=proposed.digest,batches=f.next_batches,**f.scope)
        attempted=probe.write_once(path,'normal',before=before,after=after,pins=pins,segments=f.segments,batches=f.next_batches,scope=f.scope)
        try:
            probe.snapshot(path)
            reopened='ACCEPTED'
        except ValueError as error:
            reopened=type(error).__name__+': '+str(error)
        original_ok=store.verify_store(original,expected_state_digest=pins['before_state_digest']).status
        result=dict(scope='Direct lower-level write_once; outside run_experiment bounded growth fixtures',
            original_status=original_result.status,original_state_after=original_ok,
            probe_attempt=attempted,probe_reopen=reopened,
            history_before=4096,history_after=4097)
    result['fixture_removed']=not Path(directory).exists()
    return result


def main():
    OUT.mkdir(exist_ok=False)
    before=inventory(PROJECT)
    checks=integrity();require(not checks['failed'],'Consistency checks failed')
    (OUT/'CONSISTENCIA.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
    print('Consistency:',checks['passed'],'/',checks['total'],flush=True)
    # Inherited gate starts a real -O interpreter as a supervised descendant.
    code="import subprocess,sys;sys.exit(subprocess.call([sys.executable,'-O','-B','-m','unittest','discover','-s','tests','-p','test_f3_int117_*.py','-v']))"
    execution=run_supervised([sys.executable,'-B','-c',code],cwd=ROOT,log=OUT/'ESPECIFICOS_REAUDITORIA_O.log',timeout=600)
    counts=summarize((OUT/'ESPECIFICOS_REAUDITORIA_O.log').read_text(encoding='utf8'))
    require(execution['exit_code']==0 and execution['exception'] is None and not execution['timed_out'],'Reaudit failed')
    require(counts['total']==21 and counts['passed']==21 and counts['skipped']==counts['failures']==counts['errors']==0,'Reaudit summary failed')
    require(execution['cleanup']['confirmed'] and execution['cleanup']['active_processes']==0 and execution['cleanup']['live_io_threads']==[],'Reaudit cleanup failed')
    (OUT/'REEXECUCAO.json').write_text(json.dumps(dict(execution=execution,counts=counts),indent=2),encoding='utf8')
    capacity=adversarial_capacity()
    (OUT/'DIFERENCA_INVARIANTE_CAPACIDADE.json').write_text(json.dumps(capacity,indent=2),encoding='utf8')
    changed=mismatch(before,PROJECT)
    require(not changed,'Candidate files changed during audit')
    result=dict(candidate_unchanged=True,candidate_files_verified=len(before),optimized_specifics=counts,
        consistency_passed=checks['passed'],consistency_total=checks['total'],capacity_difference=capacity)
    (OUT/'RESULTADO_AUDITORIA.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(dict(counts=counts,capacity=capacity,candidate_files_unchanged=len(before))),flush=True)

if __name__=='__main__':main()
