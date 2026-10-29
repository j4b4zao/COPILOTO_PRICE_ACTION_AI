"""Closed source inventory guard for declared offline package lineage.

Reject source names that the 74 inventory would otherwise ignore. This is a
conservative fixture policy, not a claim about every filesystem or import rule.
"""
from io import BytesIO
import zipfile
from tools.f3_int62_strict_evidence_simulator import verify_strict_blob
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int74_declared_delta_simulator import DeltaLineageResult,source_path,verify_declared_lineage


def verify_guarded_lineage(records,deltas=(),**bounds):
    if (type(records) is not tuple or not 1<=len(records)<=32
            or any(type(r) is not PackageRecord or type(r.blob) is not bytes for r in records)):
        return DeltaLineageResult('INVALID_LINEAGE_RECORDS')
    # Validate aggregate bounds before opening any archives or delegating deltas.
    budget=bounds.get('max_total_bytes',33554432)
    if type(budget) is not int or not 1<=budget<=33554432:
        return DeltaLineageResult('INVALID_LINEAGE_BOUND')
    if sum(len(r.blob) for r in records)>budget:
        return DeltaLineageResult('LINEAGE_BYTE_LIMIT_EXCEEDED')
    for record in records:
        integrity=verify_strict_blob(record.blob,record.sha256,record.stage)
        if integrity.status!='STRICT_EVIDENCE_FIXTURE_UNAUTHENTICATED':
            return DeltaLineageResult('LINEAGE_PACKAGE_REJECTED')
        with zipfile.ZipFile(BytesIO(record.blob)) as archive:
            for name in archive.namelist():
                lower=name.casefold()
                if lower.startswith(('tests/','tools/')) and lower.endswith('.py') and not source_path(name):
                    return DeltaLineageResult('UNSUPPORTED_SOURCE_INVENTORY_NAME')
    try:
        return verify_declared_lineage(records,deltas,**bounds)
    except TypeError:
        return DeltaLineageResult('INVALID_LINEAGE_BOUND')


def safe_to_promote(*args,**kwargs): return False
