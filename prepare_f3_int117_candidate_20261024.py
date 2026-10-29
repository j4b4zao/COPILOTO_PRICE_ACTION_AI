"""Freeze immutable inputs and relocate the candidate before running its auditor."""
import hashlib
import json
from pathlib import Path
import shutil

WORK=Path(__file__).resolve().parent
SOURCE=WORK/'f3_int117_work'
FINAL=WORK/'f3_int116_final'
OUT=WORK/'audit/F3_INT117_CANDIDATA_20261024'
RELOCATED=WORK/'.r117'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}

def main():
    if OUT.exists() or RELOCATED.exists():raise RuntimeError('Refusing to overwrite evidence')
    before=inventory(FINAL); candidate=inventory(SOURCE)
    for name,digest in before.items():
        if candidate.get(name)!=digest or candidate.get('b116/'+name)!=digest:
            raise RuntimeError('Inherited FINAL file mismatch: '+name)
    for name in ('ULTIMO_MARCO.json','audit/ULTIMO_MARCO.json','CHECKPOINT_F3_INT116_FINAL.json','audit/CHECKPOINT_F3_INT116_FINAL.json'):
        if json.loads((WORK/name).read_bytes())['stage']!='F3-INT-116':raise RuntimeError('Unexpected workspace marker')
    additions=sorted(set(candidate)-set(before)-{'b116/'+n for n in before})
    expected=['audit/tests/test_f3_int117_runner.py','audit/tests/test_f3_int117_sqlite_write_faults.py',
              'audit/tools/f3_int117_run_audit.py','audit/tools/f3_int117_sqlite_write_faults.py']
    if additions!=expected:raise RuntimeError('Unexpected additions: '+repr(additions))
    OUT.mkdir()
    evidence=dict(final_before=before,candidate_before=candidate,added_sources=additions,
        workspace_markers={n:sha(WORK/n) for n in ('ULTIMO_MARCO.json','audit/ULTIMO_MARCO.json',
            'CHECKPOINT_F3_INT116_FINAL.json','audit/CHECKPOINT_F3_INT116_FINAL.json')})
    (OUT/'ANTES.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
    shutil.copytree(SOURCE,RELOCATED,ignore=shutil.ignore_patterns('__pycache__'))
    if inventory(RELOCATED)!=candidate:raise RuntimeError('Relocation hash mismatch')
    print('Relocation verified; original FINAL files:',len(before),'candidate files:',len(candidate),flush=True)

if __name__=='__main__':main()
