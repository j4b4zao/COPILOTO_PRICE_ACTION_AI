"""Consolidate already-tested offline files; no operational imports or execution."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(r'C:\COPILOTO_F3_INT108')
AUDIT = ROOT/'audit'
ZIP = ROOT/'PACOTE_AUDITORIA_F3_INT108_FINAL.zip'
SIDECAR = Path(str(ZIP)+'.sha256')
VERIFICATION = ROOT/'VERIFICACAO_PACOTE_F3_INT108_FINAL.json'
MANIFEST = ROOT/'MANIFESTO_PACOTE_F3_INT108_FINAL.json'
LOCKS = ('orders_allowed','live_certified','flow_complete','f3_resolved',
         'native_prototype_authorized','strict_deadline_guaranteed',
         'authenticated_witness_verified')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write_json(path, obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def safety(obj):
    return obj['f3']=='OPEN' and obj['offline'] is True and obj['simulation_only'] is True and obj['certification'] is False and set(obj['locks'])==set(LOCKS) and all(obj['locks'][k] is False for k in LOCKS)

assert not ZIP.exists() and not SIDECAR.exists() and not VERIFICATION.exists()
assert not (AUDIT/'CHECKPOINT_F3_INT108_FINAL.json').exists()
assert not MANIFEST.exists()
validation = load(ROOT/'VALIDACAO_F3_INT108_COMPLETA.json')
candidate = load(AUDIT/'CHECKPOINT_F3_INT108_CANDIDATO.json')
old_marker_bytes = (AUDIT/'ULTIMO_MARCO.json').read_bytes()
old_marker = json.loads(old_marker_bytes)
assert old_marker['last_completed']=='F3-INT-107' and safety(old_marker)
assert candidate['status']=='CANDIDATO' and safety(candidate)
assert validation['preservation_verified'] is True and validation['locks_verified'] is True
assert safety(validation)
assert candidate['preserved_sha256']==validation['preserved_sha256']

snapshot = validation['preserved_sha256']
for name, sha in snapshot.items():
    assert digest((AUDIT/name).read_bytes())==sha, 'Changed tested file: '+name
python_paths = {p.relative_to(AUDIT).as_posix() for d in ('tools','tests') for p in (AUDIT/d).rglob('*.py')}
tested_python = {Path(n).as_posix() for n in snapshot if n.endswith('.py')}
assert python_paths==tested_python, 'Source inventory changed'
previous_checkpoints = {p.relative_to(AUDIT).as_posix():digest(p.read_bytes()) for p in AUDIT.glob('CHECKPOINT*') if p.is_file()}
evidence = {p.name:digest(p.read_bytes()) for p in ROOT.glob('VALIDACAO_F3_INT108*') if p.is_file()}
evidence['RESULTADO_F3_INT108_COMPLETO.txt'] = digest((ROOT/'RESULTADO_F3_INT108_COMPLETO.txt').read_bytes())

for label, expected in [('NOVOS',16),('REGRESSAO',1293)]:
    result = load(ROOT/f'VALIDACAO_F3_INT108_{label}.json')
    assert result==validation['new_tests' if label=='NOVOS' else 'regression']
    assert result==candidate['new_tests' if label=='NOVOS' else 'regression']
    assert result['approved'] is True and result['total']==result['passed']==expected and result['exit_code']==0
    for key in ('failures','errors','skipped','expected failures','unexpected successes'):
        assert result[key]==0
    log = (ROOT/f'VALIDACAO_F3_INT108_{label}.log').read_text(encoding='utf-8')
    assert len(re.findall(r'^test_.* \.\.\. ok$',log,re.MULTILINE))==expected
    assert re.search(r'Ran '+str(expected)+r' tests in '+re.escape(str(result['unittest_seconds']))+r's\s+OK\s*\Z',log)

scope = '''# F3-INT-109 — escopo preliminar, sem implementação

Base proposta: F3-INT-108 definitivo, F3=OPEN e sete bloqueios false.
Este documento não inicia a etapa nem autoriza uso operacional.

1. Persistência confiável: especificar um armazenamento offline para pins,
   pisos de revisão e consumo; separar estados preparados e confirmados;
   modelar interrupções antes/depois de cada gravação, recuperação e corrupção.
   Avaliar durabilidade real do backend escolhido; arquivo JSON e hash isolados
   não comprovam persistência confiável.
2. Restauração de estados antigos: demonstrar rollback conjunto de cadeia,
   pin, piso e histórico. Definir uma âncora independente do estado restaurável
   e explicitar o que acontece se essa âncora também puder ser restaurada.
   Contador local, versão ou hash dentro do mesmo backup não impedem rollback.
3. Consumo atômico: especificar transação que valide a referência esperada,
   rejeite consumo anterior, registre o consumo e avance o piso em uma unidade.
   Modelar dois consumidores, reinício, commit perdido, repetição e idempotência.
   Bloqueio apenas em memória ou check-then-write não garante exclusão durável.
4. Autenticação de origem: separar integridade de autenticidade. Definir ameaça,
   confiança na distribuição dos pins, identidade, gestão de chaves, revogação
   e verificação independente antes de avaliar qualquer mecanismo futuro.
   Hash, cadeia e assinatura autodeclarada não estabelecem origem confiável.

Critérios propostos: primeiro reproduzir falhas offline; depois criar testes
positivos/adversariais de reinício, crash, concorrência, rollback e corrupção;
preservar contratos 105–108; registrar limites do modelo e regressão completa.
Nenhuma persistência real, autenticação ou consumo atômico foi implementado
nesta consolidação. Sem Profit, Excel, RTD, DDE, corretora ou ordens.
F3 permanece OPEN. orders_allowed, live_certified, flow_complete, f3_resolved,
native_prototype_authorized, strict_deadline_guaranteed e
authenticated_witness_verified permanecem false.
'''
(AUDIT/'ESCOPO_F3_INT109_PRELIMINAR.md').write_text(scope,encoding='utf-8')
archive_marker = AUDIT/'HISTORICO_ULTIMO_MARCO_F3_INT107.json'
assert not archive_marker.exists()
archive_marker.write_bytes(old_marker_bytes)
final = dict(validation)
final.update(last_completed='F3-INT-108',status='OFFLINE_REGRESSION_APPROVED',
             previous_definitive='F3-INT-107',definitive_last_completed='F3-INT-108',
             definitive_marker_updated=True,
             next_step='F3-INT-109: escopo preliminar documentado; implementacao nao iniciada',
             validation_evidence_sha256=evidence,
             consolidated_source_sha256={name:snapshot[name] for name in snapshot if name.endswith('.py')},
             pending=['Persistencia confiavel, resistencia a rollback, consumo atomico e autenticacao de origem nao demonstrados.',
                      'Hashes verificam integridade contra referencias fornecidas; nao autenticam origem.',
                      'Sem certificacao operacional ou autorizacao de operacoes reais.'])
assert safety(final)
write_json(AUDIT/'CHECKPOINT_F3_INT108_FINAL.json',final)
(AUDIT/'CHECKPOINT_F3_INT108_FINAL.md').write_text('''# F3-INT-108 — definitivo offline

16/16 testes novos: zero falhas, erros ou skips; unittest 72,225 s; exit 0.
1293/1293 testes na descoberta completa: zero falhas, erros ou skips;
unittest 717,387 s; subprocess 719,938 s; exit 0.
Tempo total da validação: 795,876 s.

Os 330 hashes do snapshot de validação foram reconferidos antes da promoção.
Todos os 186 arquivos Python em tools/ e tests/ correspondem exatamente ao
inventário testado, sem adições ou remoções. Nenhuma alteração de código.
As evidências originais e o checkpoint candidato permanecem preservados.
Histórico do marcador anterior: HISTORICO_ULTIMO_MARCO_F3_INT107.json.
Os checkpoints anteriores não foram modificados.

F3=OPEN; sete bloqueios false. Auditoria offline, sem certificação operacional.
F3-INT-109 possui somente escopo preliminar; implementação não iniciada.
''',encoding='utf-8')
write_json(AUDIT/'ULTIMO_MARCO.json',final)
assert all(digest((AUDIT/n).read_bytes())==h for n,h in previous_checkpoints.items())
assert all(digest((AUDIT/n).read_bytes())==h for n,h in snapshot.items() if n!='ULTIMO_MARCO.json')
assert digest(archive_marker.read_bytes())==snapshot['ULTIMO_MARCO.json']
assert all(digest((ROOT/n).read_bytes())==h for n,h in evidence.items())

consolidation = dict(stage='F3-INT-108',status='DEFINITIVO_OFFLINE',
                     checked_validation_snapshot_files=len(snapshot),
                     identical_tested_python_files=len(python_paths),
                     historical_checkpoints_preserved=len(previous_checkpoints),
                     new_tests=validation['new_tests'],regression=validation['regression'],
                     f3='OPEN',offline=True,simulation_only=True,certification=False,
                     locks={k:False for k in LOCKS},
                     f3_int109='ESCOPO_PRELIMINAR_SEM_IMPLEMENTACAO',
                     evidence_sha256=evidence)
write_json(ROOT/'CONSOLIDACAO_F3_INT108_FINAL.json',consolidation)

# Package the entire workspace tree except the archive and post-package receipts.
excluded = {ZIP,SIDECAR,VERIFICATION,MANIFEST}
files = sorted(p for p in ROOT.rglob('*') if p.is_file() and p not in excluded)
assert not any(p.is_symlink() for p in ROOT.rglob('*'))
manifest = {p.relative_to(ROOT).as_posix():digest(p.read_bytes()) for p in files}
write_json(MANIFEST,dict(algorithm='SHA-256',files=manifest,
                       note='O manifesto nao inclui seu proprio hash. ZIP, sidecar e recibo pos-pacote sao externos.'))
files.append(MANIFEST)
with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in files:
        z.write(path,path.relative_to(ROOT).as_posix())
expected = {p.relative_to(ROOT).as_posix():digest(p.read_bytes()) for p in files}
with zipfile.ZipFile(ZIP) as z:
    assert z.testzip() is None
    names = z.namelist()
    assert len(names)==len(set(names))==len(files)
    assert set(names)==set(expected)
    for name in names:
        assert not name.startswith('/') and '..' not in Path(name).parts
        assert digest(z.read(name))==expected[name], name
    embedded = json.loads(z.read(MANIFEST.name))
    assert embedded['files']==manifest
    assert safety(json.loads(z.read('audit/ULTIMO_MARCO.json')))
    assert safety(json.loads(z.read('audit/CHECKPOINT_F3_INT108_FINAL.json')))
    assert json.loads(z.read('audit/ULTIMO_MARCO.json'))['last_completed']=='F3-INT-108'
    assert z.read('audit/HISTORICO_ULTIMO_MARCO_F3_INT107.json')==old_marker_bytes
    assert all(digest(z.read('audit/'+name.replace('\\','/')))==sha for name,sha in snapshot.items() if name.endswith('.py'))
package_hash = digest(ZIP.read_bytes())
SIDECAR.write_text(package_hash+'  '+ZIP.name+'\n',encoding='ascii')
assert SIDECAR.read_text().split()[0]==digest(ZIP.read_bytes())
receipt = dict(package=str(ZIP),file_count=len(files),sha256=package_hash,
               size_bytes=ZIP.stat().st_size,crc_verified=True,
               all_archived_bytes_match_workspace=True,manifest_verified=True,
               exact_tested_python_files_verified=len(python_paths),
               historical_checkpoints_unchanged=True,source_and_tests_unchanged=True,
               definitive_checkpoint='F3-INT-108',f3='OPEN',locks={k:False for k in LOCKS},
               offline=True,simulation_only=True,certification=False,
               f3_int109_implemented=False,
               external_receipts=[SIDECAR.name,VERIFICATION.name])
write_json(VERIFICATION,receipt)
print(json.dumps(receipt,indent=2),flush=True)
