import xlwings as xw
from datetime import datetime


class ProfitAdapter:

    def __init__(self):

        self.arquivo_excel = None
        self.conectado = False

    # =====================================
    # CONECTAR EXCEL
    # =====================================

    def conectar(self):

        try:

            self.arquivo_excel = xw.books.active

            self.conectado = True

            print("Excel conectado.")

            return True

        except Exception as erro:

            print("Erro conexão Excel:", erro)

            self.conectado = False

            return False

    # =====================================
    # LER MERCADO
    # =====================================

    def ler_dados(self):

        if not self.conectado:

            print("ProfitAdapter: Excel não conectado.")
            return None

        try:

            planilha = self.arquivo_excel.sheets[0]

            dados = {

                "ativo": planilha.range("A2").value,
                "open": planilha.range("B2").value,
                "high": planilha.range("C2").value,
                "low": planilha.range("D2").value,
                "close": planilha.range("E2").value,
                "volume": planilha.range("F2").value,
                "hora": datetime.now().strftime("%H:%M:%S")

            }

            print("=" * 50)
            print("DADOS LIDOS DO EXCEL")
            print("=" * 50)

            for chave, valor in dados.items():
                print(f"{chave}: {valor}")

            print("=" * 50)

            return dados

        except Exception as erro:

            print("Erro leitura Profit:", erro)

            return None