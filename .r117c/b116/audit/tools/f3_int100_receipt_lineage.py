"""F3-INT-100: offline, deterministic receipt lineage for schema2 fixture batches.

No I/O, no authentication, no live authorization. Only typed fixture values.
"""
from dataclasses import dataclass
import hashlib
import json
from tools.f3_int98_policy_bundle_registry import (PolicyEvidenceRegistry, PolicyEvidenceReceipt,
    PolicyBundleRecord, valid_policy_registry)
from tools.f3_int99_bundle_consistency import verify_policy_bundle_receipts
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid

DOMAIN = b'F3_INT100_SCHEMA2_RECEIPT_LINEAGE_V1\0'

@dataclass(frozen=True)
class ReceiptLineage:
    status: str
    chain: tuple = ()
    tip: str = ''
    f3: str = 'OPEN'
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


def build_receipt_lineage(records, receipts, registry, *, base_registry=None):
    """Bind an ordered batch to a pre-existing registry prefix, fail closed.

    A hash chain detects modifications to an *unchanged trusted copy* of its tip;
    it does not authenticate the origin of any evidence.
    """
    if not valid_policy_registry(registry):
        return ReceiptLineage('INVALID_POLICY_REGISTRY')
    if base_registry is None:
        base_registry = PolicyEvidenceRegistry()
    if not valid_policy_registry(base_registry):
        return ReceiptLineage('INVALID_BASE_REGISTRY')
    if type(records) is not tuple or type(receipts) is not tuple or not 1 <= len(records) <= 8 or len(records) != len(receipts):
        return ReceiptLineage('INVALID_LINEAGE_BATCH')
    base = base_registry.reference_ids
    if registry.reference_ids[:len(base)] != base or len(registry.reference_ids) != len(base) + len(records):
        return ReceiptLineage('LINEAGE_REGISTRY_BOUNDARY_MISMATCH')
    check = verify_policy_bundle_receipts(records, receipts, registry)
    if check.status != 'CONSISTENT_FIXTURE_UNAUTHENTICATED':
        return ReceiptLineage(check.status)
    if registry.reference_ids[len(base):] != check.references:
        return ReceiptLineage('LINEAGE_ORDER_MISMATCH')
    seed = hashlib.sha256(DOMAIN + b'BASE\0' + b''.join(x.encode('ascii') + b'\0' for x in base)).hexdigest()
    chain = []
    previous = seed
    for i, (record, receipt) in enumerate(zip(records, receipts)):
        # Type checking is performed by verify_policy_bundle_receipts.
        payload = json.dumps({'index': i, 'reference': receipt.reference_id,
            'classification': receipt.classification, 'bundle_sha256': record.sha256},
            sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        previous = hashlib.sha256(DOMAIN + bytes.fromhex(previous) + payload).hexdigest()
        chain.append(previous)
    return ReceiptLineage('LINEAGE_FIXTURE_UNAUTHENTICATED', tuple(chain), previous)


def verify_receipt_lineage(records, receipts, registry, expected_tip, *, base_registry=None):
    if not digest_valid(expected_tip):
        return ReceiptLineage('INVALID_EXPECTED_TIP')
    result = build_receipt_lineage(records, receipts, registry, base_registry=base_registry)
    if result.status != 'LINEAGE_FIXTURE_UNAUTHENTICATED':
        return result
    if result.tip != expected_tip:
        return ReceiptLineage('LINEAGE_TIP_MISMATCH')
    return result


def safe_to_promote(*args, **kwargs):
    return False
