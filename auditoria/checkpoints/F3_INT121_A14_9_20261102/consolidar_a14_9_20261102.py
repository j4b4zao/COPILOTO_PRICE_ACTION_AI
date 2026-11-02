"""Consolidate completed A14.9 runs; preserve operational restrictions."""
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

out=Path('outputs')
source=Path('work/a14_9_regressao_20261102/src')
root=source.parent/'work'
logs=[out/f'a14_9_regressao_{label}_20261102.log' for label in ('normal','otimizado')]
if any(not path.with_suffix('.exit.txt').exists() for path in logs): raise SystemExit('Both full runs must finish')
modes=[base.audit(path,mode,213) for mode,path in enumerate(logs)]
audits=dict(boundaries=base.audit_boundaries(root),barriers=barrier.audit_barriers(root),
    held_bridges=held.audit(root,logs),startup=startup.audit(root),journal=journal.audit(root),sharing=sharing.audit(root))
files=json.loads((out/'MANIFESTO_A14_9_CANDIDATA_20261102.json').read_bytes())['files_sha256']
previous=json.loads((out/'MANIFESTO_A14_8_20261102.json').read_bytes())['files_sha256']
mismatches=[name for name,sha in files.items() if hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha]
mismatches+=['A14.8/'+name for name,sha in previous.items() if hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha]
specific=[]
for mode,label in enumerate(('normal','otimizado')):
    log=out/f'a14_9_especificos_{label}_20261102.log'
    data=log.read_bytes()
    text=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    summaries=re.findall(r'^Ran (\d+) tests in ([\d.]+)s\s*$',text,re.M)
    code=log.with_suffix('.exit.txt').read_text(encoding='utf-8-sig').strip()
    accepted=code=='0' and len(summaries)==1 and summaries[0][0]=='4' and bool(re.search(r'^OK\s*\Z',text,re.M))
    specific.append(dict(optimization=mode,accepted=accepted,summary=summaries,sha256=hashlib.sha256(data).hexdigest()))
accepted=not mismatches and all(m['accepted'] for m in modes+specific) and all(a['accepted'] for a in audits.values())
status='A14_9_VALIDADA_LOCALMENTE' if accepted else 'REGRESSAO_NAO_APROVADA'
checkpoint=out/'CHECKPOINT_A14_9_20261102.json'
record=dict(date='2026-11-02',stage='F3-INT-121 A14.9',status=status,f3='OPEN',offline=True,
    simulation_only=True,real_operations_authorized=False,runtime_modified=False,production_api_changed=False,
    original_project_modified=False,previous_175_source_files_preserved=not mismatches,
    source_files=177,source_mismatches=mismatches,expected_tests_per_mode=213,modes=modes,specific=specific,audits=audits,
    python=sys.version,executable=sys.executable,authentication_tested=False,durability_tested=False,
    strict_deadline_guaranteed=False,scope='Real Windows share denial and bounded retry budget after native safety cleanup',
    next_step='Review remaining private diagnostic cases without changing operational authorization')
checkpoint.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
manifest=out/'MANIFESTO_A14_9_20261102.json'
manifest.write_text(json.dumps(dict(stage='A14.9',status=status,files_sha256=files),indent=2),encoding='utf-8')
report=out/'RETOMADA_A14_9_20261102.md'
text='# COPILOTO_PRICE_ACTION_AI — A14.9, 2/11/2026\n\n'+status+'\n\n'
text+='F3 OPEN; offline=true; simulation_only=true; operacoes reais bloqueadas. Projeto operacional preservado.\n\n'
for mode,label in zip(modes,('Normal','Otimizado')):
    text+=f"- {label}: {mode['summary']}; auditoria aceita={mode['accepted']}.\n"
    for error in mode['failures']: text+='  Falha: '+error+'\n'
for name,audit in audits.items():
    count=audit.get('records',len(audit.get('files',[])))
    text+=f"- {name}: {count} registros; aceita={audit['accepted']}.\n"
    for error in audit['failures']: text+='  Falha: '+error+'\n'
text+= ('\nSomente dois arquivos acrescentados: f3_int121_a14_9_readback.py e test_f3_int121_a14_9_sharing.py. '
        'Os 175 arquivos da A14.8 foram preservados.\n\n'
        'Quatro novos cenarios por modo: bloqueio real transitorio com recuperacao; bloqueio persistente; '
        'arquivo ausente; conteudo adulterado rejeitado depois da liberacao. CreateFileW confirma '
        'ERROR_SHARING_VIOLATION=32; Path.read_bytes preserva PermissionError/errno=13 e o winerror '
        'efetivamente observado, inclusive null quando Python nao o fornece.\n\n'
        'O leitor privado diferencia JOURNAL_READ_DENIED, JOURNAL_MISSING e a verificacao de conteudo. '
        'O callback privado libera um handle real depois da primeira leitura negada; Path.read_bytes nao e mockado. '
        'O caso persistente mantem o handle ate o encerramento do orcamento e preserva o ultimo erro. '
        'Todos os handles de arquivo sao fechados em finally. A limpeza nativa antecede as leituras e o bloqueio.\n\n'
        'O auditor independente verifica os bytes, as identidades nativas, as tentativas, o tempo de liberacao '
        'e os diagnosticos. Foram rejeitadas 28 adulteracoes sinteticas em cada modo do auditor, fora dos 213 testes.\n\n'
        'Limite: o orcamento restringe novas tentativas, mas nao garante prazo estrito para escalonamento '
        'ou chamadas de sistema bloqueantes. Nao comprova autenticacao nem durabilidade contra queda de energia. '
        'Nenhuma API operacional ou status NATIVE_CLEANUP_NOT_CONFIRMED foi promovido.\n\n'
        'Para reproduzir: extrair em pasta nova no Windows com Python 3.13.5 e cryptography 50.0.2 e executar '
        'sequencialmente `python -B -m unittest discover -v` e `python -O -B -m unittest discover -v`. '
        'Esperados 213 testes por modo. Manifesto vigente em audit/A14_9/; manifestos herdados sao historicos.\n\n'
        'Os checkpoints anteriores permanecem preservados no GitHub. O bundle completo do historico Git original '
        'continua apenas local; nao publica-lo, pois inclui refs e stash locais.\n')
report.write_text(text,encoding='utf-8')
patch=out/'A14_9_DELTA.patch'
patch.write_text(''.join(''.join(difflib.unified_diff([], (source/name).read_text(encoding='utf-8').splitlines(True),
    fromfile='/dev/null',tofile='b/'+name)) for name in sorted(set(files)-set(previous))),encoding='utf-8')
support=[checkpoint,manifest,report,patch,out/'auditar_regressao.py',out/'auditar_a14_6.py',
    out/'auditar_a14_6_retencao.py',out/'auditar_a14_7.py',out/'auditar_a14_8.py',out/'auditar_a14_9.py',
    out/'A14_9_VERIFICACAO_AUDITOR_20261102.json',Path('work/verificar_auditor_a14_9.py'),
    Path('work/preparar_a14_9_integral.py'),Path('work/consolidar_a14_9_20261102.py')]
archive_path=out/'F3_INT121_A14_9_VALIDACAO_20261102.zip'
with ZipFile(archive_path,'w',ZIP_DEFLATED) as archive:
    for name in files: archive.write(source/name,name)
    for path in support: archive.write(path,'audit/A14_9/'+path.name)
    for prefix in ('a14_9_regressao_','a14_9_especificos_'):
        for label in ('normal','otimizado'):
            for suffix in ('.log','.exit.txt'):
                path=out/(prefix+label+'_20261102'+suffix)
                archive.write(path,'audit/A14_9/'+path.name)
    for pattern in ('a12_evidence_*/*.json','a14_6_evidence_*/*.json','a14_6_held_repeats_*/*.json',
        'a14_7_startup_evidence_*/*.json','a14_8_journal_evidence_*/*.json','a14_9_sharing_evidence_*/*.json'):
        for path in sorted(root.glob(pattern)):
            archive.write(path,'audit/A14_9/evidencias/'+path.parent.name+'/'+path.name)
    for path in sorted(Path('work/a14_9/work').glob('a14_9_sharing_evidence_*/*.json')):
        archive.write(path,'audit/A14_9/especificos/'+path.parent.name+'/'+path.name)
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
Path('work/upload_a14_9_validada_20261102.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(status=status,tests_per_mode=213,source_files=177,source_mismatches=mismatches,
    audits={k:v['accepted'] for k,v in audits.items()},zip_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest()),indent=2))
raise SystemExit(0 if accepted else 1)
