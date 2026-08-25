"""Testes offline da pipeline explícita Profit RTD RC7."""

from core.order_flow_state import OrderFlowState
from market_data.excel_range_gateway import ExcelRangeGateway
from market_data.profit_rtd_order_flow_pipeline import ProfitRTDOrderFlowPipeline


class Range:
    def __init__(self, value):
        self.value = value


class Sheet:
    def __init__(self, matrix):
        self.matrix = matrix
        self.calls = []

    def range(self, cell_range):
        self.calls.append(cell_range)
        return Range(self.matrix)


class Sheets:
    def __init__(self, sheet):
        self.sheet = sheet

    def __getitem__(self, name):
        assert name == "Planilha1"
        return self.sheet


class Book:
    def __init__(self, sheet):
        self.sheets = Sheets(sheet)


class Excel:
    def __init__(self, matrix=None):
        self.book = None if matrix is None else Book(Sheet(matrix))


class Reader:
    def __init__(self, payloads):
        self.payloads = list(payloads)

    def read_times_trades(self, symbol):
        payload = self.payloads.pop(0)
        assert payload["symbol"] == symbol
        return payload


def trade(ts, quantity, aggressor, price=174400.0):
    return {
        "timestamp": ts,
        "buyer": "XP",
        "price": price,
        "quantity": quantity,
        "seller": "BTG",
        "aggressor": aggressor,
    }


def payload(trades, timestamp="2026-08-25T10:00:00"):
    return {
        "symbol": "WINV26",
        "timestamp": timestamp,
        "trades": trades,
        "source": "PROFIT_RTD",
        "observational_only": True,
        "score_influence_allowed": False,
        "order_execution_allowed": False,
    }


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_excel_range_gateway_reutiliza_workbook_aberto():
    matrix = [[1, 2], [3, 4]]
    excel = Excel(matrix)
    gateway = ExcelRangeGateway(excel)
    assert gateway.read_range("Planilha1", "A1:B2") == matrix
    assert excel.book.sheets.sheet.calls == ["A1:B2"]


def teste_excel_range_gateway_rejeita_workbook_ausente():
    raises(RuntimeError, lambda: ExcelRangeGateway(Excel()).read_range("Planilha1", "A1:H52"))


def teste_pipeline_primeira_janela_estabelece_baseline():
    state = OrderFlowState()
    initial = [
        trade("2026-08-25T10:00:02.000", 10, "Comprador"),
        trade("2026-08-25T10:00:01.000", 5, "Vendedor"),
    ]
    receipt = ProfitRTDOrderFlowPipeline(Reader([payload(initial)]), state).process(
        "WINV26", price=174400.0
    )
    assert receipt.baseline_reset
    assert not receipt.state_updated
    assert receipt.new_trade_count == 0
    assert state.sample_count == 0
    assert state.cumulative_buy == 0.0
    assert state.cumulative_sell == 0.0


def teste_pipeline_emite_apenas_negocios_novos_e_atualiza_estado():
    state = OrderFlowState()
    old = [
        trade("2026-08-25T10:00:02.000", 10, "Comprador"),
        trade("2026-08-25T10:00:01.000", 5, "Vendedor"),
    ]
    current = [
        trade("2026-08-25T10:00:04.000", 12, "Comprador"),
        trade("2026-08-25T10:00:03.000", 4, "Vendedor"),
        *old,
    ]
    pipeline = ProfitRTDOrderFlowPipeline(
        Reader([payload(old), payload(current, "2026-08-25T10:00:04")]),
        state,
    )
    first = pipeline.process("WINV26", price=174400.0)
    second = pipeline.process("WINV26", price=174410.0)
    assert first.baseline_reset
    assert second.continuity == "CONTIGUOUS"
    assert second.new_trade_count == 2
    assert second.source_units == 2
    assert second.state_updated
    assert state.buy_aggression == 12.0
    assert state.sell_aggression == 4.0
    assert state.delta == 8.0
    assert state.sample_count == 1
    assert state.sampling_mode == "PROFIT_RTD_TT"


def teste_pipeline_janela_identica_nao_cria_delta_zero():
    state = OrderFlowState()
    window = [trade("2026-08-25T10:00:02.000", 10, "Comprador")]
    pipeline = ProfitRTDOrderFlowPipeline(Reader([payload(window), payload(window)]), state)
    pipeline.process("WINV26", price=174400.0)
    receipt = pipeline.process("WINV26", price=174400.0)
    assert receipt.new_trade_count == 0
    assert not receipt.state_updated
    assert state.sample_count == 0
    assert state.waiting_for_sample


def teste_pipeline_permanece_sem_influencia_direta_no_nucleo():
    state = OrderFlowState()
    window = [trade("2026-08-25T10:00:02.000", 10, "Comprador")]
    receipt = ProfitRTDOrderFlowPipeline(Reader([payload(window)]), state).process(
        "WINV26", price=174400.0
    )
    assert receipt.observational_only
    assert not receipt.score_influence_allowed
    assert not receipt.decision_influence_allowed
    assert not receipt.order_execution_allowed


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC7 APROVADO")


if __name__ == "__main__":
    main()
