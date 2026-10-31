"""Private strict-negative fixture: retain A12 bridge after worker return.

Used only by A14.4 strict ordering probes. A14.5 observational runs continue
using the original natural-return bridge, unchanged on disk.
"""
import json
import os
from pathlib import Path
import sys
import time


def _held_bridge():
    import f3_int121_a12_boundaries as boundaries
    original = boundaries.worker_api.run_worker
    def run_and_retain(database_path, *args, **kwargs):
        root = Path(database_path).parent
        def mark(phase, **fields):
            path = root / ('bridge-retention-' + phase.lower() + '.json')
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(dict(schema='A14_6_HELD_BRIDGE', phase=phase,
                pid=os.getpid(), optimization=sys.flags.optimize, specimen_id=root.name,
                observed_ns=time.perf_counter_ns(), real_operations_authorized=False, **fields)), encoding='utf-8')
            temporary.replace(path)
        mark('ARMED')
        result = original(database_path, *args, **kwargs)
        mark('ACTIVE', worker_status=result.status)
        # No result frame can reach the owner while held, so its normal
        # Peer.close path cannot race the explicit owner-death experiment.
        deadline = time.monotonic() + 60
        while not (root / 'release-held-bridge').exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('A14_6_HELD_BRIDGE_EXPIRED')
            time.sleep(0.02)
        return result
    boundaries.worker_api.run_worker = run_and_retain
    try:
        boundaries._bridge()
    finally:
        boundaries.worker_api.run_worker = original


if __name__ == '__main__':
    if os.name != 'nt' or sys.argv[1:] != ['--held-bridge']:
        raise RuntimeError('Private Windows held-bridge specimen only')
    _held_bridge()
