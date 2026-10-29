"""Deterministic bounded mutation corpus for the closed crash-witness JSON codec."""
from dataclasses import dataclass
import json
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int70_crash_witness_codec import decode_witness, encode_witness, assess_encoded


@dataclass(frozen=True)
class MutationAudit(ConcurrentResult):
    complete: bool = False
    observations: tuple = ()
    failures: tuple = ()


def corpus(blob):
    canonical=encode_witness(decode_witness(blob))
    original=json.loads(canonical); cases=[]
    def changed(label,edit):
        value=json.loads(canonical); edit(value)
        cases.append((label,False,json.dumps(value).encode()))
    cases.append(('pretty_json',True,json.dumps(original,indent=2).encode()))
    cases.append(('compact_json',True,canonical))
    for offset in (0,len(canonical)//4,len(canonical)//2,len(canonical)-1):
        cases.append(('truncate_'+str(offset),False,canonical[:offset]))
    for value in (True,0,2,None,[],{}):
        changed('schema_'+repr(value),lambda p,v=value:p.update(schema=v))
    changed('extra_class_field',lambda p:p.update(__class__='subprocess.Popen'))
    for value in ('','0','0'*63,'0'*64,'0'*65,None,False,[]):
        changed('digest_'+repr(value),lambda p,v=value:p.update(left_sha256=v))
    for value in ([],{},None,[None]*4):
        changed('requests_'+repr(value),lambda p,v=value:p.update(requests=v))
    changed('duplicate_argument',lambda p:p['requests'][0]['arguments'].append(p['requests'][0]['arguments'][0]))
    changed('unknown_wire_tag',lambda p:p['requests'][0]['arguments'][0][1].update(kind='__import__'))
    for op in ('unknown','',None,False):
        changed('event_op_'+repr(op),lambda p,v=op:p['left_events'][0].__setitem__(0,v))
    for actor in (False,-1,4,None,'0'):
        changed('event_actor_'+repr(actor),lambda p,v=actor:p['left_events'][0].__setitem__(1,v))
    for generation in (False,-1,64,None,'0'):
        changed('event_generation_'+repr(generation),lambda p,v=generation:p['left_events'][0].__setitem__(2,v))
    cases.append(('invalid_utf8',False,b'\xff'))
    cases.append(('duplicate_schema_key',False,b'{"schema":0,'+canonical[1:]))
    return tuple(cases)


def audit_mutations(blob,*,max_cases=128):
    if type(max_cases) is not int or not 1<=max_cases<=128:
        return MutationAudit('INVALID_MUTATION_BOUND')
    try:
        cases=corpus(blob)
    except ValueError:
        return MutationAudit('INVALID_MUTATION_BASELINE')
    observations=[]; failures=[]
    for label,expected,payload in cases[:max_cases]:
        verdict=assess_encoded(payload)
        accepted=verdict.status=='ENCODED_CRASH_WITNESS_REPLAYED_FIXTURE_UNAUTHENTICATED'
        observations.append((label,expected,accepted))
        if accepted!=expected: failures.append(label)
    complete=len(cases)<=max_cases
    status=('CODEC_MUTATION_EXPECTATION_MISMATCH' if failures else
            'CODEC_MUTATION_CORPUS_FIXTURE_UNAUTHENTICATED' if complete else 'CODEC_MUTATION_LIMIT_REACHED')
    return MutationAudit(status,len(observations),complete=complete,
                         observations=tuple(observations),failures=tuple(failures))


def safe_to_promote(*args,**kwargs):
    return False
