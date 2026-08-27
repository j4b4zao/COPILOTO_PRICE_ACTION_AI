from __future__ import annotations

from tools import profit_rtd_order_flow_confluence_shadow_session as mod


class FakeQuoteReader:
    def __init__(self, rows):
        self.rows = list(rows)
        self.i = 0

    def obter_dados(self):
        row = self.rows[min(self.i, len(self.rows) - 1)]
        self.i += 1
        return row


def test_read_price_retries_same_cycle_without_forward_fill():
    reader = FakeQuoteReader([
        {'ativo': 'WINV26', 'close': None},
        {'ativo': 'WINV26', 'close': 177000},
    ])
    price, attempts, reason = mod._read_price(reader, 'WINV26', attempts=2)
    assert price == 177000.0
    assert attempts == 2
    assert reason == 'OK'


def test_read_price_fails_safe_after_two_missing_reads():
    reader = FakeQuoteReader([
        {'ativo': 'WINV26', 'close': None},
        {'ativo': 'WINV26', 'close': None},
    ])
    price, attempts, reason = mod._read_price(reader, 'WINV26', attempts=2)
    assert price is None
    assert attempts == 2
    assert reason == 'PRICE_MISSING'


def test_read_price_rejects_symbol_mismatch():
    reader = FakeQuoteReader([
        {'ativo': 'WDOU26', 'close': 5000},
        {'ativo': 'WDOU26', 'close': 5001},
    ])
    price, attempts, reason = mod._read_price(reader, 'WINV26', attempts=2)
    assert price is None
    assert attempts == 2
    assert reason == 'SYMBOL_MISMATCH'


def test_security_contract_is_explicit_in_source():
    source = open(mod.__file__, 'r', encoding='utf-8').read()
    assert "'observational_only': True" in source
    assert "'predictive_claim_allowed': False" in source
    assert "'score_influence_allowed': False" in source
    assert "'decision_influence_allowed': False" in source
    assert "'order_execution_allowed': False" in source
    assert "'price_action_integration': 'PENDING_RC54_2'" in source


if __name__ == '__main__':
    test_read_price_retries_same_cycle_without_forward_fill()
    test_read_price_fails_safe_after_two_missing_reads()
    test_read_price_rejects_symbol_mismatch()
    test_security_contract_is_explicit_in_source()
    print('PROFIT_RTD_RC54_1=OK')
