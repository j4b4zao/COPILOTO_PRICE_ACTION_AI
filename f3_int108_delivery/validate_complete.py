"""Run only the isolated audit suites; preserve definitive checkpoints."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(r'C:\COPILOTO_F3_INT108')
AUDIT = ROOT / 'audit'
LOCKS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed',
         'authenticated_witness_verified')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot():
    files = list((AUDIT/'tools').rglob('*.py')) + list((AUDIT/'tests').rglob('*.py'))
    files += list(AUDIT.glob('CHECKPOINT*')) + [AUDIT/'ULTIMO_MARCO.json']
    return {str(p.relative_to(AUDIT)):sha(p) for p in files if p.is_file()}

def run_suite(name, args):
    log = ROOT / (name + '.log')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=str(AUDIT)+os.pathsep+str(AUDIT/'tests'))
    command = [sys.executable, '-B', '-m', 'unittest', *args]
    start = time.monotonic()
    print('START '+name, flush=True)
    with log.open('w', encoding='utf-8') as stream:
        process = subprocess.run(command, cwd=AUDIT, env=env,
                                 stdout=stream, stderr=subprocess.STDOUT)
    elapsed = time.monotonic()-start
    output = log.read_text(encoding='utf-8')
    summary = re.search(r'Ran (\d+) tests? in ([\d.]+)s', output)
    counts = {key:0 for key in ('failures','errors','skipped','expected failures','unexpected successes')}
    for key in counts:
        match = re.search(re.escape(key)+r'=(\d+)', output)
        if match:
            counts[key] = int(match.group(1))
    total = int(summary[1]) if summary else None
    passed = len(re.findall(r'^test_.* \.\.\. ok$', output, re.MULTILINE))
    result = dict(command=command, cwd=str(AUDIT), total=total, passed=passed,
                  **counts, seconds=round(elapsed,3),
                  unittest_seconds=float(summary[2]) if summary else None,
                  exit_code=process.returncode, log=str(log))
    result['approved'] = (process.returncode == 0 and total is not None
                          and passed == total and all(v==0 for v in counts.values()))
    (ROOT/(name+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
    return result

started = time.monotonic()
before = snapshot()
state = json.loads((AUDIT/'ULTIMO_MARCO.json').read_text(encoding='utf-8'))
assert state['last_completed']=='F3-INT-107'
assert state['f3']=='OPEN' and all(state['locks'][key] is False for key in LOCKS)
prior = json.loads((AUDIT/'preserved_sha256.json').read_text())
assert all(sha(AUDIT/key)==digest for key,digest in prior.items())
new = run_suite('VALIDACAO_F3_INT108_NOVOS', ['test_f3_int108_typed_chain_guard.ChainGuardTests','-v'])
full = run_suite('VALIDACAO_F3_INT108_REGRESSAO', ['discover','-s','tests','-p','test*.py','-v'])
after = snapshot()
unchanged = before == after
sys.path[:0] = [str(AUDIT),str(AUDIT/'tests')]
from tools.f3_int105_typed_identity_envelope import TypedEnvelope
from tools.f3_int106_typed_batch_manifest import TypedBatchManifest
from tools.f3_int107_typed_batch_chain import ChainResult
from tools.f3_int108_typed_chain_guard import verify_typed_chain, safe_to_promote
results = [TypedEnvelope('CHECK'),TypedBatchManifest('CHECK'),ChainResult('CHECK'),
           verify_typed_chain((),context='audit:A',purpose='check',run_id='run:1',
                              batches=(),expected_digest=None,minimum_revision=0,
                              consumed_chain_digests=frozenset())]
locks_ok = all(r.f3=='OPEN' and all(getattr(r,k) is False for k in LOCKS)
               and safe_to_promote(r) is False for r in results)
current = json.loads((AUDIT/'ULTIMO_MARCO.json').read_text())
locks_ok = locks_ok and current == state
approved = new['approved'] and new['total']==16 and full['approved'] and full['total']==1293 and unchanged and locks_ok
record = dict(stage='F3-INT-108',status='CANDIDATO' if approved else 'VALIDACAO_NAO_APROVADA',
              new_tests=new, regression=full, expected_regression=1293,
              total_elapsed_seconds=round(time.monotonic()-started,3),
              preservation_verified=unchanged, locks_verified=locks_ok,
              preserved_sha256=before, f3='OPEN', locks={k:False for k in LOCKS},
              offline=True,simulation_only=True,certification=False,
              definitive_last_completed='F3-INT-107',definitive_marker_updated=False)
(ROOT/'VALIDACAO_F3_INT108_COMPLETA.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
if approved:
    candidate = dict(record)
    candidate['candidate_stage']='F3-INT-108'
    candidate['pending']=['Revisao e promocao explicita pendentes; ultimo marco definitivo continua F3-INT-107.',
                          'Hashes nao autenticam origem. Persistencia, consumo atomico e fencing reais nao verificados.']
    (AUDIT/'CHECKPOINT_F3_INT108_CANDIDATO.json').write_text(json.dumps(candidate,indent=2),encoding='utf-8')
lines = ['PROJETO: COPILOTO_PRICE_ACTION_AI', 'ETAPA: F3-INT-108 - VALIDACAO INTEGRAL',
         'WORKSPACE: '+str(ROOT), 'STATUS: '+record['status'], '',
         'REVISAO: fachada compativel com INT-105/106/107. Sem alteracao de codigo.',
         'INT-108 delega tipos, ordem, revisoes, filhos e hash a INT-107; INT-106/105 continuam vinculando identidade e escopo.',
         'Pin obrigatorio, piso inclusivo e historico explicito sao restricoes adicionais da nova API.',
         'ChainResult, status de sucesso nao autenticado e sete bloqueios sao preservados.', '']
for title, result in [('NOVOS',new),('REGRESSAO COMPLETA (inclui os 16 novos)',full)]:
    lines += [title, 'Comando: '+' '.join(result['command']), 'Diretorio: '+result['cwd'],
              f"Total: {result['total']}; aprovados: {result['passed']}; falhas: {result['failures']}; erros: {result['errors']}; skips: {result['skipped']}",
              f"Tempo unittest: {result['unittest_seconds']} s; tempo subprocess: {result['seconds']} s; codigo de saida: {result['exit_code']}",
              'Log: '+result['log'],'']
lines += [f"Tempo total de validacao: {record['total_elapsed_seconds']} s.",
          f'Fontes, testes e checkpoints preexistentes inalterados: {unchanged}.',
          f'Estado e bloqueios verificados: {locks_ok}. F3=OPEN.',
          *[key+'=false' for key in LOCKS], '',
          'ARQUIVOS GERADOS: RESULTADO_F3_INT108_COMPLETO.txt; VALIDACAO_F3_INT108_NOVOS.log/.json;',
          'VALIDACAO_F3_INT108_REGRESSAO.log/.json; VALIDACAO_F3_INT108_COMPLETA.json.',
          'Candidato: audit/CHECKPOINT_F3_INT108_CANDIDATO.json.' if approved else 'Candidato nao preparado: verificar logs.',
          'ULTIMO_MARCO.json permanece F3-INT-107. Nenhum checkpoint definitivo modificado.',
          'LIMITES: estado externo restaurado permite replay; sem persistencia confiavel ou consumo atomico.',
          'Hashes nao autenticam origem. Sem certificacao operacional.',
          'Somente testes da auditoria isolada. Sem sistemas operacionais, conectores ou ordens. Sem avanco para F3-INT-109.']
(ROOT/'RESULTADO_F3_INT108_COMPLETO.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('FINAL '+record['status'],flush=True)
sys.exit(0 if approved else 1)
