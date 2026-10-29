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
OUT=AUDIT/'LOG_F3_INT109_ESPECIFICOS.txt'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',
         PYTHONPATH=str(AUDIT)+os.pathsep+str(AUDIT/'tests'))
command=[sys.executable,'-B','-m','unittest',
         'test_f3_int109_offline_consumption_store.ConsumptionStoreTests',
         'test_f3_int108_typed_chain_guard.ChainGuardTests','-v']
start=time.monotonic()
with OUT.open('w',encoding='utf-8') as log:
    run=subprocess.run(command,cwd=AUDIT,env=env,stdout=log,stderr=subprocess.STDOUT)
elapsed=time.monotonic()-start
log=OUT.read_text(encoding='utf-8')
summary=re.search(r'Ran (\d+) tests in ([\d.]+)s',log)
passed=len(re.findall(r'^test_.* \.\.\. ok$',log,re.MULTILINE))
new_passed=len(re.findall(r'^test_.*\(test_f3_int109_offline_consumption_store\..* \.\.\. ok$',log,re.MULTILINE))
counts={key:0 for key in ('failures','errors','skipped','expected failures','unexpected successes')}
for key in counts:
    found=re.search(re.escape(key)+r'=(\d+)',log)
    if found: counts[key]=int(found[1])
snapshot=json.loads((AUDIT/'preserved_before.json').read_text())
unchanged=all(hashlib.sha256((AUDIT/name).read_bytes()).hexdigest()==sha for name,sha in snapshot.items())
state=json.loads((AUDIT/'ULTIMO_MARCO.json').read_text())
locks_ok=state['f3']=='OPEN' and len(state['locks'])==7 and all(x is False for x in state['locks'].values())
record=dict(stage='F3-INT-109',status='CANDIDATO',command=command,total=int(summary[1]) if summary else None,
            passed=passed,new_passed=new_passed,**counts,exit_code=run.returncode,
            seconds=round(elapsed,3),unittest_seconds=float(summary[2]) if summary else None,
            previous_files_unchanged=unchanged,definitive_last_completed=state['last_completed'],
            definitive_marker_updated=False,f3='OPEN',locks=state['locks'],offline=True,
            simulation_only=True,certification=False,full_regression_executed=False,
            source_sha256={name:hashlib.sha256((AUDIT/name).read_bytes()).hexdigest() for name in
                           ('tools/f3_int109_offline_consumption_store.py','tests/test_f3_int109_offline_consumption_store.py',
                            'reproduce_f3_int109_before.py')})
approved=(run.returncode==0 and summary and passed==int(summary[1]) and all(v==0 for v in counts.values())
          and unchanged and locks_ok and state['last_completed']=='F3-INT-108')
record['approved']=bool(approved)
if not approved: record['status']='VALIDACAO_NAO_APROVADA'
(AUDIT/'RESULTADO_F3_INT109_ESPECIFICOS.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
if approved:
    record['pending']=['Regressao historica completa ainda nao executada nesta etapa.',
                       'Ancora externa e SQLite nao possuem commit distribuido; perda de confirmacao exige reconciliacao.',
                       'Rollback conjunto de banco e ancora continua possivel.',
                       'Durabilidade de hardware, origem, fencing e autenticacao reais nao demonstrados.']
    (AUDIT/'CHECKPOINT_F3_INT109_CANDIDATO.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2),flush=True)
sys.exit(0 if approved else 1)
