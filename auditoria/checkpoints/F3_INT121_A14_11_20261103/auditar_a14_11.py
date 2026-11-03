"""Replay first-attempt budget evidence, keeping simulated and real clocks apart."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import auditar_a14_7 as startup
from auditar_a14_8 import canonical,decode

SCENARIOS={
    'test_legacy_counterproof_first_attempt_after_budget':'legacy_late',
    'test_guard_prevents_first_attempt_after_budget':'guard_late',
    'test_guard_prevents_first_attempt_at_deadline':'guard_equal',
    'test_guard_real_clock_valid_journal_control':'real_control',
}
CLOCKS={'legacy_late':[1_000_000,201_000_000,202_000_000,203_000_000],
        'guard_late':[1_000_000,201_000_000,202_000_000],
        'guard_equal':[1_000_000,101_000_000,102_000_000]}


def check(row,mode):
    errors=[]
    def need(ok,message):
        if not ok: errors.append(message)
    scenario=SCENARIOS.get(row.get('test'))
    need(scenario is not None and row.get('scenario')==scenario,'Scenario mismatch')
    need(type(row.get('optimization')) is int and row['optimization']==mode,'Wrong optimization')
    for key,value in dict(f3='OPEN',offline=True,simulation_only=True,real_operations_authorized=False,
        runtime_modified=False,production_api_changed=False,strict_deadline_guaranteed=False,
        authentication_tested=False,durability_tested=False).items():
        need(type(row.get(key)) is type(value) and row.get(key)==value,'Scope changed: '+key)
    need(row.get('observer_error') is None,'Unexpected observer failure')
    native=row.get('native') or {}
    errors.extend('Native proof: '+error for error in startup.check(native,mode))
    expected=native.get('result') or {}
    need(expected.get('mode')=='success','Wrong native startup control')
    original=base64.b64decode(row['original_base64'],validate=True)
    need(hashlib.sha256(original).hexdigest()==row.get('original_sha256'),'Original hash mismatch')
    need(canonical(decode(original))==canonical(expected),'Original journal differs from pipe')
    captured=base64.b64decode(row['captured_base64'],validate=True) if row.get('captured_base64') is not None else None
    legacy=scenario=='legacy_late'
    controlled=scenario in CLOCKS
    guarded=scenario in ('guard_late','guard_equal')
    need(row.get('implementation')==('LEGACY_A14_9' if legacy else 'ISOLATED_A14_11'),'Wrong implementation')
    need(row.get('expected_legacy_violation') is legacy,'Legacy counterproof misrepresented')
    need(row.get('scheduler_delay_simulated') is controlled
         and row.get('clock_mode')==('CONTROLLED' if controlled else 'REAL'),'Simulated clock presented as natural OS delay')
    ticks=row.get('clock_values')
    need(ticks==CLOCKS.get(scenario,[]) and all(type(t) is int for t in ticks),'Controlled clock sequence changed')
    begin,end=row.get('invocation_started_real_ns'),row.get('invocation_finished_real_ns')
    native_end=native.get('outer_cleanup_finished_ns')
    need(all(type(t) is int and t>0 for t in (native_end,begin,end)) and native_end<=begin<=end,
         'Real invocation preceded native cleanup')
    calls=row.get('read_calls') or []
    need(len(calls)==(0 if guarded else 1),'Unexpected actual file read count')
    for call in calls:
        a,b=call.get('started_real_ns'),call.get('finished_real_ns')
        need(type(a) is int and type(b) is int and begin<=a<=b<=end,'File read outside real invocation')
    result=row.get('reader') or {}
    need(result.get('error') is None,'Budget exhaustion fabricated an OS error')
    need(result.get('strict_deadline_guaranteed') is False and result.get('production_api_changed') is False,
         'Retry budget promoted to operational/strict guarantee')
    start,deadline,finish=(result.get(k) for k in ('started_ns','deadline_ns','finished_ns'))
    need(all(type(t) is int for t in (start,deadline,finish)) and deadline-start==100_000_000,
         'Budget changed')
    attempts=result.get('attempts') or []
    if controlled:
        need(start==ticks[0] and finish==ticks[-1],'Controlled result timestamps changed')
    else:
        need(begin<=start<=finish<=end,'Real/synthetic clock domains mixed')
    if not legacy: need(result.get('first_attempt_budget_checked') is True,'New guard not active')
    if guarded:
        need(result.get('status')=='JOURNAL_READ_BUDGET_EXHAUSTED' and captured is None
             and result.get('verification') is None and attempts==[],'Expired first-read budget was not rejected before I/O')
        need(ticks[1]>=deadline and (ticks[1]==deadline if scenario=='guard_equal' else ticks[1]>deadline),
             'Boundary clock does not match scenario')
    else:
        need(result.get('status')=='CONTENT_MATCH' and captured==original,'Valid control/counterproof content missing')
        need(len(attempts)==1,'Expected one actual read attempt')
        attempt=attempts[0] if attempts else {}
        need(attempt.get('error') is None,'Unexpected read failure')
        a,b=attempt.get('started_ns'),attempt.get('finished_ns')
        need(type(a) is int and type(b) is int and start<=a<=b<=finish,'Attempt chronology invalid')
        if legacy: need(a==ticks[1] and b==ticks[2] and a>deadline,'Legacy first-read gap not reproduced')
        else: need(a<deadline and calls[0]['started_real_ns']>=a,'Real control read outside initial budget')
        verification=result.get('verification') or {}
        need(verification.get('accepted') is True and verification.get('reason')=='CONTENT_MATCH'
             and verification.get('sha256')==hashlib.sha256(original).hexdigest()
             and type(verification.get('size')) is int and verification['size']==len(original),'Content verification differs')
    return errors


def audit(root,modes=(0,1)):
    files,failures,nonces,identities=[],[],set(),set()
    for mode in modes:
        names=[]
        for path in sorted(Path(root).glob(f'a14_11_budget_evidence_O{mode}_*/*.json')):
            try:
                row=json.loads(path.read_bytes()); errors=check(row,mode); names.append(row.get('test'))
                native=row.get('native') or {}; nonce=native.get('nonce'); ident=native.get('probe_identity') or {}
                pair=(ident.get('pid'),ident.get('creation_100ns'))
                if nonce in nonces or pair in identities: errors.append('Native specimen reused')
                nonces.add(nonce); identities.add(pair)
            except (ValueError,TypeError,KeyError,AttributeError,IndexError) as error: errors=['Malformed record: '+repr(error)]
            failures.extend(str(path)+': '+error for error in errors)
            files.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if len(names)!=4 or set(names)!=set(SCENARIOS): failures.append(f'O{mode}: expected four first-attempt scenarios')
    return dict(accepted=not failures,files=files,records=len(files),failures=failures,
                scope='Controlled-clock first-attempt gap and isolated guard; separate real-clock control; no strict OS deadline')


if __name__=='__main__':
    result=audit(sys.argv[1]); print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['accepted'] else 1)
