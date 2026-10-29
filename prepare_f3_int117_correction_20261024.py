"""Freeze previous releases and relocate only the corrected candidate."""
import hashlib
import json
from pathlib import Path
import shutil
WORK=Path(__file__).resolve().parent
SOURCE=WORK/'f3_int117_corrigida'
OLD=WORK/'f3_int117_work'
FINAL=WORK/'f3_int116_final'
OUT=WORK/'audit/F3_INT117_CORRECAO_20261024'
RELOCATED=WORK/'.r117c'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}

def main():
    if OUT.exists() or RELOCATED.exists():raise RuntimeError('Refusing evidence overwrite')
    final=inventory(FINAL);old=inventory(OLD);current=inventory(SOURCE)
    for name,digest in final.items():
        if current.get(name)!=digest or current.get('b116/'+name)!=digest:
            raise RuntimeError('Historical FINAL changed: '+name)
    changed=sorted(n for n,d in old.items() if current.get(n)!=d)
    expected=['audit/tests/test_f3_int117_runner.py','audit/tools/f3_int117_run_audit.py',
              'audit/tools/f3_int117_sqlite_write_faults.py']
    if changed!=expected:raise RuntimeError('Unexpected correction changes: '+repr(changed))
    for name in expected:
        archived=SOURCE/'audit/PRESERVADO_117_PRE_CORRECAO'/Path(name).relative_to('audit')
        if sha(archived)!=old[name]:raise RuntimeError('Archived source missing: '+name)
    if current['audit/tests/test_f3_int117_sqlite_write_faults.py']!=old['audit/tests/test_f3_int117_sqlite_write_faults.py']:
        raise RuntimeError('Original 12 tests changed')
    OUT.mkdir()
    pins=dict(final_before=final,previous_candidate_before=old,corrected_before=current,modified_sources=changed,
        added_test='audit/tests/test_f3_int117_capacity_boundary.py',
        workspace_markers={n:sha(WORK/n) for n in ('ULTIMO_MARCO.json','audit/ULTIMO_MARCO.json',
            'CHECKPOINT_F3_INT116_FINAL.json','audit/CHECKPOINT_F3_INT116_FINAL.json')},
        release_hashes={n:sha(WORK/'audit'/n) for n in ('F3_INT116_FINAL_COMPLETA_20261024.zip',
            'F3_INT117_CANDIDATA_COMPLETA_20261024.zip')})
    (OUT/'ANTES.json').write_text(json.dumps(pins,indent=2),encoding='utf8')
    shutil.copytree(SOURCE,RELOCATED,ignore=shutil.ignore_patterns('__pycache__'))
    if inventory(RELOCATED)!=current:raise RuntimeError('Relocation mismatch')
    print('Relocated correction verified:',len(current),'files; FINAL:',len(final),flush=True)

if __name__=='__main__':main()
