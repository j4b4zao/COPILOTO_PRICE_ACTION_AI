"""Independent replay of controlled observer faults and final handle cleanup."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import auditar_a14_7 as startup
from auditar_a14_8 import canonical,decode

SCENARIOS={
    'test_callback_failure_before_release_still_closes':'fail_before_release',
    'test_callback_failure_after_release_preserves_error':'fail_after_release',
    'test_callback_budget_overrun_prevents_late_read':'over_budget',
}


def check(row,mode):
    errors=[]
    def need(ok,message):
        if not ok: errors.append(message)
    scenario=SCENARIOS.get(row.get('test'))
    need(scenario is not None and row.get('scenario')==scenario,'Scenario mismatch')
    need(type(row.get('optimization')) is int and row['optimization']==mode,'Wrong optimization')
    for key,value in dict(fault_is_controlled=True,f3='OPEN',offline=True,simulation_only=True,
        real_operations_authorized=False,runtime_modified=False,production_api_changed=False,
        strict_deadline_guaranteed=False,authentication_tested=False,durability_tested=False).items():
        need(type(row.get(key)) is type(value) and row.get(key)==value,'Scope changed: '+key)
    need(row.get('observer_error') is None and row.get('close_error') is None and row.get('lock_closed') is True,
         'Unexpected observer/close failure')
    native=row.get('native') or {}
    errors.extend('Native proof: '+error for error in startup.check(native,mode))
    expected=native.get('result') or {}
    need(expected.get('mode')=='success','Wrong native startup control')
    raw=base64.b64decode(row['original_base64'],validate=True)
    after=base64.b64decode(row['post_close_base64'],validate=True)
    need(raw==after and hashlib.sha256(raw).hexdigest()==row.get('sha256'),'Post-close bytes/hash differ')
    need(canonical(decode(raw))==canonical(expected),'Disk content differs from pipe control')
    need(type(row.get('win32_denial')) is int and row['win32_denial']==32,'Missing genuine share violation')
    times=row.get('timings') or {}
    callbacks=row.get('callbacks') or []
    need(len(callbacks)==1,'Expected exactly one denial callback')
    callback=callbacks[0] if callbacks else {}
    error=callback.get('error') or {}
    need(error.get('type')=='PermissionError' and error.get('errno')==13
         and (error.get('winerror') is None or type(error.get('winerror')) is int),'Original Python denial lost')
    chronology=[native.get('outer_cleanup_finished_ns'),times.get('original_read_ns'),times.get('lock_acquired_ns'),
        times.get('reader_started_ns'),callback.get('started_ns'),callback.get('finished_ns'),
        times.get('reader_finished_ns'),times.get('finally_started_ns'),times.get('post_close_read_ns')]
    need(all(type(t) is int and t>0 for t in chronology)
         and all(a<=b for a,b in zip(chronology,chronology[1:])),'Native cleanup/callback/finally ordering invalid')
    releasing,released=times.get('release_started_ns'),times.get('release_finished_ns')
    need(type(releasing) is int and type(released) is int and releasing<=released<=times.get('post_close_read_ns',0),
         'Handle release not completed before post-close read')
    result=row.get('reader')
    failure=row.get('callback_error')
    if scenario=='over_budget':
        result=result or {}
        need(failure is None,'Budget overrun misclassified as callback exception')
        need(result.get('status')=='JOURNAL_READ_DENIED' and result.get('verification') is None,
             'Late read accepted/manufactured verification')
        need(result.get('strict_deadline_guaranteed') is False and result.get('production_api_changed') is False,
             'Retry budget/API scope changed')
        attempts=result.get('attempts') or []
        need(len(attempts)==1,'Reader made a late retry after callback overrun')
        attempt=attempts[0] if attempts else {}
        need(attempt.get('error')==error and result.get('error')==error,'Last original denial lost')
        start,deadline,finish=(result.get(k) for k in ('started_ns','deadline_ns','finished_ns'))
        need(all(type(t) is int and t>0 for t in (start,deadline,finish)) and deadline-start==100_000_000,
             'Retry budget changed')
        need(times['reader_started_ns']<=start<=attempt.get('started_ns',0)<=attempt.get('finished_ns',0)
             <=callback.get('started_ns',0)<=releasing<=released<=callback.get('finished_ns',0)<=finish
             <=times['reader_finished_ns'] and released>=deadline,'Budget/attempt/release ordering invalid')
    else:
        failure=failure or {}
        need(result is None and failure.get('type')=='RuntimeError'
             and failure.get('message')=='A14_10_CONTROLLED_CALLBACK_FAILURE','Controlled callback exception lost')
        need(type(failure.get('observed_ns')) is int
             and callback.get('finished_ns',0)<=failure['observed_ns']<=times.get('reader_finished_ns',0),
             'Callback exception timestamp invalid')
        if scenario=='fail_before_release':
            need(times.get('finally_started_ns',0)<=releasing,'Handle released before intended finally path')
        else:
            need(callback.get('started_ns',0)<=releasing<=released<=callback.get('finished_ns',0),
                 'Release did not precede callback failure')
    return errors


def audit(root,modes=(0,1)):
    files,failures,nonces,identities=[],[],set(),set()
    for mode in modes:
        names=[]
        for path in sorted(Path(root).glob(f'a14_10_observer_evidence_O{mode}_*/*.json')):
            try:
                row=json.loads(path.read_bytes()); errors=check(row,mode); names.append(row.get('test'))
                native=row.get('native') or {}; nonce=native.get('nonce'); ident=native.get('probe_identity') or {}
                pair=(ident.get('pid'),ident.get('creation_100ns'))
                if nonce in nonces or pair in identities: errors.append('Native specimen reused')
                nonces.add(nonce); identities.add(pair)
            except (ValueError,TypeError,KeyError,AttributeError) as error: errors=['Malformed record: '+repr(error)]
            failures.extend(str(path)+': '+error for error in errors)
            files.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if len(names)!=3 or set(names)!=set(SCENARIOS): failures.append(f'O{mode}: expected three distinct observer scenarios')
    return dict(accepted=not failures,files=files,records=len(files),failures=failures,
                scope='Controlled callback failure and retry-budget overrun after native cleanup; no operational promotion')


if __name__=='__main__':
    result=audit(sys.argv[1]); print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['accepted'] else 1)
