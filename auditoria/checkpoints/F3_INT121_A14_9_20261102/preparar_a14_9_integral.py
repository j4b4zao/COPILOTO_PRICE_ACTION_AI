import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

workspace=Path(__file__).resolve().parent.parent
source=workspace/'work/a14_9/src'
previous=json.loads((workspace/'outputs/MANIFESTO_A14_8_20261102.json').read_bytes())['files_sha256']
for name,sha in previous.items():
    if hashlib.sha256((source/name).read_bytes()).hexdigest()!=sha: raise SystemExit('Previous source changed: '+name)
names=list(previous)+['f3_int121_a14_9_readback.py','test_f3_int121_a14_9_sharing.py']
manifest=dict(stage='F3-INT-121 A14.9 CANDIDATA',status='REGRESSAO_PENDENTE',
              files_sha256={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in names})
(workspace/'outputs/MANIFESTO_A14_9_CANDIDATA_20261102.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
target=workspace/'work/a14_9_regressao_20261102/src'
if target.exists(): raise SystemExit('Refusing to overwrite regression')
for name in names:
    destination=target/name
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source/name,destination)
print('175 previous files unchanged; 177-file isolated snapshot created',flush=True)
for optimization,label in ((0,'normal'),(1,'otimizado')):
    log=workspace/f'outputs/a14_9_regressao_{label}_20261102.log'
    if log.exists(): raise SystemExit('Refusing to overwrite log')
    print('Starting '+label,flush=True)
    command=[sys.executable]+(['-O'] if optimization else [])+['-B','-m','unittest','discover','-v']
    with log.open('wb') as stream: code=subprocess.call(command,cwd=target,stdout=stream,stderr=subprocess.STDOUT)
    log.with_suffix('.exit.txt').write_text(str(code),encoding='utf-8')
    print(label+' exit='+str(code),flush=True)
