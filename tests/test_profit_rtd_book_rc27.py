from models.book_depth import BookDepthSnapshot
import tools.profit_rtd_book_validation_session as session


class FakeExcel:
    def conectar(self, path):
        return True


class FakeGateway:
    def __init__(self, excel):
        self.excel = excel


class FakeReader:
    def __init__(self, gateway):
        self.gateway = gateway


class FakeProvider:
    def __init__(self, reader, source="PROFIT_RTD", max_levels=50):
        self.index = 0

    def snapshot(self, symbol):
        i = self.index
        self.index += 1
        best_bid = 177000.0 + (i * 5.0)
        best_ask = best_bid + 5.0
        bids = [(best_bid - (j * 5.0), 100 + i + j, 0) for j in range(5)]
        asks = [(best_ask + (j * 5.0), 90 + i + j, 0) for j in range(5)]
        return BookDepthSnapshot.build(
            symbol=symbol,
            timestamp=f"2026-08-26T09:00:{i:02d}",
            bids=bids,
            asks=asks,
            source="PROFIT_RTD",
        )


def run():
    original_excel = session.ExcelConnector
    original_gateway = session.ExcelRangeGateway
    original_reader = session.ProfitRTDBookDepthReader
    original_provider = session.NormalizedLevel2BookDepthProvider
    try:
        session.ExcelConnector = FakeExcel
        session.ExcelRangeGateway = FakeGateway
        session.ProfitRTDBookDepthReader = FakeReader
        session.NormalizedLevel2BookDepthProvider = FakeProvider
        result = session.run_session("WINV26", cycles=6, interval=0, output_dir=None, sleeper=lambda _: None)
        assert result["status"] == "COMPLETED", result
        assert result["completed_cycles"] == 6
        assert result["fresh_snapshots"] == 6
        assert result["duplicate_snapshots"] == 0
        assert result["quote_changes"] == 5
        assert result["availability_rate"] == 1.0
        assert result["symbol_changes"] == 0
        assert result["collection_errors"] == 0
        assert result["observational_only"] is True
        assert result["score_influence_allowed"] is False
        assert result["decision_influence_allowed"] is False
        assert result["order_execution_allowed"] is False
        assert result["reasons"] == []
        print("PROFIT_RTD_BOOK_RC27=PASS")
    finally:
        session.ExcelConnector = original_excel
        session.ExcelRangeGateway = original_gateway
        session.ProfitRTDBookDepthReader = original_reader
        session.NormalizedLevel2BookDepthProvider = original_provider


if __name__ == "__main__":
    run()
