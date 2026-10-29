"""Small bounded metamorphic corpus over closed offline import bundles."""
from dataclasses import dataclass
from io import BytesIO
from itertools import islice
import hashlib
import json
import zipfile
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int90_import_witness_bundle import assess_import_bundle
from tools.f3_int91_evidence_registry import BundleRecord,describe_bundle


@dataclass(frozen=True)
class BundleMutationResult(ConcurrentResult):
    complete: bool = False
    observations: tuple = ()
    failures: tuple = ()


def bundle_cases(blob):
    with zipfile.ZipFile(BytesIO(blob)) as archive: original={n:archive.read(n) for n in archive.namelist()}
    def rewrite(edit):
        files=original.copy(); edit(files); stream=BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for n,v in files.items(): archive.writestr(n,v)
        return stream.getvalue()
    def manifest_edit(edit):
        def apply(files):
            p=json.loads(files['bundle_manifest.json']); edit(p); files['bundle_manifest.json']=json.dumps(p).encode()
        return apply
    def witness_edit(edit):
        def apply(files):
            p=json.loads(files['witness.json']); edit(p); files['witness.json']=json.dumps(p).encode()
            m=json.loads(files['bundle_manifest.json']); m['witness_sha256']=hashlib.sha256(files['witness.json']).hexdigest()
            files['bundle_manifest.json']=json.dumps(m).encode()
        return apply
    yield 'outer_repack','REFERENCE',rewrite(lambda files:None)
    yield 'pretty_manifest','REFERENCE',rewrite(lambda files:files.update({'bundle_manifest.json':json.dumps(json.loads(files['bundle_manifest.json']),indent=2).encode()}))
    yield 'reverse_catalog_order','REFERENCE',rewrite(manifest_edit(lambda p:p['records'].reverse()))
    def reverse_pair(p):
        p['left_events'],p['right_events']=p['right_events'],p['left_events']
        p['left_trace_sha256'],p['right_trace_sha256']=p['right_trace_sha256'],p['left_trace_sha256']
    yield 'reverse_pair','OBSERVATIONS',rewrite(witness_edit(reverse_pair))
    for value in (True,0,2,None,[],{}):
        yield 'manifest_schema_'+repr(value),'REJECT',rewrite(manifest_edit(lambda p,v=value:p.update(schema=v)))
    for value in ([],None,[None]*49):
        yield 'manifest_records_'+repr(value),'REJECT',rewrite(manifest_edit(lambda p,v=value:p.update(records=v)))
    yield 'extra_manifest_field','REJECT',rewrite(manifest_edit(lambda p:p.update(__class__='arbitrary')))
    yield 'duplicate_catalog_record','REJECT',rewrite(manifest_edit(lambda p:p['records'].append(p['records'][0])))
    yield 'catalog_escape','REJECT',rewrite(manifest_edit(lambda p:p['records'][0].update(file='../escape.zip')))
    yield 'catalog_bool_stage','REJECT',rewrite(manifest_edit(lambda p:p['records'][0].update(stage=True)))
    yield 'bad_witness_digest','REJECT',rewrite(manifest_edit(lambda p:p.update(witness_sha256='0'*64)))
    yield 'bad_trace_digest_rehashed','REJECT',rewrite(witness_edit(lambda p:p.update(left_trace_sha256='0'*64)))
    yield 'bad_witness_schema_rehashed','REJECT',rewrite(witness_edit(lambda p:p.update(schema=2)))
    yield 'extra_file','REJECT',rewrite(lambda files:files.update({'extra.txt':b'x'}))
    yield 'missing_witness','REJECT',rewrite(lambda files:files.pop('witness.json'))
    for offset in (0,len(blob)//2,len(blob)-1): yield 'truncate_'+str(offset),'REJECT',blob[:offset]


def audit_bundle_mutations(record,*,max_cases=64):
    if type(max_cases) is not int or not 1<=max_cases<=64:
        return BundleMutationResult('INVALID_BUNDLE_CORPUS_BOUND')
    if type(record) is not BundleRecord or type(record.blob) is not bytes or not 1<=len(record.blob)<=262144:
        return BundleMutationResult('INVALID_BUNDLE_CORPUS_BASELINE')
    try:
        with zipfile.ZipFile(BytesIO(record.blob)) as archive:
            entries=archive.infolist()
            if len(entries)>50 or sum(e.file_size for e in entries)>1048576:
                return BundleMutationResult('BUNDLE_CORPUS_DECODED_LIMIT')
        baseline=describe_bundle(record.blob,record.sha256)
    except (ValueError,zipfile.BadZipFile):
        return BundleMutationResult('INVALID_BUNDLE_CORPUS_BASELINE')
    cases=tuple(islice(bundle_cases(record.blob),max_cases+1)); complete=len(cases)<=max_cases
    observations=[]; failures=[]
    for label,expected,payload in cases[:max_cases]:
        digest=hashlib.sha256(payload).hexdigest()
        verdict=assess_import_bundle(payload,digest)
        accepted=verdict.status=='IMPORT_BUNDLE_REPLAYED_FIXTURE_UNAUTHENTICATED'; identity='REJECT'
        if accepted:
            description=describe_bundle(payload,digest)
            identity=('INCONSISTENT' if description.reference_id==baseline.reference_id and description.observable_id!=baseline.observable_id else
                      'REFERENCE' if description.reference_id==baseline.reference_id else
                      'OBSERVATIONS' if description.observable_id==baseline.observable_id else 'CHANGED')
        observations.append((label,expected,identity))
        if identity!=expected: failures.append(label)
    status=('BUNDLE_CORPUS_EXPECTATION_MISMATCH' if failures else
            'BUNDLE_CORPUS_FIXTURE_UNAUTHENTICATED' if complete else 'BUNDLE_CORPUS_LIMIT_REACHED')
    return BundleMutationResult(status,len(observations),complete=complete,
                                  observations=tuple(observations),failures=tuple(failures))


def safe_to_promote(*args,**kwargs): return False
