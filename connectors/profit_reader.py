class ProfitReader:

    def __init__(self, excel):

        self.excel = excel

    def obter_dados(self):

        dados = {}

        # ==========================
        # ATIVO
        # ==========================

        dados["ativo"] = self.excel.ler_celula(
            "Planilha1",
            "A3"
        )

        # ==========================
        # DATA / HORA
        # ==========================

        dados["data"] = self.excel.ler_celula(
            "Planilha1",
            "B3"
        )

        dados["hora"] = self.excel.ler_celula(
            "Planilha1",
            "C3"
        )

        # ==========================
        # OHLC
        # ==========================

        dados["close"] = self.excel.ler_celula(
            "Planilha1",
            "D3"
        )

        dados["open"] = self.excel.ler_celula(
            "Planilha1",
            "E3"
        )

        dados["high"] = self.excel.ler_celula(
            "Planilha1",
            "F3"
        )

        dados["low"] = self.excel.ler_celula(
            "Planilha1",
            "G3"
        )

        # ==========================
        # ESTATÍSTICAS
        # ==========================

        dados["media"] = self.excel.ler_celula(
            "Planilha1",
            "I3"
        )

        dados["negocios"] = self.excel.ler_celula(
            "Planilha1",
            "J3"
        )

        # ==========================
        # INDICADORES
        # ==========================

        dados["adx"] = self.excel.ler_celula(
            "Planilha1",
            "L3"
        )

        dados["macd"] = self.excel.ler_celula(
            "Planilha1",
            "M3"
        )

        dados["media_movel"] = self.excel.ler_celula(
            "Planilha1",
            "N3"
        )

        return dados