"""Gate standalone do retry transitório Excel no Profit RTD RC24."""

from market_data.excel_range_gateway import ExcelRangeGateway


class Range:
    def __init__(self, values):
        self.values = list(values)

    @property
    def value(self):
        current = self.values.pop(0)
        if isinstance(current, Exception):
            raise current
        return current


class Sheet:
    def __init__(self, values):
        self.values = values
        self.calls = 0

    def range(self, cell_range):
        self.calls += 1
        return Range([self.values[self.calls - 1]])


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
    def __init__(self, values):
        self.book = Book(Sheet(values))


def raises(expected, callback):
    try:
        callback()
    except expected as exc:
        return exc
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_falha_transitoria_recupera_na_segunda_tentativa():
    matrix = [[1, 2], [3, 4]]
    excel = Excel([RuntimeError("Excel ocupado"), matrix])
    sleeps = []
    gateway = ExcelRangeGateway(excel, attempts=3, retry_delay=0.05, sleeper=sleeps.append)
    assert gateway.read_range("Planilha1", "A1:B2") == matrix
    assert excel.book.sheets.sheet.calls == 2
    assert sleeps == [0.05]


def teste_falha_persistente_continua_fail_safe():
    excel = Excel([RuntimeError("ocupado 1"), RuntimeError("ocupado 2"), RuntimeError("ocupado 3")])
    sleeps = []
    gateway = ExcelRangeGateway(excel, attempts=3, retry_delay=0.05, sleeper=sleeps.append)
    exc = raises(RuntimeError, lambda: gateway.read_range("Planilha1", "A1:H52"))
    assert "após 3 tentativa(s)" in str(exc)
    assert excel.book.sheets.sheet.calls == 3
    assert sleeps == [0.05, 0.05]


def teste_configuracao_invalida_e_rejeitada():
    raises(ValueError, lambda: ExcelRangeGateway(Excel([[]]), attempts=0))
    raises(ValueError, lambda: ExcelRangeGateway(Excel([[]]), retry_delay=-0.01))


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC24 APROVADO")


if __name__ == "__main__":
    main()
