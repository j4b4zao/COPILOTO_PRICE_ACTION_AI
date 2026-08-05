import sys
import os

sys.path.append(
    os.path.dirname(__file__)
)


from connectors.excel_connector import ExcelConnector


excel = ExcelConnector()


conectado = excel.conectar(
    "C:\\COPILOTO_PRICE_ACTION_AI\\dados\\mercado.xlsx"
)


if conectado:

    preco = excel.ler_celula(
        "Planilha1",
        "A1"
    )


    print(
        "Preço recebido:",
        preco
    )