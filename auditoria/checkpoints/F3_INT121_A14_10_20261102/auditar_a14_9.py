"""Replay genuine share-denial records without importing candidate readers."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import auditar_a14_7 as startup
from auditar_a14_8 import canonical,decode

SCENARIOS={
    'test_transient_real_sharing_denial_recovers':'transient_valid',
    'test_persistent_real_sharing_denial_is_not_missing':'persistent',
    'test_missing_journal_is_not_sharing_denial':'missing',
    'test_corrupt_journal_after_release_still_rejected':'transient_corrupt',
}


def check(row,mode):
    errors=[]
    def need(ok,message):
        if not ok: errors.append(message)
    scenario=SCENARIOS.get(row.get('test'))
    need(scenario is not None and row.get('scenario')==scenario,'Scenario mismatch')
    need(type(row.get('optimization')) is int and row['optimization']==mode,'Wrong optimization')
    for key,value in dict(f3='OPEN',offline=True,simulation_only=True,real_operations_authorized=False,
        runtime_modified=False,production_api_changed=False,authentication_tested=False,durability_tested=False).items():
        need(type(row.get(key)) is type(value) and row.get(key)==value,'Scope changed: '+key)
    need(row.get('observer_error') is None and row.get('lock_close_error') is None
         and row.get('lock_closed') is True,'Observer/handle cleanup failed')
    native=row.get('native') or {}
    errors.extend('Native proof: '+error for error in startup.check(native,mode))
    expected=native.get('result') or {}
    need(expected.get('mode')=='success','Wrong native startup control')
    raw=base64.b64decode(row['original_base64'],validate=True)
    need(hashlib.sha256(raw).hexdigest()==row.get('original_sha256'),'Original hash mismatch')
    need(canonical(decode(raw))==canonical(expected),'Original differs from pipe record')
    captured=base64.b64decode(row['captured_base64'],validate=True) if row.get('captured_base64') is not None else None
    result=row.get('reader') or {}
    times=row.get('timings') or {}
    started,deadline,finished=(result.get(k) for k in ('started_ns','deadline_ns','finished_ns'))
    original_start=times.get('original_read_started_ns')
    native_finish=native.get('outer_cleanup_finished_ns')
    need(all(type(t) is int and t>0 for t in (native_finish,original_start,started,deadline,finished))
         and native_finish<=original_start<=started<deadline and started<=finished,'Invalid cleanup/read budget ordering')
    need(result.get('strict_deadline_guaranteed') is False and result.get('production_api_changed') is False,
         'Retry budget promoted to strict guarantee/API')
    need(deadline-started==(150_000_000 if scenario=='persistent' else 500_000_000),'Retry budget changed')
    attempts=result.get('attempts') or []
    need(bool(attempts),'No real read attempts')
    previous=started
    for attempt in attempts:
        begin,end=attempt.get('started_ns'),attempt.get('finished_ns')
        need(type(begin) is int and type(end) is int and previous<=begin<=end<=finished
             and begin<deadline,'Attempt outside retry budget/order')
        previous=end
    status={'transient_valid':'CONTENT_MATCH','transient_corrupt':'CONTENT_MISMATCH',
            'persistent':'JOURNAL_READ_DENIED','missing':'JOURNAL_MISSING'}.get(scenario)
    need(result.get('status')==status,'Denied/missing/content statuses conflated')
    if scenario=='missing':
        need(row.get('win32_denial') is None and set(times)=={'original_read_started_ns'},'Missing file fabricated lock proof')
        need(len(attempts)==1 and (attempts[0].get('error') or {}).get('type')=='FileNotFoundError',
             'Missing file retried or error changed')
        error=result.get('error') or {}
        need(error.get('type')=='FileNotFoundError' and error.get('errno')==2,'Missing-file errno lost')
    else:
        need(type(row.get('win32_denial')) is int and row['win32_denial']==32,'No genuine Win32 sharing violation')
        acquired,probe,releasing,released=(times.get(k) for k in
            ('lock_acquired_ns','win32_probe_started_ns','lock_release_started_ns','lock_release_finished_ns'))
        need(all(type(t) is int and t>0 for t in (acquired,probe,releasing,released))
             and original_start<=acquired<=probe<=started and acquired<=releasing<=released,
             'Invalid lock lifetime')
        denied=[a for a in attempts if a.get('error') is not None]
        need(bool(denied),'Real Python denial never observed')
        for attempt in denied:
            error=attempt.get('error') or {}
            need(error.get('type')=='PermissionError' and error.get('errno')==13
                 and (error.get('winerror') is None or type(error.get('winerror')) is int),
                 'Python denial errno/type changed')
        if scenario=='persistent':
            need(len(denied)==len(attempts) and finished>=deadline and releasing>=finished,
                 'Persistent lock released early or deadline not exhausted')
            need(result.get('error')==(attempts[-1].get('error') if attempts else None),'Last denial lost')
        else:
            need(len(attempts)>=2 and len(denied)==len(attempts)-1
                 and attempts[-1].get('error') is None and result.get('error') is None,
                 'Transient recovery lacks failed and successful attempts')
            need(bool(denied) and denied[0]['finished_ns']<=releasing<=released<=attempts[-1]['started_ns'],
                 'Read succeeded before lock release')
    verification=result.get('verification')
    if scenario in ('persistent','missing'):
        need(captured is None and verification is None,'Read failure manufactured content verification')
    else:
        verification=verification or {}
        need(captured is not None,'Successful read bytes missing')
        if captured is not None:
            target=json.loads(json.dumps(expected))
            if scenario=='transient_corrupt': target['nonce']='0'*32
            need(canonical(decode(captured))==canonical(target),'Captured payload differs from declared scenario')
            if scenario=='transient_valid': need(captured==raw,'Valid bytes changed')
            need(verification.get('sha256')==hashlib.sha256(captured).hexdigest()
                 and type(verification.get('size')) is int and verification['size']==len(captured),'Captured hash/size mismatch')
        need(verification.get('accepted') is (scenario=='transient_valid') and verification.get('reason')==status,
             'Corrupt content accepted or valid content rejected')
    return errors


def audit(root,modes=(0,1)):
    files,failures,nonces,identities=[],[],set(),set()
    for mode in modes:
        names=[]
        for path in sorted(Path(root).glob(f'a14_9_sharing_evidence_O{mode}_*/*.json')):
            try:
                row=json.loads(path.read_bytes())
                errors=check(row,mode)
                names.append(row.get('test'))
                native=row.get('native') or {}
                nonce=native.get('nonce')
                identity=native.get('probe_identity') or {}
                pair=(identity.get('pid'),identity.get('creation_100ns'))
                if nonce in nonces or pair in identities: errors.append('Reused native specimen')
                nonces.add(nonce); identities.add(pair)
            except (ValueError,TypeError,KeyError,AttributeError) as error:
                errors=['Malformed record: '+repr(error)]
            failures.extend(str(path)+': '+error for error in errors)
            files.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if len(names)!=4 or set(names)!=set(SCENARIOS): failures.append(f'O{mode}: expected four distinct sharing scenarios')
    return dict(accepted=not failures,files=files,records=len(files),failures=failures,
                scope='Real share denial and retry budget after native cleanup; no strict realtime/durability/authentication claim')


if __name__=='__main__':
    result=audit(sys.argv[1])
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['accepted'] else 1)
