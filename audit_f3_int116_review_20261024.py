"""Independent review evidence; never modifies candidate or FINAL files."""
import hashlib
import json
from pathlib import Path
import sys

WORK = Path(__file__).resolve().parent
ROOT = WORK / 'f3_int116_work/audit'
BASE = Path('C:/COPILOTO_F3_INT115_FINAL')
OUT = WORK / 'audit/F3_INT116_REVISAO_20261024'
sys.path.insert(0, str(ROOT))
from tools.f3_int115_process_control import run_supervised
from tools.f3_int115_run_candidate import summarize

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}

def mismatch(pins, root):
    return [n for n, h in pins.items() if not (root/n).is_file() or sha(root/n) != h]

def main():
    OUT.mkdir(exist_ok=False)
    baseline = inventory(BASE)
    candidate = inventory(ROOT.parent)
    manifest = json.loads((ROOT/'MANIFESTO_F3_INT116_CANDIDATA.json').read_bytes())
    old = json.loads((BASE/'audit/MANIFESTO_F3_INT115_FINAL.json').read_bytes())
    data = dict(base_count=len(baseline), candidate_count=len(candidate),
        base_manifest_count=len(old['files_sha256']),
        base_manifest_errors=mismatch(old['files_sha256'], BASE),
        inherited_errors=mismatch(baseline, ROOT.parent),
        candidate_manifest_errors=mismatch(manifest['files_sha256'], ROOT),
        manifest_sidecar_ok=sha(ROOT/'MANIFESTO_F3_INT116_CANDIDATA.json') ==
            (ROOT/'MANIFESTO_F3_INT116_CANDIDATA.json.sha256').read_text().split()[0],
        added=sorted(set(candidate)-set(baseline)),
        modified=sorted(n for n in baseline.keys() & candidate.keys() if baseline[n]!=candidate[n]),
        removed=sorted(set(baseline)-set(candidate)), runs=[])
    (OUT/'ANTES.json').write_text(json.dumps(dict(base=baseline,candidate=candidate,checks=data),indent=2),encoding='utf8')
    assert not any(data[n] for n in ('base_manifest_errors','inherited_errors','candidate_manifest_errors','modified','removed'))
    assert data['manifest_sidecar_ok']
    for label, pattern in [('ESPECIFICOS','test_f3_int116_commit_recovery.py'),('REGRESSAO_COMPLETA','test_*.py')]:
        result = run_supervised([sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v'],cwd=ROOT,log=OUT/(label+'.log'),timeout=3600)
        result.update(label=label,**summarize((OUT/(label+'.log')).read_text(encoding='utf8',errors='replace')))
        data['runs'].append(result)
        data['base_changed_after']=mismatch(baseline,BASE)
        data['candidate_changed_after']=mismatch(candidate,ROOT.parent)
        (OUT/'RESULTADO.json').write_text(json.dumps(data,indent=2),encoding='utf8')
        print(json.dumps(result),flush=True)
        assert result['exit_code']==0 and not result['exception'] and not result['timed_out']
        assert result['cleanup']['confirmed'] and result['cleanup']['active_processes']==0 and not result['cleanup']['live_io_threads']
        assert not data['base_changed_after'] and not data['candidate_changed_after']
        assert result['total'] and result['failures']==result['errors']==0
    print('REVIEW_TESTS_COMPLETE',flush=True)

if __name__=='__main__':
    main()
