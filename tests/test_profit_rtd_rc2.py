"""Testes offline do mapa de cotações Profit RTD RC2."""

from connectors.profit_reader import ProfitReader


HEADERS = (
    "Asset",
    "Data",
    "Hora",
    "Último",
    "Abertura",
    "Máximo",
    "Mínimo",
    "Strike",
    "Média",
    "Volume",
    "Vencimento",
    "ADX",
    "MACD Histograma",
    "Média Móvel",
)
COLUMNS = tuple("ABCDEFGHIJKLMN")
ROW = (
    "WINV26",
    "25/08/2026",
    "10:13:33",
    174815,
    174565,
    175380,
    174170,
    0,
    174587.92510841353,
    136134201334,
    "14/10/2026",
    "59,52",
    "227,89",
    "171.638,50",
)


class Excel:
    def __init__(self, *, row=ROW, headers=HEADERS):
        self.values = {}
        self.calls = []
        for column, value in zip(COLUMNS, headers):
            self.values[f"{column}1"] = value
        for column, value in zip(COLUMNS, row):
            self.values[f"{column}2"] = value

    def ler_celula(self, sheet, cell):
        self.calls.append((sheet, cell))
        return self.values.get(cell)


def raises(expected, callback):
    try:
        callback()
    except expected:
        return
    raise AssertionError(f"Esperava {expected.__name__}.")


def teste_reader_mapeia_identificacao_data_e_ohlc():
    data = ProfitReader(Excel()).obter_dados()
    assert data["ativo"] == "WINV26"
    assert data["data"] == "25/08/2026"
    assert data["hora"] == "10:13:33"
    assert data["close"] == 174815
    assert data["open"] == 174565
    assert data["high"] == 175380
    assert data["low"] == 174170


def teste_reader_mapeia_strike_media_volume_e_vencimento():
    data = ProfitReader(Excel()).obter_dados()
    assert data["strike"] == 0
    assert data["media"] == 174587.92510841353
    assert data["volume"] == 136134201334
    assert data["vencimento"] == "14/10/2026"


def teste_reader_mapeia_indicadores_nas_colunas_corretas():
    data = ProfitReader(Excel()).obter_dados()
    assert data["adx"] == "59,52"
    assert data["macd"] == "227,89"
    assert data["media_movel"] == "171.638,50"


def teste_volume_vem_de_j_e_nao_de_k():
    excel = Excel()
    data = ProfitReader(excel).obter_dados()
    assert data["volume"] == excel.values["J2"]
    assert data["volume"] != excel.values["K2"]


def teste_negocios_permanece_indisponivel_sem_inferencia():
    data = ProfitReader(Excel()).obter_dados()
    assert data["negocios"] is None


def teste_agressoes_permanecem_indisponiveis():
    data = ProfitReader(Excel()).obter_dados()
    assert data["agressao_compra"] is None
    assert data["agressao_venda"] is None


def teste_layout_e_validado_apenas_uma_vez():
    excel = Excel()
    reader = ProfitReader(excel)
    reader.obter_dados()
    reader.obter_dados()
    header_calls = [
        call for call in excel.calls
        if call[1].endswith("1")
    ]
    assert len(header_calls) == 14


def teste_cabecalho_divergente_e_rejeitado():
    headers = list(HEADERS)
    headers[9] = "Negócios"
    raises(
        ValueError,
        lambda: ProfitReader(
            Excel(headers=headers),
        ).obter_dados(),
    )


def teste_cabecalho_ausente_e_rejeitado():
    headers = list(HEADERS)
    headers[13] = None
    raises(
        ValueError,
        lambda: ProfitReader(
            Excel(headers=headers),
        ).obter_dados(),
    )


def teste_linha_configuravel_e_respeitada():
    excel = Excel()
    for column, value in zip(COLUMNS, ROW):
        excel.values[f"{column}3"] = value
    excel.values["A3"] = "WDOU26"
    data = ProfitReader(excel, linha=3).obter_dados()
    assert data["ativo"] == "WDOU26"
    assert ("Planilha1", "A3") in excel.calls


def teste_dependencia_e_linha_invalidas_sao_rejeitadas():
    raises(TypeError, lambda: ProfitReader(object()))
    raises(TypeError, lambda: ProfitReader(Excel(), linha=True))
    raises(ValueError, lambda: ProfitReader(Excel(), linha=1))


def teste_saida_nao_contem_score_decisao_ou_ordem():
    data = ProfitReader(Excel()).obter_dados()
    assert "score" not in data
    assert "decision" not in data
    assert "order" not in data
    assert "execute" not in data


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 PROFIT RTD RC2 APROVADO")


if __name__ == "__main__":
    main()
