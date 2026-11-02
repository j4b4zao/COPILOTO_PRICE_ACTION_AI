import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

workspace=Path(__file__).resolve().parent.parent
source=workspace/'work/a14_10/src'
previous=json.loads((workspace/'outputs/MANIFESTO_A14_9_20261102.json').read_bytes())['files_sha256']
for name,sha in previous.items():
    if hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha: raise SystemExit('Previous source changed: '+name)
names=list(previous)+['test_f3_int121_a14_10_observer.py']
manifest=dict(stage='F3-INT-121 A14.10 CANDIDATA',status='REGRESSAO_PENDENTE',
              files_sha256={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in names})
(workspace/'outputs/MANIFESTO_A14_10_CANDIDATA_20261102.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
target=workspace/'work/a14_10_regressao_20261102/src'
if target.exists(): raise SystemExit('Refusing overwrite')
for name in names:
    destination=target/name; destination.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source/name,destination)
print('177 previous files unchanged; 178-file isolated snapshot created',flush=True)
for mode,label in ((0,'normal'),(1,'otimizado')):
    log=workspace/f'outputs/a14_10_regressao_{label}_20261102.log'
    if log.exists(): raise SystemExit('Refusing log overwrite')
    print('Starting '+label,flush=True)
    command=[sys.executable]+(['-O'] if mode else [])+['-B','-m','unittest','discover','-v']
    with log.open('wb') as stream: code=subprocess.call(command,cwd=target,stdout=stream,stderr=subprocess.STDOUT)
    log.with_suffix('.exit.txt').write_text(str(code),encoding='utf-8'); print(label+' exit='+str(code),flush=True)
