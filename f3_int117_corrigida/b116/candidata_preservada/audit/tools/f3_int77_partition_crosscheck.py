"""Bounded differential check of monolithic and segmented offline lineage."""
from dataclasses import dataclass
from tools.f3_int50_concurrent_recovery_simulator import ConcurrentResult
from tools.f3_int75_source_inventory_guard import verify_guarded_lineage
from tools.f3_int76_segmented_lineage_simulator import verify_segments


@dataclass(frozen=True)
class PartitionResult(ConcurrentResult):
    observations: tuple = ()


def audit_partitions(records,deltas=(),*,sizes=(2,3,8,16,32),anchor_stage=52,anchor_tests=526):
    if (type(sizes) is not tuple or not 1<=len(sizes)<=5
            or any(type(n) is not int or not 2<=n<=32 for n in sizes) or len(set(sizes))!=len(sizes)):
        return PartitionResult('INVALID_PARTITION_SIZES')
    if type(records) is not tuple or not 1<=len(records)<=32:
        return PartitionResult('INVALID_PARTITION_RECORDS')
    reference=verify_guarded_lineage(records,deltas,anchor_stage=anchor_stage,anchor_tests=anchor_tests)
    accepted=reference.status=='DECLARED_LINEAGE_FIXTURE_UNAUTHENTICATED'
    observations=[]
    for size in sizes:
        candidate=verify_segments(records,deltas,anchor_stage=anchor_stage,anchor_tests=anchor_tests,
                                  chunk_size=size,max_chunk_bytes=33554432,max_total_bytes=33554432)
        candidate_accepted=candidate.status=='SEGMENTED_LINEAGE_FIXTURE_UNAUTHENTICATED'
        observations.append((size,candidate.status))
        if (candidate_accepted!=accepted or accepted and
                (candidate.stages,candidate.applied,candidate.final_tests)!=(reference.stages,reference.applied,reference.final_tests)):
            return PartitionResult('PARTITION_CONTRACT_MISMATCH',len(observations),observations=tuple(observations))
    return PartitionResult('ACCEPTED_PARTITIONS_AGREE_FIXTURE_UNAUTHENTICATED' if accepted
                           else 'REJECTED_PARTITIONS_AGREE_FIXTURE_UNAUTHENTICATED',len(observations),observations=tuple(observations))


def safe_to_promote(*args,**kwargs): return False
