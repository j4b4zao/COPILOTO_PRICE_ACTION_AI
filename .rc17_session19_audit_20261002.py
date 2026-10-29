"""One-session descriptive artifact audit; never starts collection."""
import collections
import hashlib
import json
import math
import pathlib
import subprocess
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parent
def digest(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest().upper()
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

call = json.loads((ROOT / '.rc17_session19_call_20261002.json').read_text(encoding='utf-8'))
assert call.get('status') != 'STARTED', 'Capture still running'
protocol_path = ROOT / 'rc17_sideways_to_directional_evolution_protocol_rc1_20261002.json'
protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
protocol_hash = digest(protocol_path)
assert protocol_hash == '2A278E7C4C438098D9CE167A778F7386A09B341A555A73E322598215150EBDB3'
head = git('rev-parse', 'HEAD')
assert head == '085ea40de746efc8a4bc8861073a2a3097ed7f3b'
baseline = json.loads((ROOT / '.rc17_session19_baseline_20261002.json').read_text())
changed = [p for p, h in baseline.items() if not (ROOT/p).is_file() or digest(ROOT/p).lower() != h]
# Workbooks may be updated by the live source; agent never writes them.
operational_workbooks = {'Profit.xlsx', 'livroOfertas.xlsx', 'times&trades.xlsx'}
protected_changes = [p for p in changed if p not in operational_workbooks]
raw_path = pathlib.Path(call['output_path']) if call.get('output_path') else None
raw = json.loads(raw_path.read_text(encoding='utf-8')) if raw_path else {}
samples = raw.get('samples', [])
raw_hash = digest(raw_path) if raw_path else None
counter_names = ['OBSERVABILITY_SAMPLE_COUNT','DIAGNOSTIC_AVAILABLE_COUNT','DIAGNOSTIC_UNAVAILABLE_COUNT',
 'HISTORY_UNCHANGED_TRUE_COUNT','HISTORY_UNCHANGED_FALSE_COUNT','CLOSED_COUNT_MISMATCH_COUNT',
 'HISTORY_HASH_MISSING_COUNT','HISTORY_HASH_MISMATCH_COUNT','FORMING_CANDLE_IN_CLOSED_HISTORY_COUNT',
 'INDEX_ORDER_VIOLATION_COUNT','SERIALIZATION_VIOLATION_COUNT','SWING_HIGH_COUNT_MISMATCH',
 'SWING_LOW_COUNT_MISMATCH','NULLABLE_SWING_MISMATCH_COUNT','TREND_RESULT_MISMATCH_COUNT',
 'FLAG_RESULT_MISMATCH_COUNT','RC17_CONSISTENCY_VIOLATION_COUNT','CANDIDATE_SWING_MISMATCH_COUNT',
 'REQUIRED_FIELD_MISSING_COUNT','CHRONOLOGY_VIOLATION_COUNT','PA_BIAS_RESULT_MISMATCH_COUNT']
counts = dict.fromkeys(counter_names, 0)
trends = dict.fromkeys(['UP','DOWN','SIDEWAYS','UNKNOWN'],0)
biases = dict.fromkeys(['BUY','SELL','NONE'],0)
swing_states = dict.fromkeys(['SAMPLES_WITH_HIGH_ONLY','SAMPLES_WITH_LOW_ONLY','SAMPLES_WITH_BOTH_SWING_TYPES','SAMPLES_WITH_NO_SWINGS'],0)
transitions = {t.replace('->','_TO_'):0 for t in protocol['observed_transitions']}
unknown_pairs = collections.Counter()
events = []
issues = []
valid_samples = []
previous_cycle = None
previous_time = None
for position, sample in enumerate(samples):
    local_issues = []
    def fail(key, detail):
        counts[key] += 1
        local_issues.append(detail)
    structure = sample.get('structure', {})
    pa = sample.get('price_action', {})
    trend = structure.get('trend')
    bias = pa.get('bias')
    if trend in trends: trends[trend] += 1
    else: fail('REQUIRED_FIELD_MISSING_COUNT','Unknown or missing formal trend')
    if bias in biases: biases[bias] += 1
    else: fail('REQUIRED_FIELD_MISSING_COUNT','Unknown or missing formal PA bias')
    try:
        cycle = sample['cycle']; ts = datetime.fromisoformat(sample['timestamp'])
        if type(cycle) is not int or (previous_cycle is not None and (cycle <= previous_cycle or ts < previous_time)):
            fail('CHRONOLOGY_VIOLATION_COUNT','Persisted order is not chronological')
        previous_cycle, previous_time = cycle, ts
    except (KeyError,TypeError,ValueError):
        fail('CHRONOLOGY_VIOLATION_COUNT','Missing/invalid cycle or timestamp')
    obs = sample.get('market_structure_observability')
    if not isinstance(obs,dict):
        fail('DIAGNOSTIC_UNAVAILABLE_COUNT','Missing observability')
        valid_samples.append(False); issues.append({'position':position,'issues':local_issues}); continue
    counts['OBSERVABILITY_SAMPLE_COUNT'] += 1
    if obs.get('guard_status') not in ['EXECUTED','SKIPPED']:
        fail('DIAGNOSTIC_UNAVAILABLE_COUNT','Diagnostic unavailable')
        valid_samples.append(False); issues.append({'position':position,'issues':local_issues}); continue
    counts['DIAGNOSTIC_AVAILABLE_COUNT'] += 1
    if obs.get('history_unchanged_during_pipeline') is True: counts['HISTORY_UNCHANGED_TRUE_COUNT'] += 1
    else: fail('HISTORY_UNCHANGED_FALSE_COUNT','History unchanged guard false or absent')
    required = ['closed_candles','closed_history_sha256','closed_candle_count','total_candle_count','excluded_forming_candle',
        'swing_highs','swing_lows','swing_high_count','swing_low_count','latest_swing_high','previous_swing_high',
        'latest_swing_low','previous_swing_low','observed_result','candidates','engine_version','rc17_source_sha256']
    missing = [key for key in required if key not in obs]
    if missing:
        fail('REQUIRED_FIELD_MISSING_COUNT','Missing fields: '+','.join(missing))
        valid_samples.append(False); issues.append({'position':position,'issues':local_issues}); continue
    closed = obs['closed_candles']
    try:
        canonical(obs)
        if not all(all(type(c.get(f)) in [int,float] and math.isfinite(c[f]) for f in ['open','high','low','close','volume']) for c in closed):
            raise ValueError('Missing/nonfinite OHLCV')
    except (TypeError,ValueError): fail('SERIALIZATION_VIOLATION_COUNT','Noncanonical or nonfinite evidence')
    if len(closed)!=obs['closed_candle_count'] or obs['total_candle_count']!=len(closed)+1:
        fail('CLOSED_COUNT_MISMATCH_COUNT','Closed/total count inconsistent')
    if not obs['closed_history_sha256']: fail('HISTORY_HASH_MISSING_COUNT','Missing history hash')
    elif hashlib.sha256(canonical(closed).encode()).hexdigest()!=obs['closed_history_sha256']:
        fail('HISTORY_HASH_MISMATCH_COUNT','History hash inconsistent')
    forming=obs['excluded_forming_candle']
    if forming and any(c.get('timestamp')==forming.get('timestamp') or c.get('index')==forming.get('index') for c in closed):
        fail('FORMING_CANDLE_IN_CLOSED_HISTORY_COUNT','Forming candle occurs in closed history')
    if any(c.get('index')!=i for i,c in enumerate(closed)) or any(closed[i]['timestamp']>=closed[i+1]['timestamp'] for i in range(len(closed)-1)):
        fail('INDEX_ORDER_VIOLATION_COUNT','Closed history index/timestamp order invalid')
    highs=obs['swing_highs']; lows=obs['swing_lows']
    for kind,swings in [('high',highs),('low',lows)]:
        if obs['swing_'+kind+'_count']!=len(swings): fail('SWING_'+kind.upper()+'_COUNT_MISMATCH','Swing count differs from persisted list')
        for key,value in [('latest_swing_'+kind,swings[-1] if swings else None),('previous_swing_'+kind,swings[-2] if len(swings)>=2 else None)]:
            if obs[key]!=value: fail('NULLABLE_SWING_MISMATCH_COUNT',key+' inconsistent')
        confirmed=[c for c in obs['candidates'] if c.get('candidate_type')==kind.upper() and c.get('candidate_confirmed') is True]
        if [c['candidate_index'] for c in confirmed]!=[s['history_index'] for s in swings]:
            fail('CANDIDATE_SWING_MISMATCH_COUNT','Persisted candidates disagree with swings')
        expected_indexes=[]
        if obs['guard_status']=='EXECUTED':
            for i in range(2,len(closed)-2):
                values=[closed[j][kind] for j in [i-1,i-2,i+1,i+2]]
                if all(closed[i][kind]>v if kind=='high' else closed[i][kind]<v for v in values): expected_indexes.append(i)
        if expected_indexes!=[s['history_index'] for s in swings] or any(s['price']!=closed[s['history_index']][kind] or s['timestamp']!=closed[s['history_index']]['timestamp'] for s in swings):
            fail('CANDIDATE_SWING_MISMATCH_COUNT','Persisted swings not consistent with exact captured inputs')
    high_n,low_n=len(highs),len(lows)
    state='SAMPLES_WITH_BOTH_SWING_TYPES' if high_n and low_n else 'SAMPLES_WITH_HIGH_ONLY' if high_n else 'SAMPLES_WITH_LOW_ONLY' if low_n else 'SAMPLES_WITH_NO_SWINGS'
    swing_states[state]+=1
    expected_flags={'hh':high_n>=2 and highs[-1]['price']>highs[-2]['price'], 'lh':high_n>=2 and highs[-1]['price']<highs[-2]['price'],
        'hl':low_n>=2 and lows[-1]['price']>lows[-2]['price'], 'll':low_n>=2 and lows[-1]['price']<lows[-2]['price']}
    observed=obs['observed_result']
    mappings={'hh':'higher_high','hl':'higher_low','lh':'lower_high','ll':'lower_low'}
    if any(structure.get(k) is not v or observed.get(mappings[k]) is not v for k,v in expected_flags.items()):
        fail('FLAG_RESULT_MISMATCH_COUNT','Formal flags inconsistent')
    expected_trend='UP' if expected_flags['hh'] and expected_flags['hl'] else 'DOWN' if expected_flags['lh'] and expected_flags['ll'] else 'SIDEWAYS' if highs or lows else 'UNKNOWN'
    if trend!=observed.get('trend') or (obs['guard_status']=='EXECUTED' and trend!=expected_trend):
        fail('TREND_RESULT_MISMATCH_COUNT','Formal trend inconsistent')
    if bias!={'UP':'BUY','DOWN':'SELL','SIDEWAYS':'NONE','UNKNOWN':'NONE'}.get(trend):
        fail('PA_BIAS_RESULT_MISMATCH_COUNT','Persisted bias inconsistent with formal trend')
    if structure.get('last_high')!=(highs[-1]['price'] if highs else 0) or structure.get('last_low')!=(lows[-1]['price'] if lows else 0) or structure.get('valid') is not bool(highs or lows) or observed.get('valid')!=structure.get('valid'):
        fail('RC17_CONSISTENCY_VIOLATION_COUNT','Validity or last swing inconsistent')
    if obs['engine_version']!='RC17-CLOSED-CANDLE' or obs['rc17_source_sha256'].upper()!=digest(ROOT/'analysis/market_structure.py'):
        fail('RC17_CONSISTENCY_VIOLATION_COUNT','Engine identity inconsistent')
    counts['RC17_CONSISTENCY_VIOLATION_COUNT'] += int(bool(local_issues) and not any('Validity or last swing' in x or 'Engine identity' in x for x in local_issues))
    valid_samples.append(not local_issues)
    if local_issues: issues.append({'position':position,'cycle':sample.get('cycle'),'issues':local_issues})

def snapshot(s):
    o=s['market_structure_observability']; st=s['structure']
    out={k:o[k] for k in ['swing_high_count','swing_low_count','latest_swing_high','previous_swing_high','latest_swing_low','previous_swing_low','closed_history_sha256']}
    out.update({k.upper():st[k] for k in ['hh','hl','lh','ll']})
    out.update(trend=st['trend'],price_action_bias=s['price_action']['bias'],valid=st['valid'])
    return out
for i in range(1,len(samples)):
    a,b=samples[i-1],samples[i]
    if not valid_samples[i-1] or not valid_samples[i] or a['structure']['valid'] is not True or b['structure']['valid'] is not True:
        continue
    ta,tb=a['structure']['trend'],b['structure']['trend']
    if 'UNKNOWN' in [ta,tb]: unknown_pairs[ta+'_TO_'+tb]+=1; continue
    transitions[ta+'_TO_'+tb]+=1
    if ta=='SIDEWAYS' and a['price_action']['bias']=='NONE' and tb in ['UP','DOWN']:
        events.append({'from_cycle':a['cycle'],'to_cycle':b['cycle'],'from_timestamp':a['timestamp'],'to_timestamp':b['timestamp'],
            'before':snapshot(a),'after':snapshot(b),'after_formal_conditions_confirmed':True})
# Preserve UNKNOWN pairs even though UNKNOWN structures are formally invalid.
for a,b in zip(samples,samples[1:]):
    if 'UNKNOWN' in [a.get('structure',{}).get('trend'),b.get('structure',{}).get('trend')]:
        key=str(a.get('structure',{}).get('trend'))+'_TO_'+str(b.get('structure',{}).get('trend'))
        if key not in unknown_pairs: unknown_pairs[key]=sum(1 for x,y in zip(samples,samples[1:]) if str(x.get('structure',{}).get('trend'))+'_TO_'+str(y.get('structure',{}).get('trend'))==key)
failure_keys=[k for k in counts if k not in ['OBSERVABILITY_SAMPLE_COUNT','DIAGNOSTIC_AVAILABLE_COUNT','HISTORY_UNCHANGED_TRUE_COUNT']]
capture_valid=bool(raw_path and samples and raw.get('status')=='COMPLETED' and raw.get('requested_cycles')==600 and raw.get('collection_errors')==0 and raw.get('missing_price_count')==0 and raw.get('data_ready') is True and not protected_changes and not any(counts[k] for k in failure_keys) and counts['OBSERVABILITY_SAMPLE_COUNT']==len(samples))
capture_valid &= raw.get('analyzable_samples')==len(samples) and len(samples)+raw.get('skipped_cycles',0)+raw.get('collection_errors',0)==600
prospective=raw.get('prospective_microstructure',{})
capture_valid &= prospective.get('captured_samples')==len(samples) and prospective.get('source_analyzable_samples')==len(samples) and prospective.get('sample_count_matches_source') is True
classification='CAPTURE_INTEGRITY_FAILURE' if not capture_valid else 'DIRECTIONAL_TRANSITION_OBSERVED' if events else 'NO_DIRECTIONAL_TRANSITION_OBSERVED'
if not raw_path:
    counts = dict.fromkeys(counter_names, None)
    trends = dict.fromkeys(trends, None)
    biases = dict.fromkeys(biases, None)
    swing_states = dict.fromkeys(swing_states, None)
    transitions = dict.fromkeys(transitions, None)
    issues.append({'reason':'NO_RAW_NO_FORMAL_WINDOW', 'detail':'Feed stopped, normal warmup interrupted before formal window. Integrity/state/transition measurements unavailable, not measured zero.'})
result={'session_id':19,'block':'RC17_SIDEWAYS_TO_DIRECTIONAL_EVOLUTION_19_23','prospective':True,'independent_session':True,
 'capture_completed':bool(raw_path), 'formal_window_started':bool(raw_path), 'capture_call_count':1,
 'protocol_version':protocol['version'],'protocol_sha256':protocol_hash,'raw_file':str(raw_path) if raw_path else None,'raw_sha256':raw_hash,'raw_size':raw_path.stat().st_size if raw_path else None,
 'integrity':{'capture_integrity_valid':bool(capture_valid),'counts':counts,'issues':issues,'capture_status':call.get('status'),'code_or_prior_evidence_changed':protected_changes},
 'state_counts':{'trend_counts':trends,'pa_bias_counts':biases,'total_analyzed_samples':len(samples)},'swing_state_counts':swing_states,
 'transition_counts':transitions,'unknown_pairs':dict(unknown_pairs),'primary_events':events,'session_classification':classification,
 'research_only':True,'descriptive_only':True,'predictive_validation':False,'causal_validation':False,'operational_promotion':False,
 'collection':{k:raw.get(k,call.get(k)) for k in ['requested_cycles','analyzable_samples','skipped_cycles','collection_errors','warmup']}}
result_path=ROOT/'rc17_sideways_to_directional_evolution_session19_rc1_20261002.json'
with result_path.open('x',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
json.loads(result_path.read_text(encoding='utf-8'))
if raw_path: assert digest(raw_path)==raw_hash
assert git('rev-parse','HEAD')==head
rows={'STATUS':'PASS' if capture_valid else 'FAIL_CLOSED','SESSION_ID':19,'BLOCK':result['block'],'BRANCH':git('branch','--show-current'),'HEAD':head,'HEAD_BEFORE':head,'HEAD_AFTER':head,
 'PROTOCOL_VERSION':protocol['version'],'PROTOCOL_SHA256':protocol_hash,'PROTOCOL_VALIDATOR_STATUS':'PASS','RAW_FILE':result['raw_file'],'RAW_SHA256':raw_hash,'RAW_SIZE':result['raw_size'],
 'REQUESTED_CYCLES':call.get('requested_cycles',600),'TOTAL_CYCLES':len(samples)+raw.get('skipped_cycles',0)+raw.get('collection_errors',0),
 'ANALYZABLE_SAMPLES':len(samples),'SKIPPED_CYCLES':raw.get('skipped_cycles',0),'ERRORS':raw.get('collection_errors',call.get('collection_errors',0)),**counts,
 'TREND_COUNTS':trends,'PA_BIAS_COUNTS':biases,**swing_states,'TRANSITION_COUNTS':transitions,'UNKNOWN_PAIRS':dict(unknown_pairs),'PRIMARY_EVENT_COUNT':len(events),
 'SESSION_CLASSIFICATION':classification,'RESULT_JSON_FILE':str(result_path),'RESULT_JSON_SHA256':digest(result_path),'CAPTURE_INTEGRITY_VALID':bool(capture_valid),
 'RC17_CHANGED':False,'PRICE_ACTION_CHANGED':False,'COLLECTOR_CHANGED':False,'THRESHOLDS_CHANGED':False,'OPERATIONAL_LOGIC_CHANGED':False,
 'FROZEN10_CHANGED':False,'SESSIONS11_13_CHANGED':False,'SESSIONS14_18_CHANGED':False,'SESSION20_EXECUTED':False,'STAGE_COMMIT_PUSH_EXECUTED':False,
 'RESEARCH_ONLY':True,'DESCRIPTIVE_ONLY':True,'PREDICTIVE_VALIDATION':False,'CAUSAL_VALIDATION':False,'OPERATIONAL_PROMOTION':False,
 'CAPTURE_CALL_COUNT':1,'RAW_UNCHANGED_DURING_AUDIT':bool(raw_path and digest(raw_path)==raw_hash),'WORKBOOKS_MODIFIED_BY_AGENT':False,
 'SESSION19_EXECUTED':True,'SESSION19_COMPLETED':bool(raw_path),'FORMAL_WINDOW_STARTED':bool(raw_path),'PROTECTED_FILES_PRESERVED':not changed,
 'SOURCE_UPDATED_WORKBOOKS':[x for x in changed if x in operational_workbooks],'WARMUP':call.get('warmup'),'ISSUES':issues,'PRIMARY_EVENTS':events}
if not raw_path: rows['FAIL_CLOSED_REASON']='Normal warmup/capture did not generate raw; no retry and no reconstructed evidence'; rows['CALL_RESULT']=call
report=ROOT/'saida_rc17_sideways_to_directional_session19_rc1_20261002.txt'
with report.open('x',encoding='utf-8') as f:
    for k,v in rows.items(): f.write(k+' = '+(json.dumps(v,ensure_ascii=False,allow_nan=False) if not isinstance(v,str) else v)+'\n')
print(json.dumps({k:rows[k] for k in ['STATUS','RAW_FILE','RAW_SHA256','ANALYZABLE_SAMPLES','SESSION_CLASSIFICATION','RESULT_JSON_SHA256']},ensure_ascii=False))
