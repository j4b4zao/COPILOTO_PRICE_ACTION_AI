"""Preserve inventories and copy the corrected project to an unrelated path."""
import hashlib
import json
from pathlib import Path
import shutil

WORK=Path(__file__).resolve().parent
OUT=WORK/'audit/F3_INT116_CORRECAO_20261024'
SOURCE=WORK/'f3_int116_corrigida'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}

def main():
    OUT.mkdir(exist_ok=False)
    original=inventory(WORK/'f3_int116_work')
    base=inventory(SOURCE/'base_f3_int115_final')
    corrected=inventory(SOURCE)
    errors=[name for name,digest in base.items() if not (SOURCE/name).is_file() or sha(SOURCE/name)!=digest]
    if errors:raise RuntimeError('Historical FINAL mismatch: '+repr(errors))
    changed=[name for name,digest in original.items() if not (SOURCE/name).is_file() or sha(SOURCE/name)!=digest]
    if changed!=['audit/tools/f3_int116_run_audit.py']:
        raise RuntimeError('Unexpected correction changes: '+repr(changed))
    (OUT/'ANTES.json').write_text(json.dumps(dict(original_candidate=original,base_final=base,
        corrected_before=corrected,modified=changed),indent=2),encoding='utf8')
    moved=OUT/'Projeto em outra pasta'
    shutil.copytree(SOURCE,moved,ignore=shutil.ignore_patterns('__pycache__'))
    if inventory(moved)!=corrected:raise RuntimeError('Relocation copy mismatch')
    print(moved/'audit/tools/f3_int116_run_audit.py')

if __name__=='__main__':main()
