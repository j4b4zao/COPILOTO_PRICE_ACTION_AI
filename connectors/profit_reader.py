"""
connectors/profit_reader.py

Leitor dos dados do Profit Pro através do Excel.

A linha padrão da planilha representa o ativo principal
analisado pelo Copiloto.

RC11
"""


class ProfitReader:

    def __init__(self, excel, linha=2):

        self.excel = excel

        # ======================================================
        # LINHA DO ATIVO
        # ======================================================

        # Linha padrão:
        #   linha 2 = ativo principal do Copiloto
        #
        # Futuramente:
        #   linha 3 = segundo ativo / WDO
        #
        # O contrato do ativo é definido no Profit/DDE.
        self.linha = linha

    def obter_dados(self):

        dados = {}

        linha = self.linha

        # ======================================================
        # IDENTIFICAÇÃO
        # ======================================================

        dados["ativo"] = self.excel.ler_celula(
            "Planilha1",
            f"A{linha}"
        )

        # ======================================================
        # DATA / HORA
        # ======================================================

        dados["data"] = self.excel.ler_celula(
            "Planilha1",
            f"B{linha}"
        )

        dados["hora"] = self.excel.ler_celula(
            "Planilha1",
            f"C{linha}"
        )

        # ======================================================
        # OHLC
        # ======================================================

        dados["close"] = self.excel.ler_celula(
            "Planilha1",
            f"D{linha}"
        )

        dados["open"] = self.excel.ler_celula(
            "Planilha1",
            f"E{linha}"
        )

        dados["high"] = self.excel.ler_celula(
            "Planilha1",
            f"F{linha}"
        )

        dados["low"] = self.excel.ler_celula(
            "Planilha1",
            f"G{linha}"
        )

        # ======================================================
        # ESTATÍSTICAS
        # ======================================================

        # Média
        dados["media"] = self.excel.ler_celula(
            "Planilha1",
            f"I{linha}"
        )

        # Número de negócios
        #
        # IMPORTANTE:
        # NEGÓCIOS não é tratado como volume.
        dados["negocios"] = self.excel.ler_celula(
            "Planilha1",
            f"J{linha}"
        )

        # Volume
        #
        # O Profit agora exporta o campo Volume em K.
        dados["volume"] = self.excel.ler_celula(
            "Planilha1",
            f"K{linha}"
        )

        # ======================================================
        # VENCIMENTO
        # ======================================================

        dados["vencimento"] = self.excel.ler_celula(
            "Planilha1",
            f"L{linha}"
        )

        # ======================================================
        # INDICADORES
        # ======================================================

        dados["adx"] = self.excel.ler_celula(
            "Planilha1",
            f"M{linha}"
        )

        dados["macd"] = self.excel.ler_celula(
            "Planilha1",
            f"N{linha}"
        )

        # ======================================================
        # ORDER FLOW (OPCIONAL)
        # ======================================================

        # Valores acumulados exportados pelo Profit. Células
        # vazias mantêm o módulo como dado indisponível.
        dados["agressao_compra"] = self.excel.ler_celula(
            "Planilha1",
            f"O{linha}"
        )

        dados["agressao_venda"] = self.excel.ler_celula(
            "Planilha1",
            f"P{linha}"
        )

        # ======================================================
        # MÉDIA MÓVEL
        # ======================================================

        # A exportação atual do Profit enviada para análise
        # não possui mais uma coluna de Média Móvel.
        #
        # Mantemos a chave para compatibilidade com módulos
        # existentes do projeto, sem inventar um valor.
        dados["media_movel"] = None

        return dados
