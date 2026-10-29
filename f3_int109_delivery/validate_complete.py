"""Validation only: never edit source, candidate or definitive checkpoints."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

ROOT=Path(r'C:\COPILOTO_F3_INT108')
AUDIT=ROOT/'audit'
LOCKS=('orders_allowed','live_certified','flow_complete','f3_resolved',
       'native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot():
    paths=list((AUDIT/'tools').rglob('*.py'))+list((AUDIT/'tests').rglob('*.py'))
    paths+=list(AUDIT.glob('CHECKPOINT*'))+[AUDIT/'ULTIMO_MARCO.json']
    return {p.relative_to(AUDIT).as_posix():sha(p) for p in paths if p.is_file()}

def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def run_suite(label,args):
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',
             PYTHONPATH=str(AUDIT)+os.pathsep+str(AUDIT/'tests'))
    command=[sys.executable,'-B','-m','unittest',*args]
    log_path=ROOT/f'VALIDACAO_F3_INT109_{label}.log'
    start=time.monotonic()
    print('START '+label,flush=True)
    with log_path.open('w',encoding='utf-8') as log:
        process=subprocess.run(command,cwd=AUDIT,env=env,stdout=log,stderr=subprocess.STDOUT)
    elapsed=time.monotonic()-start
    output=log_path.read_text(encoding='utf-8')
    summary=re.search(r'Ran (\d+) tests? in ([\d.]+)s',output)
    counts={k:0 for k in ('failures','errors','skipped','expected failures','unexpected successes')}
    for key in counts:
        found=re.search(re.escape(key)+r'=(\d+)',output)
        if found: counts[key]=int(found[1])
    passed=len(re.findall(r'^test_.* \.\.\. ok$',output,re.MULTILINE))
    total=int(summary[1]) if summary else None
    result=dict(command=command,cwd=str(AUDIT),total=total,passed=passed,**counts,
                unittest_seconds=float(summary[2]) if summary else None,
                seconds=round(elapsed,3),exit_code=process.returncode,log=str(log_path),
                log_sha256=sha(log_path),resource_warning_count=output.count('ResourceWarning:'))
    result['approved']=process.returncode==0 and total is not None and total==passed and all(v==0 for v in counts.values())
    write_json(ROOT/f'VALIDACAO_F3_INT109_{label}.json',result)
    print(json.dumps(result),flush=True)
    return result

started=time.monotonic()
before=snapshot()
state=json.loads((AUDIT/'ULTIMO_MARCO.json').read_text())
candidate=json.loads((AUDIT/'CHECKPOINT_F3_INT109_CANDIDATO.json').read_text())
assert state['last_completed']=='F3-INT-108' and state['f3']=='OPEN'
assert len(state['locks'])==7 and all(state['locks'][k] is False for k in LOCKS)
assert candidate['status']=='CANDIDATO' and candidate['stage']=='F3-INT-109'
assert all(sha(AUDIT/path)==digest for path,digest in candidate['source_sha256'].items())
assert all(sha(AUDIT/path)==digest for path,digest in state['consolidated_source_sha256'].items())
new=run_suite('NOVOS',['test_f3_int109_offline_consumption_store.ConsumptionStoreTests','-v'])
full=run_suite('REGRESSAO',['discover','-s','tests','-p','test*.py','-v'])
unchanged=before==snapshot()
sys.path[:0]=[str(AUDIT),str(AUDIT/'tests')]
from tools.f3_int105_typed_identity_envelope import TypedEnvelope
from tools.f3_int106_typed_batch_manifest import TypedBatchManifest
from tools.f3_int107_typed_batch_chain import ChainResult
from tools.f3_int109_offline_consumption_store import StoreResult,safe_to_promote,consume_chain
objects=[TypedEnvelope('CHECK'),TypedBatchManifest('CHECK'),ChainResult('CHECK'),StoreResult('CHECK'),
         consume_chain('unused.sqlite',(),expected_state_digest=None,expected_digest=None,
                       context='audit:A',purpose='review',run_id='run:1',batches=())]
locks_ok=all(obj.f3=='OPEN' and all(getattr(obj,k) is False for k in LOCKS) and safe_to_promote(obj) is False for obj in objects)
assert json.loads((AUDIT/'ULTIMO_MARCO.json').read_text())==state
assert json.loads((AUDIT/'CHECKPOINT_F3_INT109_CANDIDATO.json').read_text())==candidate
approved=new['approved'] and new['total']==29 and full['approved'] and full['total']==1322 and unchanged and locks_ok
record=dict(stage='F3-INT-109',status='CANDIDATO_REVISAO_FINAL_PENDENTE' if approved else 'VALIDACAO_NAO_APROVADA',
            approved=approved,new_tests=new,regression=full,expected_total=1322,
            total_seconds=round(time.monotonic()-started,3),source_and_checkpoints_unchanged=unchanged,
            preserved_sha256=before,locks_verified=locks_ok,f3='OPEN',locks={k:False for k in LOCKS},
            definitive_last_completed='F3-INT-108',definitive_marker_updated=False,candidate_updated=False,
            offline=True,simulation_only=True,certification=False,
            python_version=sys.version,sqlite_version=sqlite3.sqlite_version)
write_json(ROOT/'VALIDACAO_F3_INT109_COMPLETA.json',record)
lines=['PROJETO: COPILOTO_PRICE_ACTION_AI','ETAPA: F3-INT-109 - REGRESSAO INTEGRAL',
       'WORKSPACE: '+str(ROOT),'STATUS: '+record['status'],'',
       'REVISAO: sem alteracoes de implementacao. Compativel com contratos F3-INT-105 a 108.',
       'StoreResult herda ChainResult e seus sete bloqueios; scope usa LABEL de 105.',
       'Consume delega identidade, lotes, revisoes, pin, piso e historico a 108 -> 107 -> 106 -> 105.',
       'A transacao local publica sucesso somente apos commit; esgotamento e divergencias rejeitam.',
       'Confirmação perdida e rollback conjunto de banco/ancora continuam limitacoes declaradas.','']
for label,result in [('29 TESTES NOVOS',new),('REGRESSAO INTEGRAL (inclui os 29 novos)',full)]:
    lines += [label,'Comando: '+' '.join(result['command']),'Diretorio: '+result['cwd'],
              f"Total: {result['total']}; aprovados: {result['passed']}; falhas: {result['failures']}; erros: {result['errors']}; skips: {result['skipped']}",
              f"Tempo unittest: {result['unittest_seconds']} s; subprocess: {result['seconds']} s; codigo de saida: {result['exit_code']}",
              f"ResourceWarnings: {result['resource_warning_count']}",'Log: '+result['log'],'']
lines += [f"Tempo total de validacao: {record['total_seconds']} s.",
          f'Fontes, testes, candidato e checkpoints definitivos inalterados: {unchanged}.',
          f'Sete bloqueios verificados: {locks_ok}. F3=OPEN.',*[k+'=false' for k in LOCKS],
          'ULTIMO_MARCO.json = F3-INT-108. F3-INT-109 permanece CANDIDATO ate revisao final.',
          'Nenhum checkpoint foi editado nesta execucao.','',
          'ARQUIVOS GERADOS: RESULTADO_F3_INT109_COMPLETO.txt; VALIDACAO_F3_INT109_NOVOS.log/.json;',
          'VALIDACAO_F3_INT109_REGRESSAO.log/.json; VALIDACAO_F3_INT109_COMPLETA.json.',
          'RISCOS: ancora independente deve ser retida; rollback conjunto ainda permite replay;',
          'sem commit distribuido, fencing real, durabilidade de hardware comprovada ou autenticacao de origem.',
          'Hashes nao autenticam origem. Sem certificacao operacional.',
          'Somente auditoria offline: nenhum conector, corretora ou ordem. Sem avanco para F3-INT-110.']
(ROOT/'RESULTADO_F3_INT109_COMPLETO.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('FINAL '+record['status'],flush=True)
sys.exit(0 if approved else 1)
