"""Run the two offline Windows suites sequentially in an isolated snapshot."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

workspace = Path(__file__).resolve().parent.parent
manifest = json.loads((workspace/'outputs/MANIFESTO_A14_7_CANDIDATA_20261031.json').read_bytes())
source = workspace/'work/a14_7/src'
target = workspace/'work/a14_7_regressao_20261102/src'
if target.exists():
    raise SystemExit('Refusing to overwrite existing regression snapshot')
for name, expected in manifest['files_sha256'].items():
    if hashlib.sha256((source/name).read_bytes()).hexdigest() != expected:
        raise SystemExit('Source hash mismatch: '+name)
for name in manifest['files_sha256']:
    destination = target/name
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source/name,destination)
print('Verified and copied '+str(len(manifest['files_sha256']))+' source files',flush=True)
for mode,label in ((0,'normal'),(1,'otimizado')):
    log = workspace/f'outputs/a14_7_regressao_{label}_20261102.log'
    if log.exists():
        raise SystemExit('Refusing to overwrite existing log')
    command = [sys.executable]+(['-O'] if mode else [])+['-B','-m','unittest','discover','-v']
    print('Starting '+label,flush=True)
    with log.open('wb') as stream:
        code = subprocess.call(command,cwd=target,stdout=stream,stderr=subprocess.STDOUT)
    log.with_suffix('.exit.txt').write_text(str(code),encoding='utf-8')
    print(label+' exit='+str(code),flush=True)
print('Both modes completed; audit raw evidence before promotion',flush=True)
