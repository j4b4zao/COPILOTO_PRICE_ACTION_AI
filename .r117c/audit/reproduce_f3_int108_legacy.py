"""Run from audit/: python -B reproduce_f3_int108_legacy.py.

Reproduces legacy acceptance, not authentication or a hash collision.
Executed before the guard was implemented; original output retained in report.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'tests'))
from test_f3_int107_typed_batch_chain import TypedBatchChainTests
from tools.f3_int107_typed_batch_chain import ChainBatch
from tools.f3_int106_typed_batch_manifest import TypedBatchEntry

TypedBatchChainTests.setUpClass()
t = TypedBatchChainTests()
a = ChainBatch((TypedBatchEntry('audit', 'x'),), 1)
b = ChainBatch((TypedBatchEntry('report', 'y'),), 2)
c = ChainBatch((TypedBatchEntry('audit', 'z'),), 3)
for label, batches in (
    ('complete', (a,b,c)), ('prefix_removed', (b,c)),
    ('suffix_removed', (a,b)), ('old_replay', (a,)),
    ('middle_replaced', (a,ChainBatch((TypedBatchEntry('report','other'),),2),c)),
    ('identity_replayed_new_revision', (a,ChainBatch(a.entries,2))),
):
    result = t.call(batches=batches)
    print(label, result.status, result.digest, flush=True)
    assert result.status == 'CHAIN_FIXTURE_UNAUTHENTICATED'
