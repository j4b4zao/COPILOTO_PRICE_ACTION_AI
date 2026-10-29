"""Adversarial disposable fixture with a revision floor above history length."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
from dataclasses import replace
WORK=Path(__file__).resolve().parents[2]
ROOT=WORK/'f3_int117_work/audit'
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from tools import f3_int117_sqlite_write_faults as probe
from tools import f3_int109_offline_consumption_store as store
import test_f3_int109_offline_consumption_store as prior

prior.ConsumptionStoreTests.setUpClass()
source=prior.ConsumptionStoreTests
batches=(replace(source.next_batches[0],revision=5000),)
proposed=probe.build_typed_chain(source.segments,**source.scope,batches=batches)
with tempfile.TemporaryDirectory(prefix='audit117_capacity_') as directory:
    path=Path(directory)/'probe.sqlite';original=Path(directory)/'original.sqlite'
    history=[format(i,'064x') for i in range(4096)]
    before=dict(version=1,generation=4096,next_revision=5000,scope=list(source.scope.values()),consumed=history)
    after=dict(before,generation=4097,next_revision=5001,consumed=sorted(history+[proposed.digest]))
    probe.seed(path,before,512);shutil.copy2(path,original)
    if probe.snapshot(path)[0]!=before:raise RuntimeError('Initial state not accepted')
    pins=dict(before_state_digest=store._digest(before),after_state_digest=store._digest(after),expected_chain_digest=proposed.digest)
    original_result=store.consume_chain(original,source.segments,expected_state_digest=pins['before_state_digest'],
        expected_digest=proposed.digest,batches=batches,**source.scope)
    attempt=probe.write_once(path,'normal',before=before,after=after,pins=pins,segments=source.segments,batches=batches,scope=source.scope)
    try:
        probe.snapshot(path)
        state_error=None
    except ValueError as error:
        state_error=str(error)
    result=dict(history_before=4096,history_after=4097,revision_before=5000,revision_after=5001,
        original_status=original_result.status,original_preserved=probe.snapshot(original)[0]==before,
        probe_attempt=attempt,reopen_error=state_error,
        scope='Direct write_once call outside bounded run_experiment fixtures')
result['fixture_removed']=not Path(directory).exists()
if result['original_status']!='HISTORY_CAPACITY_EXHAUSTED' or not result['probe_attempt']['committed'] or not state_error:
    raise RuntimeError('Counterexample not reproduced')
output=Path(__file__).with_name('DIFERENCA_CAPACIDADE_REVISAO5000.json')
output.write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
