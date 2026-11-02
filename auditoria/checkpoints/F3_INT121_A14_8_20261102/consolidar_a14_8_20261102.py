"""Archive completed A14.8 runs and independent evidence replay."""
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

out=Path('outputs')
source=Path('work/a14_8_regressao_20261102/src')
root=source.parent/'work'
logs=[out/f'a14_8_regressao_{label}_20261102.log' for label in ('normal','otimizado')]
if any(not path.with_suffix('.exit.txt').exists() for path in logs):
    raise SystemExit('Both full runs must finish before consolidation')
modes=[base.audit(path,mode,209) for mode,path in enumerate(logs)]
audits=dict(boundaries=base.audit_boundaries(root),barriers=barrier.audit_barriers(root),
    held_bridges=held.audit(root,logs),startup=startup.audit(root),journal=journal.audit(root))
files=json.loads((out/'MANIFESTO_A14_8_CANDIDATA_20261102.json').read_bytes())['files_sha256']
previous=json.loads((out/'MANIFESTO_A14_7_20261102.json').read_bytes())['files_sha256']
mismatches=[name for name,sha in files.items() if hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha]
mismatches += ['A14.7/'+name for name,sha in previous.items()
               if hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha]
specific=[]
for mode,label in enumerate(('normal','otimizado')):
    log=out/f'a14_8_especificos_{label}_20261102.log'
    data=log.read_bytes()
    text=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    summaries=re.findall(r'^Ran (\d+) tests in ([\d.]+)s\s*$',text,re.M)
    code=log.with_suffix('.exit.txt').read_text(encoding='utf-8-sig').strip()
    accepted=code=='0' and len(summaries)==1 and summaries[0][0]=='8' and bool(re.search(r'^OK\s*\Z',text,re.M))
    specific.append(dict(optimization=mode,accepted=accepted,summary=summaries,
                         sha256=hashlib.sha256(data).hexdigest()))
accepted=not mismatches and all(m['accepted'] for m in modes+specific) and all(a['accepted'] for a in audits.values())
status='A14_8_VALIDADA_LOCALMENTE' if accepted else 'REGRESSAO_NAO_APROVADA'
checkpoint=out/'CHECKPOINT_A14_8_20261102.json'
record=dict(date='2026-11-02',stage='F3-INT-121 A14.8',status=status,f3='OPEN',offline=True,
    simulation_only=True,real_operations_authorized=False,runtime_modified=False,production_api_changed=False,
    original_project_modified=False,previous_173_source_files_preserved=True,source_files=175,source_mismatches=mismatches,
    expected_tests_per_mode=209,modes=modes,specific=specific,audits=audits,
    python=sys.version,executable=sys.executable,authentication_tested=False,durability_tested=False,
    scope='Readback after native safety cleanup, exact disk capture and comparison with private pipe record',
    next_step='Review read-error coverage; retain all operational restrictions and conservative API status')
checkpoint.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
manifest=out/'MANIFESTO_A14_8_20261102.json'
manifest.write_text(json.dumps(dict(stage='A14.8',status=status,files_sha256=files),indent=2),encoding='utf-8')
report=out/'RETOMADA_A14_8_20261102.md'
text='# COPILOTO_PRICE_ACTION_AI — A14.8, 2/11/2026\n\n'+status+'\n\n'
text+='F3 OPEN; offline=true; simulation_only=true; operacoes reais bloqueadas. Projeto operacional preservado.\n\n'
for mode,label in zip(modes,('Normal','Otimizado')):
    text+=f"- {label}: {mode['summary']}; auditoria aceita={mode['accepted']}.\n"
    for error in mode['failures']: text+='  Falha: '+error+'\n'
for name,audit in audits.items():
    count=audit.get('records',len(audit.get('files',[])))
    text+=f"- {name}: {count} registros; aceita={audit['accepted']}.\n"
    for error in audit['failures']: text+='  Falha: '+error+'\n'
text+= ('\nA etapa acrescenta apenas f3_int121_a14_8_journal.py e test_f3_int121_a14_8_journal.py. '
        'Os 173 arquivos da A14.7 foram preservados.\n\n'
        'Oito casos nativos novos por modo: journal valido; ausente; truncado; nonce trocado; '
        'identidade trocada; limpeza adulterada; autorizacao adulterada; falha real de publicacao com fallback. '
        'Os bytes originais e capturados ficam em base64 nos registros, com SHA-256 e tempos de leitura. '
        'A leitura e qualquer adulteracao ocorrem depois da confirmacao do encerramento no Job externo. '
        'O comparador e o auditor foram verificados com 28 contraexemplos sinteticos, fora dos 209 testes.\n\n'
        'O auditor independente verifica os bytes, a mudanca exata de cada fixture, os hashes e a ordem temporal; '
        'nao importa o comparador da candidata. Reutiliza apenas o auditor offline da prova nativa A14.7.\n\n'
        'Limite: igualdade do journal com um registro privado recebido por pipe nao prova autenticacao '
        'nem durabilidade contra queda de energia, fsync ou falha fisica do disco. Nenhuma promocao de '
        'run_native_worker ou NATIVE_CLEANUP_NOT_CONFIRMED foi feita.\n\n'
        'Para reproduzir no Windows, extrair em pasta nova e executar sequencialmente '
        '`python -B -m unittest discover -v` e `python -O -B -m unittest discover -v`. '
        'Esperados 209 testes por modo. Manifesto vigente em audit/A14_8/; manifestos herdados sao historicos. '
        'Python 3.13.5 e cryptography 50.0.2 foram usados nesta validacao.\n\n'
        'Proxima lacuna para avaliar: erros de leitura diferentes de arquivo ausente, como compartilhamento '
        'negado por um handle real do Windows. Isso nao foi executado nesta etapa.\n')
report.write_text(text,encoding='utf-8')
patch=out/'A14_8_DELTA.patch'
patch.write_text(''.join(''.join(difflib.unified_diff([], (source/name).read_text(encoding='utf-8').splitlines(True),
    fromfile='/dev/null',tofile='b/'+name)) for name in sorted(set(files)-set(previous))),encoding='utf-8')
support=[checkpoint,manifest,report,patch,out/'auditar_regressao.py',out/'auditar_a14_6.py',
    out/'auditar_a14_6_retencao.py',out/'auditar_a14_7.py',out/'auditar_a14_8.py',
    out/'A14_8_VERIFICACAO_AUDITOR_20261102.json',Path('work/verificar_auditor_a14_8.py'),
    Path('work/preparar_a14_8_integral.py'),Path('work/consolidar_a14_8_20261102.py')]
archive_path=out/'F3_INT121_A14_8_VALIDACAO_20261102.zip'
with ZipFile(archive_path,'w',ZIP_DEFLATED) as archive:
    for name in files: archive.write(source/name,name)
    for path in support: archive.write(path,'audit/A14_8/'+path.name)
    for prefix in ('a14_8_regressao_','a14_8_especificos_'):
        for label in ('normal','otimizado'):
            for suffix in ('.log','.exit.txt'):
                path=out/(prefix+label+'_20261102'+suffix)
                archive.write(path,'audit/A14_8/'+path.name)
    for pattern in ('a12_evidence_*/*.json','a14_6_evidence_*/*.json','a14_6_held_repeats_*/*.json',
                    'a14_7_startup_evidence_*/*.json','a14_8_journal_evidence_*/*.json'):
        for path in sorted(root.glob(pattern)):
            archive.write(path,'audit/A14_8/evidencias/'+path.parent.name+'/'+path.name)
    for path in sorted(Path('work/a14_8/work').glob('a14_8_journal_evidence_*/*.json')):
        archive.write(path,'audit/A14_8/especificos/'+path.parent.name+'/'+path.name)
with ZipFile(archive_path) as archive:
    if archive.testzip() is not None: raise RuntimeError('Corrupt ZIP')
    for name,sha in files.items():
        if hashlib.sha256(archive.read(name)).hexdigest()!=sha: raise RuntimeError('Archived source mismatch')
checksum=archive_path.with_suffix('.zip.sha256')
checksum.write_text(hashlib.sha256(archive_path.read_bytes()).hexdigest()+'  '+archive_path.name+'\n',encoding='utf-8')
payload={}
for path in [*support,archive_path,checksum]:
    raw=path.read_bytes()
    try:
        content=raw.decode('utf-8'); encoding='utf-8'
    except UnicodeDecodeError:
        content=base64.b64encode(raw).decode('ascii'); encoding='base64'
    payload[path.name]=dict(content=content,encoding=encoding)
Path('work/upload_a14_8_validada_20261102.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(status=status,tests_per_mode=209,source_files=175,source_mismatches=mismatches,
    audits={k:v['accepted'] for k,v in audits.items()},zip_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest()),indent=2))
raise SystemExit(0 if accepted else 1)
