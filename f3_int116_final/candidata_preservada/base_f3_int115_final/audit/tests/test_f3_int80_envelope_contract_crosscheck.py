import unittest
from test_f3_int76_segmented_lineage import fixture_package
from test_f3_int78_verified_envelope import rewrite_record
from tools.f3_int73_package_lineage_simulator import PackageRecord
from tools.f3_int78_verified_envelope import EnvelopePolicy
from tools.f3_int80_envelope_contract_crosscheck import audit_envelope_contracts,safe_to_promote


class EnvelopeContractTests(unittest.TestCase):
    def test_valid_common_domain(self):
        records=tuple(fixture_package(53+i,528+2*i) for i in range(8))
        r=audit_envelope_contracts(records)
        self.assertEqual(r.status,'ENVELOPE_CONTRACTS_FIXTURE_UNAUTHENTICATED')
        self.assertTrue(all(row[-1]=='AGREE' for row in r.observations))
    def test_explicit_extension_labeled(self):
        r=rewrite_record(fixture_package(53,528),{f'docs/{i}':b'x' for i in range(600)})
        result=audit_envelope_contracts((r,),policy=EnvelopePolicy(1024))
        self.assertEqual(result.observations[0][-1],'EXPLICIT_FILE_CAPACITY_EXTENSION')
    def test_stricter_count_policy_labeled(self):
        r=fixture_package(53,10000001)
        result=audit_envelope_contracts((r,))
        self.assertEqual(result.observations[0][-1],'CONSERVATIVE_NEW_REJECTION')
    def test_source_inventory_alias_rejected_by_both(self):
        r=rewrite_record(fixture_package(53,528),{'TOOLS/other.py':b'x'})
        result=audit_envelope_contracts((r,)); self.assertEqual(result.observations[0][-1],'AGREE')
    def test_corrupted_logs(self):
        r=rewrite_record(fixture_package(53,528),{'LOG_F3_INT53_NOVOS.txt':b'Ran 2 tests in 0.1s\nFAILED\nOK\n'})
        result=audit_envelope_contracts((r,)); self.assertEqual(result.observations[0][-1],'AGREE')
    def test_corrupted_digest(self):
        r=fixture_package(53,528); bad=PackageRecord(r.stage,r.blob,'0'*64)
        result=audit_envelope_contracts((bad,)); self.assertEqual(result.observations[0][-1],'AGREE')
    def test_invalid_policy(self):
        self.assertEqual(audit_envelope_contracts((fixture_package(53,528),),policy=EnvelopePolicy(True)).status,'INVALID_CONTRACT_POLICY')
    def test_stage_one_not_in_anchored_comparison_domain(self):
        self.assertEqual(audit_envelope_contracts((fixture_package(1,528),)).status,'INVALID_CONTRACT_RECORDS')
    def test_zero_predecessor_count_not_in_comparison_domain(self):
        self.assertEqual(audit_envelope_contracts((fixture_package(53,2),)).status,'OUTSIDE_POSITIVE_ANCHOR_DOMAIN')
    def test_invalid_records(self):
        for records in ((),[],(None,),(fixture_package(53,528),)*17):
            self.assertEqual(audit_envelope_contracts(records).status,'INVALID_CONTRACT_RECORDS')
    def test_flags(self):
        r=audit_envelope_contracts((fixture_package(53,528),)); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
