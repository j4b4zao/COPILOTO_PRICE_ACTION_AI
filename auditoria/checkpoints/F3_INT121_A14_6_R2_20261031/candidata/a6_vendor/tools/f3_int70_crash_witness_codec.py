"""Closed JSON codec for offline crash witnesses; no pickle or dynamic classes."""
from dataclasses import asdict
import hashlib
import json
from a6_vendor.tools.f3_int44_witness_membership_simulator import Membership
from a6_vendor.tools.f3_int50_concurrent_recovery_simulator import EpochEvidence, ConcurrentResult
from a6_vendor.tools.f3_int53_interleaving_simulator import Snapshot
from a6_vendor.tools.f3_int54_schedule_divergence_simulator import Request
from a6_vendor.tools.f3_int62_strict_evidence_simulator import strict_json
from a6_vendor.tools.f3_int66_crash_schedule_simulator import run_crash_schedule
from a6_vendor.tools.f3_int68_crash_witness_simulator import CrashWitness, replay_crash_witness

MAX_BYTES=131072


def wire_scan(value):
    stack=[(value,0)]; nodes=0
    while stack:
        item,depth=stack.pop(); nodes+=1
        if nodes>8192 or depth>32: raise ValueError('WIRE_TRAVERSAL_LIMIT')
        if type(item) is dict:
            if len(item)>64 or any(type(k) is not str for k in item): raise ValueError('WIRE_OBJECT_LIMIT')
            stack.extend((v,depth+1) for pair in item.items() for v in pair)
        elif type(item) is list:
            if len(item)>256: raise ValueError('WIRE_ARRAY_LIMIT')
            stack.extend((v,depth+1) for v in item)
        elif type(item) is str:
            if len(item)>4096: raise ValueError('WIRE_STRING_LIMIT')
        elif type(item) is int:
            if not -(2**63)<=item<2**63: raise ValueError('WIRE_INTEGER_LIMIT')
        elif type(item) not in (bool,type(None)):
            raise ValueError('WIRE_SCALAR_TYPE')


def pack(value):
    if type(value) is tuple: return {'kind':'tuple','items':[pack(v) for v in value]}
    if type(value) is Membership:
        return dict(kind='membership',epoch=value.epoch,members=pack(value.members),threshold=value.threshold,predecessor=value.predecessor)
    if type(value) is EpochEvidence:
        return dict(kind='evidence',witness=value.witness,epoch=value.epoch,digest=value.digest)
    if type(value) in (str,int,bool,type(None)): return value
    raise ValueError('UNKNOWN_FIXTURE_TYPE')


def unpack(value):
    if type(value) in (str,int,bool,type(None)): return value
    if type(value) is not dict: raise ValueError('UNKNOWN_WIRE_TYPE')
    kind=value.get('kind')
    if kind=='tuple' and set(value)=={'kind','items'} and type(value['items']) is list:
        return tuple(unpack(v) for v in value['items'])
    if kind=='membership' and set(value)=={'kind','epoch','members','threshold','predecessor'}:
        return Membership(value['epoch'],unpack(value['members']),value['threshold'],value['predecessor'])
    if kind=='evidence' and set(value)=={'kind','witness','epoch','digest'}:
        return EpochEvidence(value['witness'],value['epoch'],value['digest'])
    raise ValueError('UNKNOWN_WIRE_TAG_OR_FIELDS')


def trace_digest(trace):
    encoded=json.dumps(asdict(trace),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def encode_witness(witness):
    verified=replay_crash_witness(witness)
    if verified.status!='CRASH_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED':
        raise ValueError(verified.status)
    payload=dict(schema=1,requests=[dict(round_id=r.round_id,arguments=[[k,pack(v)] for k,v in r.arguments]) for r in witness.requests],
                 left_events=[list(row[:3]) for row in witness.left.trace],right_events=[list(row[:3]) for row in witness.right.trace],
                 left_sha256=trace_digest(witness.left),right_sha256=trace_digest(witness.right))
    wire_scan(payload)
    blob=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    if len(blob)>MAX_BYTES: raise ValueError('WIRE_BYTE_LIMIT')
    return blob


def decode_witness(blob):
    if type(blob) is not bytes or not 1<=len(blob)<=MAX_BYTES: raise ValueError('WIRE_BYTE_LIMIT')
    try:
        payload=strict_json(blob); wire_scan(payload)
        if (type(payload) is not dict or set(payload)!={'schema','requests','left_events','right_events','left_sha256','right_sha256'}
                or type(payload['schema']) is not int or payload['schema']!=1
                or type(payload['requests']) is not list or not 1<=len(payload['requests'])<=3):
            raise ValueError('INVALID_WIRE_SCHEMA')
        requests=[]
        for item in payload['requests']:
            if (type(item) is not dict or set(item)!={'round_id','arguments'} or type(item['arguments']) is not list
                    or any(type(pair) is not list or len(pair)!=2 or type(pair[0]) is not str for pair in item['arguments'])):
                raise ValueError('INVALID_WIRE_REQUEST')
            args=tuple((k,unpack(v)) for k,v in item['arguments'])
            if len({k for k,v in args})!=len(args): raise ValueError('DUPLICATE_WIRE_ARGUMENT')
            requests.append(Request(item['round_id'],args))
        traces=[]
        for side in ('left','right'):
            events=payload[side+'_events']
            if type(events) is not list or not 1<=len(events)<=16 or any(type(e) is not list or len(e)!=3 for e in events):
                raise ValueError('INVALID_WIRE_EVENTS')
            trace=run_crash_schedule(Snapshot(),tuple(requests),tuple(tuple(e) for e in events))
            if trace.status!='CRASH_SCHEDULE_FIXTURE_UNAUTHENTICATED' or trace_digest(trace)!=payload[side+'_sha256']:
                raise ValueError('WIRE_REPLAY_DIGEST_MISMATCH')
            traces.append(trace)
        witness=CrashWitness(tuple(requests),*traces)
        if replay_crash_witness(witness).status!='CRASH_DIVERGENCE_REPRODUCED_FIXTURE_UNAUTHENTICATED':
            raise ValueError('WIRE_DIVERGENCE_NOT_REPRODUCED')
        return witness
    except (TypeError,KeyError,UnicodeError,RecursionError,OverflowError) as error:
        raise ValueError('INVALID_WIRE_STRUCTURE') from error


def assess_encoded(blob):
    try:
        decode_witness(blob)
    except ValueError:
        return ConcurrentResult('ENCODED_CRASH_WITNESS_REJECTED')
    return ConcurrentResult('ENCODED_CRASH_WITNESS_REPLAYED_FIXTURE_UNAUTHENTICATED',2)


def safe_to_promote(*args,**kwargs):
    return False
