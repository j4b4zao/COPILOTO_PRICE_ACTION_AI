"""Prove verbose unittest prefixes preserve all existing evidence checks."""
import importlib.util
import json
from pathlib import Path
import tempfile

def module(name):
    spec=importlib.util.spec_from_file_location(name,'outputs/'+name+'.py')
    loaded=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded
base=module('auditar_regressao')
held=module('auditar_a14_6_retencao')
checks=[]
with tempfile.TemporaryDirectory(dir='work',prefix='verbose_parser_') as directory:
    logs=[]
    for mode,label in enumerate(('normal','otimizado')):
        original=Path(f'outputs/a14_6_r2_regressao_{label}.log')
        text=original.read_text(encoding='utf-8-sig')
        verbose='\n'.join(('test_example (Example.test_example) ... '+line)
                          if '_EVIDENCE=' in line else line for line in text.splitlines())+'\n'
        path=Path(directory)/(label+'.log')
        path.write_text(verbose,encoding='utf-8')
        path.with_suffix('.exit.txt').write_text('0',encoding='utf-8')
        logs.append(path)
        replay=base.audit(path,mode,192)
        if not replay['accepted']:
            raise RuntimeError(replay)
        checks.append(dict(mode=mode,verbose_log_accepted=True))
    result=held.audit('work/a14_6_r2_regressao/work',logs)
    if not result['accepted']:
        raise RuntimeError(result)
    checks.append(dict(held_bridge_and_natural_observations_accepted=True))
Path('outputs/A14_7_VERIFICACAO_PARSER_20261102.json').write_text(json.dumps(dict(
    scope='Synthetic formatting transformations of old validated logs, not project tests',checks=checks),indent=2),encoding='utf-8')
print('Verbose prefixes accepted with all previous evidence checks preserved')
