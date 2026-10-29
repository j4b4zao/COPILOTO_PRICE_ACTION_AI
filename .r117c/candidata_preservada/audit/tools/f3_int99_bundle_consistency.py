"""F3-INT-99: offline, read-only cross-check of schema2 bundle evidence receipts.

No authentication, persistence, external I/O, or operational authority is implied.
"""
from dataclasses import dataclass
import hashlib
from tools.f3_int98_policy_bundle_registry import (
    PolicyBundleRecord, PolicyEvidenceRegistry, PolicyEvidenceReceipt,
    decode_policy_bundle, encode_policy_witness, valid_policy_registry, NAMESPACE,
)
from tools.f3_int88_import_divergence_witness import classify_import_ends
from tools.f3_int72_atomic_witness_batch_simulator import digest_valid

@dataclass(frozen=True)
class BundleConsistencyResult:
    status: str
    references: tuple = ()
    f3: str = 'OPEN'
    orders_allowed: bool = False
    live_certified: bool = False
    flow_complete: bool = False
    f3_resolved: bool = False
    native_prototype_authorized: bool = False
    strict_deadline_guaranteed: bool = False
    authenticated_witness_verified: bool = False


def verify_policy_bundle_receipts(records, receipts, registry):
    """Fail closed; compare typed receipts to decoded fixture bytes and registry.

    No registry mutation; a match is not proof of real-world authenticity.
    """
    if not valid_policy_registry(registry):
        return BundleConsistencyResult('INVALID_POLICY_REGISTRY')
    if (type(records) is not tuple or type(receipts) is not tuple
            or not 1 <= len(records) <= 8 or len(records) != len(receipts)):
        return BundleConsistencyResult('INVALID_CONSISTENCY_BATCH')
    references = []
    for record, receipt in zip(records, receipts):
        if (type(record) is not PolicyBundleRecord or type(receipt) is not PolicyEvidenceReceipt
                or type(record.blob) is not bytes or not digest_valid(record.sha256)
                or not digest_valid(receipt.reference_id) or type(receipt.classification) is not str):
            return BundleConsistencyResult('INVALID_CONSISTENCY_RECORD')
        try:
            witness = decode_policy_bundle(record.blob, record.sha256)
            expected_reference = hashlib.sha256(
                NAMESPACE.encode('ascii') + b'\0REFERENCE\0' + encode_policy_witness(witness)
            ).hexdigest()
            expected_classification = classify_import_ends(
                witness.left.snapshots[-1], witness.right.snapshots[-1]
            )
        except (ValueError, AttributeError, IndexError, TypeError):
            return BundleConsistencyResult('INVALID_CONSISTENCY_BUNDLE')
        if (receipt.reference_id != expected_reference
                or receipt.classification != expected_classification):
            return BundleConsistencyResult('CONSISTENCY_RECEIPT_MISMATCH')
        references.append(expected_reference)
    if len(set(references)) != len(references):
        return BundleConsistencyResult('CONSISTENCY_DUPLICATE_REFERENCE')
    if any(ref not in registry.reference_ids for ref in references):
        return BundleConsistencyResult('CONSISTENCY_UNREGISTERED_REFERENCE')
    return BundleConsistencyResult('CONSISTENT_FIXTURE_UNAUTHENTICATED', tuple(references))


def safe_to_promote(*args, **kwargs):
    return False
