"""Gate offline do runner de preflight Profit RTD RC15."""

from tools import profit_rtd_preflight as cli


class _FakeExcel:
    def __init__(self, *, connect_ok=True, matrix=None):
        self.connect_ok = connect_ok
        self.book = _FakeBook(matrix or _valid_matrix())

    def conectar(self, _path):
        return self.connect_ok


class _FakeRange:
    def __init__(self, value):
        self.value = value


class _FakeSheet:
    def __init__(self, matrix):
        self.matrix = matrix

    def range(self, _name):
        return _FakeRange(self.matrix)


class _FakeSheets:
    def __init__(self, matrix):
        self.matrix = matrix

    def __getitem__(self, _name):
        return _FakeSheet(self.matrix)


class _FakeBook:
    def __init__(self, matrix):
        self.sheets = _FakeSheets(matrix)


def _valid_matrix():
    rows = [
        ["WINV26", "Negócios", "", "", "", "", "", ""],
        ["Data", "Compradora", "Valor", "Quantidade", "Vendedora", "Agressor", "", ""],
        ["25/08/2026 10:00:00.001", "A", 180000, 10, "B", "Comprador", "", ""],
    ]
    rows.extend([["", "", "", "", "", "", "", ""] for _ in range(49)])
    return rows


def test_ready_returns_zero(capsys):
    code = cli.run_preflight("WINV26", excel_factory=lambda: _FakeExcel())
    out = capsys.readouterr().out
    assert code == 0
    assert "PROFIT_RTD_PREFLIGHT=READY" in out
    assert "trade_count=1" in out
    assert "score_influence_allowed=False" in out
    assert "order_execution_allowed=False" in out


def test_symbol_mismatch_returns_two(capsys):
    code = cli.run_preflight("WDOU26", excel_factory=lambda: _FakeExcel())
    out = capsys.readouterr().out
    assert code == 2
    assert "PROFIT_RTD_PREFLIGHT=NOT_READY" in out
    assert "READ_ERROR:ValueError" in out


def test_excel_connect_failure_returns_one(capsys):
    code = cli.run_preflight(
        "WINV26",
        excel_factory=lambda: _FakeExcel(connect_ok=False),
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "PROFIT_RTD_PREFLIGHT=ERROR" in out
    assert "reason=EXCEL_CONNECT_FAILED" in out


def main():
    # Gate compatível com execução direta por Python puro.
    class _Capture:
        def __enter__(self):
            import contextlib
            import io
            self.buffer = io.StringIO()
            self.ctx = contextlib.redirect_stdout(self.buffer)
            self.ctx.__enter__()
            return self

        def __exit__(self, *args):
            self.ctx.__exit__(*args)

    with _Capture() as capture:
        assert cli.run_preflight("WINV26", excel_factory=lambda: _FakeExcel()) == 0
    assert "PROFIT_RTD_PREFLIGHT=READY" in capture.buffer.getvalue()

    with _Capture() as capture:
        assert cli.run_preflight("WDOU26", excel_factory=lambda: _FakeExcel()) == 2
    assert "PROFIT_RTD_PREFLIGHT=NOT_READY" in capture.buffer.getvalue()

    with _Capture() as capture:
        assert cli.run_preflight(
            "WINV26", excel_factory=lambda: _FakeExcel(connect_ok=False)
        ) == 1
    assert "EXCEL_CONNECT_FAILED" in capture.buffer.getvalue()

    print("Profit RTD RC15 tests: OK")


if __name__ == "__main__":
    main()
