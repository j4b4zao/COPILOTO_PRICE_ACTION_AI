"""Consolidate completed A14.11 runs; preserve operational restrictions."""
import base64
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile,ZIP_DEFLATED

sys.path.insert(0,'outputs')
import auditar_regressao as base
import auditar_a14_6 as barrier
import auditar_a14_6_retencao as held
import auditar_a14_7 as startup
import auditar_a14_8 as journal
import auditar_a14_9 as sharing
import auditar_a14_10 as observer
import auditar_a14_11 as budget

out=Path('outputs')
source=Path('work/a14_11_regressao_20261102/src')
root=source.parent/'work'
logs=[out/f'a14_11_regressao_{label}_20261102.log' for label in ('normal','otimizado')]
if any(not path.with_suffix('.exit.txt').exists() for path in logs): raise SystemExit('Both full runs must finish')
modes=[base.audit(path,mode,220) for mode,path in enumerate(logs)]
audits=dict(boundaries=base.audit_boundaries(root),barriers=barrier.audit_barriers(root),
    held_bridges=held.audit(root,logs),startup=startup.audit(root),journal=journal.audit(root),sharing=sharing.audit(root),observer=observer.audit(root),budget=budget.audit(root))
files=json.loads((out/'MANIFESTO_A14_11_CANDIDATA_20261102.json').read_bytes())['files_sha256']
previous=json.loads((out/'MANIFESTO_A14_10_20261102.json').read_bytes())['files_sha256']
mismatches=[name for name,sha in files.items() if hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha]
mismatches+=['A14.9/'+name for name,sha in previous.items() if hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha]
specific=[]
for mode,label in enumerate(('normal','otimizado')):
    log=out/f'a14_11_especificos_{label}_20261102.log'
    data=log.read_bytes()
    text=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    summaries=re.findall(r'^Ran (\d+) tests in ([\d.]+)s\s*$',text,re.M)
    code=log.with_suffix('.exit.txt').read_text(encoding='utf-8-sig').strip()
    accepted=code=='0' and len(summaries)==1 and summaries[0][0]=='4' and bool(re.search(r'^OK\s*\Z',text,re.M))
    specific.append(dict(optimization=mode,accepted=accepted,summary=summaries,sha256=hashlib.sha256(data).hexdigest()))
accepted=not mismatches and all(m['accepted'] for m in modes+specific) and all(a['accepted'] for a in audits.values())
status='A14_11_VALIDADA_LOCALMENTE' if accepted else 'REGRESSAO_NAO_APROVADA'
checkpoint=out/'CHECKPOINT_A14_11_20261102.json'
record=dict(date='2026-11-03',stage='F3-INT-121 A14.11',status=status,f3='OPEN',offline=True,
    simulation_only=True,real_operations_authorized=False,runtime_modified=False,production_api_changed=False,
    original_project_modified=False,previous_178_source_files_preserved=not mismatches,
    source_files=180,source_mismatches=mismatches,expected_tests_per_mode=220,modes=modes,specific=specific,audits=audits,
    python=sys.version,executable=sys.executable,authentication_tested=False,durability_tested=False,
    strict_deadline_guaranteed=False,scope='First-attempt budget guard with controlled clock and real file',
    next_step='Review remaining private diagnostic cases without changing operational authorization')
checkpoint.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
manifest=out/'MANIFESTO_A14_11_20261102.json'
manifest.write_text(json.dumps(dict(stage='A14.11',status=status,files_sha256=files),indent=2),encoding='utf-8')
report=out/'RETOMADA_A14_11_20261102.md'
text='# COPILOTO_PRICE_ACTION_AI — A14.11, 3/11/2026\n\n'+status+'\n\n'
text+='F3 OPEN; offline=true; simulation_only=true; operacoes reais bloqueadas. Projeto operacional preservado.\n\n'
for mode,label in zip(modes,('Normal','Otimizado')):
    text+=f"- {label}: {mode['summary']}; auditoria aceita={mode['accepted']}.\n"
    for error in mode['failures']: text+='  Falha: '+error+'\n'
for name,audit in audits.items():
    count=audit.get('records',len(audit.get('files',[])))
    text+=f"- {name}: {count} registros; aceita={audit['accepted']}.\n"
    for error in audit['failures']: text+='  Falha: '+error+'\n'
text+='\nA14.11 testa o limite antes da primeira leitura com relogio controlado e arquivo real. O controle positivo usa relogio real. F3 OPEN, offline, simulation_only. Operacoes reais bloqueadas.\n'
report.write_text(text,encoding='utf-8')
patch=out/'A14_11_DELTA.patch'
patch.write_text(''.join(''.join(difflib.unified_diff([], (source/name).read_text(encoding='utf-8').splitlines(True),
    fromfile='/dev/null',tofile='b/'+name)) for name in sorted(set(files)-set(previous))),encoding='utf-8')
support=[checkpoint,manifest,report,patch,out/'auditar_regressao.py',out/'auditar_a14_6.py',
    out/'auditar_a14_6_retencao.py',out/'auditar_a14_7.py',out/'auditar_a14_8.py',out/'auditar_a14_9.py',out/'auditar_a14_10.py',out/'auditar_a14_11.py',out/'CONTRAPROVA_A14_11_PRIMEIRA_LEITURA_20261102.json',
    
    Path('work/preparar_a14_11_integral.py'),Path('work/consolidar_a14_11_20261102.py')]
archive_path=out/'F3_INT121_A14_11_VALIDACAO_20261102.zip'
with ZipFile(archive_path,'w',ZIP_DEFLATED) as archive:
    for name in files: archive.write(source/name,name)
    for path in support: archive.write(path,'audit/A14_11/'+path.name)
    for prefix in ('a14_11_regressao_','a14_11_especificos_'):
        for label in ('normal','otimizado'):
            for suffix in ('.log','.exit.txt'):
                path=out/(prefix+label+'_20261102'+suffix)
                archive.write(path,'audit/A14_11/'+path.name)
    for pattern in ('a12_evidence_*/*.json','a14_6_evidence_*/*.json','a14_6_held_repeats_*/*.json',
        'a14_7_startup_evidence_*/*.json','a14_8_journal_evidence_*/*.json','a14_9_sharing_evidence_*/*.json','a14_10_observer_evidence_*/*.json','a14_11_budget_evidence_*/*.json'):
        for path in sorted(root.glob(pattern)):
            archive.write(path,'audit/A14_11/evidencias/'+path.parent.name+'/'+path.name)
    for path in sorted(Path('work/a14_11/work').glob('a14_11_budget_evidence_*/*.json')):
        archive.write(path,'audit/A14_11/especificos/'+path.parent.name+'/'+path.name)
with ZipFile(archive_path) as archive:
    if archive.testzip() is not None: raise RuntimeError('Corrupt ZIP')
    for name,sha in files.items():
        if hashlib.sha256(archive.read(name)).hexdigest()!=sha: raise RuntimeError('Archived source mismatch')
checksum=archive_path.with_suffix('.zip.sha256')
checksum.write_text(hashlib.sha256(archive_path.read_bytes()).hexdigest()+'  '+archive_path.name+'\n',encoding='utf-8')
payload={}
for path in [*support,archive_path,checksum]:
    raw=path.read_bytes()
    try: content=raw.decode('utf-8'); encoding='utf-8'
    except UnicodeDecodeError: content=base64.b64encode(raw).decode('ascii'); encoding='base64'
    payload[path.name]=dict(content=content,encoding=encoding)
Path('work/upload_a14_11_validada_20261102.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(status=status,tests_per_mode=220,source_files=180,source_mismatches=mismatches,
    audits={k:v['accepted'] for k,v in audits.items()},zip_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest()),indent=2))
raise SystemExit(0 if accepted else 1)

