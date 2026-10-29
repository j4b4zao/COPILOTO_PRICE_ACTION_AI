"""Read-only reconciliation; writes supplemental reports only, never repacks ZIP."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(r'C:\COPILOTO_F3_INT108')
AUDIT=ROOT/'audit'
ZIP=ROOT/'PACOTE_AUDITORIA_F3_INT109_FINAL.zip'
LOCKS=('orders_allowed','live_certified','flow_complete','f3_resolved',
       'native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified')

def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8'))

validation=load(ROOT/'VALIDACAO_F3_INT109_COMPLETA.json')
final=load(AUDIT/'CHECKPOINT_F3_INT109_FINAL.json')
snapshot=validation['preserved_sha256']
assert len(snapshot)==336 and final['validated_snapshot_sha256']==snapshot
before=snapshot['ULTIMO_MARCO.json']
current=sha((AUDIT/'ULTIMO_MARCO.json').read_bytes())
differences=[]
for name,expected in snapshot.items():
    actual=sha((AUDIT/name).read_bytes())
    if actual!=expected: differences.append(name)
assert differences==['ULTIMO_MARCO.json']
old_raw=(AUDIT/'HISTORICO_ULTIMO_MARCO_F3_INT108.json').read_bytes()
assert sha(old_raw)==before and old_raw==(AUDIT/'CHECKPOINT_F3_INT108_FINAL.json').read_bytes()
assert (AUDIT/'ULTIMO_MARCO.json').read_bytes()==(AUDIT/'CHECKPOINT_F3_INT109_FINAL.json').read_bytes()
old=json.loads(old_raw)
assert old['last_completed']=='F3-INT-108' and final['last_completed']=='F3-INT-109'
assert final['previous_definitive']=='F3-INT-108' and final['checkpoint_type']=='FINAL'
for state in (old,final):
    assert state['f3']=='OPEN' and state['offline'] is True and state['certification'] is False
    assert set(state['locks'])==set(LOCKS) and all(state['locks'][key] is False for key in LOCKS)
evidence=[]
for name,expected in final['validation_evidence_sha256'].items():
    actual=sha((ROOT/name).read_bytes())
    assert actual==expected
    evidence.append(dict(file=name,expected_sha256=expected,current_sha256=actual,match=True))
log_results=[]
for label,total,key in [('NOVOS',29,'new_tests'),('REGRESSAO',1322,'regression')]:
    result=load(ROOT/f'VALIDACAO_F3_INT109_{label}.json')
    assert result==final[key]==validation[key]
    log_path=ROOT/f'VALIDACAO_F3_INT109_{label}.log'
    actual=sha(log_path.read_bytes())
    assert actual==result['log_sha256']==final['validation_evidence_sha256'][log_path.name]
    text=log_path.read_text(encoding='utf-8')
    assert result['total']==result['passed']==total and result['exit_code']==0
    assert all(result[k]==0 for k in ('failures','errors','skipped'))
    assert len(re.findall(r'^test_.* \.\.\. ok$',text,re.MULTILINE))==total
    assert re.search(r'Ran '+str(total)+r' tests in '+re.escape(str(result['unittest_seconds']))+r's\s+OK\s*\Z',text)
    log_results.append(dict(file=log_path.name,sha256=actual,total=total,passed=total,failures=0,errors=0,skipped=0,exit_code=0))
zip_sha=sha(ZIP.read_bytes())
assert zip_sha=='ce6dd2595655ce71d19ad4f3844d41cab4e058c4662f1b47815330a14ddac3a7'
assert Path(str(ZIP)+'.sha256').read_text().split()[0]==zip_sha
with zipfile.ZipFile(ZIP) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert len(names)==len(set(names))==740
    manifest=json.loads(z.read('MANIFESTO_PACOTE_F3_INT109_FINAL.json'))['files']
    assert len(manifest)==739 and set(manifest)==set(names)-{'MANIFESTO_PACOTE_F3_INT109_FINAL.json'}
    assert manifest['audit/ULTIMO_MARCO.json']==current
    for name,expected in manifest.items():
        assert sha(z.read(name))==expected and sha((ROOT/name).read_bytes())==expected
    for name in names:
        assert z.read(name)==(ROOT/name).read_bytes()
    for name,expected in snapshot.items():
        if name!='ULTIMO_MARCO.json': assert sha(z.read('audit/'+name))==expected
    assert sha(z.read('audit/HISTORICO_ULTIMO_MARCO_F3_INT108.json'))==before
    assert z.read('audit/ULTIMO_MARCO.json')==z.read('audit/CHECKPOINT_F3_INT109_FINAL.json')
    for item in log_results: assert sha(z.read(item['file']))==item['sha256']
changed_keys=sorted(k for k in set(old)|set(final) if old.get(k)!=final.get(k))
record=dict(stage='F3-INT-109',status='INTEGRIDADE_RECONCILIADA',
            snapshot_phase='ANTES_DA_PROMOCAO_DEFINITIVA',snapshot_total=336,
            snapshot_unchanged_files=335,snapshot_differences=['audit/ULTIMO_MARCO.json'],
            previous_marker_sha256=before,current_marker_sha256=current,
            previous_hash_proven_by=['audit/HISTORICO_ULTIMO_MARCO_F3_INT108.json','audit/CHECKPOINT_F3_INT108_FINAL.json'],
            current_hash_proven_by='audit/CHECKPOINT_F3_INT109_FINAL.json',
            marker_changed_keys=changed_keys,
            justification='Substituicao exata do marcador FINAL 108 pelo FINAL 109 aprovado; unica divergencia no snapshot anterior a promocao.',
            evidence=evidence,logs=log_results,
            post_consolidation_manifest_marker_matches=True,
            package=str(ZIP),package_sha256=zip_sha,package_files=740,
            package_crc_verified=True,manifest_entries_verified=739,
            all_archived_files_match_workspace=True,
            definitive_checkpoint='F3-INT-109',f3='OPEN',locks={k:False for k in LOCKS},
            offline=True,certification=False,f3_int110_implemented=False,
            code_tests_checkpoints_manifest_and_zip_modified=False,
            supplementary_report_external_to_original_zip=True)
json_path=ROOT/'RECONCILIACAO_F3_INT109.json'
txt_path=ROOT/'RELATORIO_RECONCILIACAO_F3_INT109.txt'
assert not json_path.exists() and not txt_path.exists()
json_path.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
lines=['PROJETO: COPILOTO_PRICE_ACTION_AI','ETAPA: VERIFICACAO FINAL F3-INT-109',
       'RESULTADO: INTEGRIDADE RECONCILIADA','',
       '1. HASH ANTERIOR DE audit/ULTIMO_MARCO.json',before,
       'Coincide byte a byte com HISTORICO_ULTIMO_MARCO_F3_INT108.json e CHECKPOINT_F3_INT108_FINAL.json.',
       '2. HASH ATUAL DE audit/ULTIMO_MARCO.json',current,
       'Coincide byte a byte com CHECKPOINT_F3_INT109_FINAL.json no workspace e no ZIP.','',
       'JUSTIFICATIVA: o snapshot de 336 arquivos foi capturado antes da promocao definitiva.',
       'Naquele instante, ULTIMO_MARCO.json ainda era F3-INT-108. A consolidacao autorizada',
       'substituiu exatamente esse marcador pelo checkpoint FINAL F3-INT-109, com 1322 testes.',
       'Nao ha mudanca adicional no marcador alem do documento FINAL 109 aprovado.',
       'O hash anterior foi preservado no historico. Campos JSON diferentes: '+', '.join(changed_keys),
       '', 'OUTROS 335 ARQUIVOS: hashes identicos ao snapshot, tanto no workspace quanto no ZIP.',
       'Incluem todos os 188 arquivos Python validados de tools/ e tests/.',
       'As seis evidencias referenciadas no checkpoint FINAL tiveram seus hashes confirmados.','',
       'CONFERENCIA DOS LOGS CONTRA O CHECKPOINT FINAL:']
for item in log_results:
    lines += [item['file'],item['sha256'],
              f"{item['passed']}/{item['total']} aprovados; falhas=0, erros=0, skips=0; exit=0; SHA-256 confere."]
lines += ['', 'MANIFESTOS: validated_snapshot_sha256 documenta o estado anterior a promocao.',
          'MANIFESTO_PACOTE_F3_INT109_FINAL.json documenta os arquivos apos a consolidacao:',
          'seu hash para audit/ULTIMO_MARCO.json coincide com o hash atual.',
          'Portanto, nao e necessario corrigir o snapshot historico ou o manifesto do pacote.',
          'Este relatorio suplementar esclarece a transicao sem reescrever a evidencia original.','',
          'ZIP: '+str(ZIP),'Arquivos: 740; CRC: OK; 739 entradas de manifesto: OK.',
          'Todos os 740 arquivos do ZIP conferem byte a byte com o workspace.',
          'SHA-256 do ZIP (inalterado): '+zip_sha,'Sidecar SHA-256: OK.',
          'Relatorios de reconciliacao externos ao ZIP original; nenhum reempacotamento.','',
          'Estado: F3=OPEN; sete bloqueios false; checkpoint definitivo F3-INT-109.',
          'Nenhum codigo, teste, checkpoint, manifesto ou ZIP foi alterado nesta verificacao.',
          'Nao houve reexecucao dos testes; resultados e logs anteriores foram reconferidos.',
          'Auditoria exclusivamente offline. Nenhuma operacao real ou certificacao operacional.',
          'Hashes verificam integridade, nao autenticam origem. F3-INT-110 nao implementada.']
txt_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(previous=before,current=current,unchanged=335,logs_verified=len(log_results),
                      manifest_entries_verified=len(manifest),zip_sha256=zip_sha,result=record['status']),indent=2),flush=True)
