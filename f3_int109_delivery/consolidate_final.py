"""Consolidate validated INT-109 bytes offline; preserve all previous artifacts."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(r'C:\COPILOTO_F3_INT108')
AUDIT=ROOT/'audit'
ZIP=ROOT/'PACOTE_AUDITORIA_F3_INT109_FINAL.zip'
SIDECAR=Path(str(ZIP)+'.sha256')
RECEIPT=ROOT/'VERIFICACAO_PACOTE_F3_INT109_FINAL.json'
MANIFEST=ROOT/'MANIFESTO_PACOTE_F3_INT109_FINAL.json'
LOCKS=('orders_allowed','live_certified','flow_complete','f3_resolved',
       'native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def dump(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def safety(value):
    return (value['f3']=='OPEN' and value['offline'] is True and value['simulation_only'] is True
            and value['certification'] is False and set(value['locks'])==set(LOCKS)
            and all(value['locks'][key] is False for key in LOCKS))

for path in (ZIP,SIDECAR,RECEIPT,MANIFEST,AUDIT/'CHECKPOINT_F3_INT109_FINAL.json',
             AUDIT/'CHECKPOINT_F3_INT109_FINAL.md',AUDIT/'HISTORICO_ULTIMO_MARCO_F3_INT108.json',
             AUDIT/'ESCOPO_F3_INT110_PRELIMINAR.md',ROOT/'CONSOLIDACAO_F3_INT109_FINAL.json'):
    assert not path.exists(), 'Refusing to replace: '+str(path)
validation=load(ROOT/'VALIDACAO_F3_INT109_COMPLETA.json')
candidate=load(AUDIT/'CHECKPOINT_F3_INT109_CANDIDATO.json')
old_bytes=(AUDIT/'ULTIMO_MARCO.json').read_bytes()
old=json.loads(old_bytes)
assert old['last_completed']=='F3-INT-108' and safety(old)
assert candidate['stage']=='F3-INT-109' and candidate['status']=='CANDIDATO' and safety(candidate)
assert validation['approved'] is True and validation['locks_verified'] is True and safety(validation)
assert validation['source_and_checkpoints_unchanged'] is True
snapshot=validation['preserved_sha256']
for name,digest in snapshot.items():
    assert sha((AUDIT/name).read_bytes())==digest, 'Changed validated file: '+name
for name,digest in candidate['source_sha256'].items():
    assert sha((AUDIT/name).read_bytes())==digest
python_files={p.relative_to(AUDIT).as_posix() for folder in ('tools','tests') for p in (AUDIT/folder).rglob('*.py')}
tested_python={Path(name).as_posix() for name in snapshot if name.endswith('.py')}
assert python_files==tested_python
previous_checkpoints={p.relative_to(AUDIT).as_posix():sha(p.read_bytes()) for p in AUDIT.glob('CHECKPOINT*') if p.is_file()}
original_files={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in ROOT.rglob('*') if p.is_file()}
assert not any(p.is_symlink() for p in ROOT.rglob('*'))
for label,expected,key in [('NOVOS',29,'new_tests'),('REGRESSAO',1322,'regression')]:
    result=load(ROOT/f'VALIDACAO_F3_INT109_{label}.json')
    assert result==validation[key]
    assert result['approved'] is True and result['total']==result['passed']==expected and result['exit_code']==0
    assert all(result[k]==0 for k in ('failures','errors','skipped','expected failures','unexpected successes'))
    log_path=ROOT/f'VALIDACAO_F3_INT109_{label}.log'
    assert sha(log_path.read_bytes())==result['log_sha256']
    text=log_path.read_text(encoding='utf-8')
    assert len(re.findall(r'^test_.* \.\.\. ok$',text,re.MULTILINE))==expected
    assert re.search(r'Ran '+str(expected)+r' tests in '+re.escape(str(result['unittest_seconds']))+r's\s+OK\s*\Z',text)
assert sha((ROOT/'PACOTE_AUDITORIA_F3_INT108_FINAL.zip').read_bytes())=='8c7f0ae1a18ff265cca9084ce60913adc0898301420d557b86cf550316b27033'
evidence={p.name:sha(p.read_bytes()) for p in ROOT.glob('VALIDACAO_F3_INT109*') if p.is_file()}
evidence['RESULTADO_F3_INT109_COMPLETO.txt']=sha((ROOT/'RESULTADO_F3_INT109_COMPLETO.txt').read_bytes())
final=dict(stage='F3-INT-109',last_completed='F3-INT-109',checkpoint_type='FINAL',
           status='OFFLINE_REGRESSION_APPROVED',previous_definitive='F3-INT-108',
           new_tests=validation['new_tests'],regression=validation['regression'],
           total_validation_seconds=validation['total_seconds'],f3='OPEN',locks={k:False for k in LOCKS},
           offline=True,simulation_only=True,certification=False,
           validation_evidence_sha256=evidence,validated_snapshot_sha256=snapshot,
           consolidated_source_sha256={name:snapshot[name] for name in snapshot if name.endswith('.py')},
           reviewed_candidate_sha256=sha((AUDIT/'CHECKPOINT_F3_INT109_CANDIDATO.json').read_bytes()),
           historical_candidate_preserved=True,
           next_step='F3-INT-110: escopo preliminar documentado; implementacao nao iniciada',
           pending=['Rollback conjunto de banco e ancora continua permitindo replay.',
                    'Confirmacao perdida apos commit exige reconciliacao independente; nao ha commit distribuido.',
                    'Durabilidade de hardware, fencing distribuido e autenticacao de origem nao demonstrados.',
                    'Hashes nao autenticam origem. Sem certificacao ou autorizacao operacional.'])
assert safety(final)
(AUDIT/'HISTORICO_ULTIMO_MARCO_F3_INT108.json').write_bytes(old_bytes)
dump(AUDIT/'CHECKPOINT_F3_INT109_FINAL.json',final)
(AUDIT/'CHECKPOINT_F3_INT109_FINAL.md').write_text(f'''# F3-INT-109 — definitivo offline

29/29 testes novos aprovados, zero falhas, erros e skips; exit 0;
40,705 s no unittest. Regressão integral: 1322/1322 aprovados,
zero falhas, erros e skips; exit 0; 683,081 s no unittest.
Tempo total de validação: 728,241 s. Sem ResourceWarnings.

Conferidos {len(snapshot)} hashes do snapshot integral e o inventário exato dos
{len(python_files)} arquivos Python em tools/ e tests/. Nenhuma alteração de código.
Logs, relatórios de validação e checkpoint candidato preservados como histórico.
O candidato reflete a aprovação específica original; este FINAL registra
também a regressão integral posterior. Checkpoints anteriores intactos.
Marcador anterior preservado em HISTORICO_ULTIMO_MARCO_F3_INT108.json.

F3=OPEN. Sete bloqueios false. Sem certificação operacional.
F3-INT-110 somente com escopo preliminar, sem implementação.
''',encoding='utf-8')
(AUDIT/'ESCOPO_F3_INT110_PRELIMINAR.md').write_text('''# F3-INT-110 — escopo preliminar, sem implementação

Base proposta: F3-INT-109 definitivo. F3=OPEN; sete bloqueios false.
Este escopo não inicia a implementação nem autoriza uso operacional.

1. Restauração conjunta de banco e âncora: reproduzir o replay já permitido
   quando ambos voltam ao passado. Especificar fronteira de confiança e âncora
   independente não restaurável junto do banco. Contador, hash ou cópia no mesmo
   backup não são proteção antirrollback. Se a independência não for assegurada,
   declarar o caso indetectável; não simular uma garantia real inexistente.
2. Reconciliação após confirmação perdida: modelar estados preparado,
   confirmado e desconhecido, consulta de resultado e identificação idempotente.
   Cobrir commit seguido de morte do processo e falha de retenção da âncora.
   Não aceitar recomputação da âncora a partir de estado não confiável como prova.
   Reconciliar sem duplicar consumo, reduzir piso ou esvaziar histórico.
3. Limites do consumo atômico: separar transação no mesmo SQLite de cópias do
   banco, múltiplos processos, hosts e estados externos. Avaliar contenção,
   repetição, pontos de falha e eventuais requisitos de fencing independente.
   Não alegar exatamente uma entrega ao chamador a partir de commit local.
4. Durabilidade: distinguir recuperação após morte de processo de falha de
   energia, disco, controladora e filesystem. Definir evidências necessárias
   e limites dos modelos offline; FULL/DELETE solicitado não comprova hardware.
5. Autenticação de origem: especificar identidade, distribuição confiável de
   pins, gestão de chaves e revogação antes de avaliar mecanismos. Hashes,
   âncoras locais e assinaturas autodeclaradas não autenticam uma origem confiável.

Critérios propostos: contraexemplos reproduzíveis antes de alterações; correções
isoladas justificadas; testes positivos e adversariais de reinício, rollback,
reconciliação e concorrência; compatibilidade com 105–109; regressão integral.
Não alterar checkpoints definitivos durante exploração. Não implementar nesta
consolidação. Sem rede operacional, Profit, Excel, RTD, DDE, corretora ou ordens.
orders_allowed, live_certified, flow_complete, f3_resolved,
native_prototype_authorized, strict_deadline_guaranteed e
authenticated_witness_verified permanecem false. Sem certificação operacional.
''',encoding='utf-8')
dump(AUDIT/'ULTIMO_MARCO.json',final)
assert all(sha((AUDIT/name).read_bytes())==digest for name,digest in previous_checkpoints.items())
assert all(sha((ROOT/name).read_bytes())==digest for name,digest in original_files.items() if name!='audit/ULTIMO_MARCO.json')
assert (AUDIT/'HISTORICO_ULTIMO_MARCO_F3_INT108.json').read_bytes()==old_bytes
dump(ROOT/'CONSOLIDACAO_F3_INT109_FINAL.json',dict(
    stage='F3-INT-109',status='FINAL_OFFLINE',checked_snapshot_files=len(snapshot),
    identical_tested_python_files=len(python_files),previous_checkpoints_preserved=len(previous_checkpoints),
    new_tests=validation['new_tests'],regression=validation['regression'],f3='OPEN',locks={k:False for k in LOCKS},
    offline=True,simulation_only=True,certification=False,f3_int110_implemented=False,
    evidence_sha256=evidence,original_workspace_files=len(original_files)))

# Include previous packages and all historical evidence. Only the new ZIP and
# its post-package receipts are external; the manifest excludes its own hash.
excluded={ZIP,SIDECAR,RECEIPT,MANIFEST}
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p not in excluded)
manifest={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in files}
dump(MANIFEST,dict(algorithm='SHA-256',files=manifest,
                  note='Manifesto exclui seu proprio hash. ZIP109, sidecar109 e recibo109 sao externos.'))
files.append(MANIFEST)
expected={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in files}
with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in files: z.write(path,path.relative_to(ROOT).as_posix())
with zipfile.ZipFile(ZIP) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert len(names)==len(set(names))==len(files) and set(names)==set(expected)
    for name in names:
        assert not name.startswith('/') and '..' not in Path(name).parts
        assert sha(z.read(name))==expected[name]
    assert json.loads(z.read(MANIFEST.name))['files']==manifest
    for name in ('audit/ULTIMO_MARCO.json','audit/CHECKPOINT_F3_INT109_FINAL.json'):
        value=json.loads(z.read(name));assert value['last_completed']=='F3-INT-109' and safety(value)
        assert value['regression']['total']==value['regression']['passed']==1322
    assert z.read('audit/HISTORICO_ULTIMO_MARCO_F3_INT108.json')==old_bytes
    assert all(sha(z.read('audit/'+name))==snapshot[name] for name in python_files)
    assert all(sha(z.read('audit/'+name))==digest for name,digest in previous_checkpoints.items())
package_hash=sha(ZIP.read_bytes())
SIDECAR.write_text(package_hash+'  '+ZIP.name+'\n',encoding='ascii')
assert SIDECAR.read_text().split()[0]==sha(ZIP.read_bytes())
receipt=dict(package=str(ZIP),file_count=len(files),sha256=package_hash,size_bytes=ZIP.stat().st_size,
             crc_verified=True,manifest_verified=True,all_archived_bytes_match_workspace=True,
             exact_tested_python_files_verified=len(python_files),historical_checkpoints_unchanged=True,
             candidate_preserved=True,previous_package_108_unchanged=True,
             definitive_checkpoint='F3-INT-109',regression_passed=1322,new_tests_passed=29,
             f3='OPEN',locks={k:False for k in LOCKS},offline=True,simulation_only=True,
             certification=False,f3_int110_implemented=False,
             external_receipts=[SIDECAR.name,RECEIPT.name])
dump(RECEIPT,receipt)
print(json.dumps(receipt,indent=2),flush=True)
