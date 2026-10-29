"""Execute the isolated 110/109/108 suites; preserve definitive checkpoints."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(r'C:\COPILOTO_F3_INT108')
AUDIT=ROOT/'audit'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',
         PYTHONPATH=str(AUDIT)+os.pathsep+str(AUDIT/'tests'))
command=[sys.executable,'-B','-m','unittest',
         'test_f3_int110_confirmed_consumption.ConfirmedConsumptionTests',
         'test_f3_int109_offline_consumption_store.ConsumptionStoreTests',
         'test_f3_int108_typed_chain_guard.ChainGuardTests','-v']
log_path=AUDIT/'LOG_F3_INT110_ESPECIFICOS.txt'
start=time.monotonic()
with log_path.open('w',encoding='utf-8') as log:
    process=subprocess.run(command,cwd=AUDIT,env=env,stdout=log,stderr=subprocess.STDOUT)
elapsed=time.monotonic()-start
output=log_path.read_text(encoding='utf-8')
summary=re.search(r'Ran (\d+) tests in ([\d.]+)s',output)
passed=len(re.findall(r'^test_.* \.\.\. ok$',output,re.MULTILINE))
new_passed=len(re.findall(r'^test_.*\(test_f3_int110_confirmed_consumption\..* \.\.\. ok$',output,re.MULTILINE))
counts={k:0 for k in ('failures','errors','skipped','expected failures','unexpected successes')}
for key in counts:
    match=re.search(re.escape(key)+r'=(\d+)',output)
    if match: counts[key]=int(match[1])
snapshot=json.loads((AUDIT/'PRESERVACAO_F3_INT110.json').read_text())
unchanged=all(hashlib.sha256((AUDIT/name).read_bytes()).hexdigest()==sha for name,sha in snapshot.items())
state=json.loads((AUDIT/'ULTIMO_MARCO.json').read_text())
locks_ok=state['f3']=='OPEN' and len(state['locks'])==7 and all(x is False for x in state['locks'].values())
approved=(process.returncode==0 and summary and int(summary[1])==passed==64 and new_passed==19
          and all(v==0 for v in counts.values()) and unchanged and locks_ok and state['last_completed']=='F3-INT-109')
record=dict(stage='F3-INT-110',status='CANDIDATO' if approved else 'VALIDACAO_NAO_APROVADA',
            approved=bool(approved),command=command,total=int(summary[1]) if summary else None,
            passed=passed,new_passed=new_passed,**counts,exit_code=process.returncode,
            seconds=round(elapsed,3),unittest_seconds=float(summary[2]) if summary else None,
            log_sha256=hashlib.sha256(log_path.read_bytes()).hexdigest(),
            resource_warning_count=output.count('ResourceWarning:'),
            previous_files_unchanged=unchanged,preserved_files=len(snapshot),locks_verified=locks_ok,
            definitive_last_completed=state['last_completed'],definitive_marker_updated=False,
            f3='OPEN',locks=state['locks'],offline=True,simulation_only=True,certification=False,
            full_regression_executed=False,
            source_sha256={name:hashlib.sha256((AUDIT/name).read_bytes()).hexdigest() for name in
                           ('tools/f3_int110_confirmed_consumption.py','tests/test_f3_int110_confirmed_consumption.py',
                            'reproduce_f3_int110_before.py')},
            confirmed_implementation_defect='INT-109 pode confirmar consumo sem persistir UPDATE ignorado/revertido por trigger.',
            correction='Nova fachada exige rowcount=1 e releitura igual ao estado completo esperado antes do commit.',
            pending=['Regressao historica completa da F3-INT-110 ainda nao executada.',
                     'Rollback conjunto, bancos copiados e reconciliacao apos confirmacao perdida continuam limitacoes.',
                     'Durabilidade de hardware, fencing e autenticacao de origem nao demonstrados.',
                     'API legada 109 preservada; usar explicitamente a fachada 110 para a protecao nova.'])
(AUDIT/'RESULTADO_F3_INT110_ESPECIFICOS.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
if approved:
    (AUDIT/'CHECKPOINT_F3_INT110_CANDIDATO.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(record,indent=2),flush=True)
sys.exit(0 if approved else 1)
