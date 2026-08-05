from connectors.excel_connector import ExcelConnector
from connectors.profit_reader import ProfitReader


excel = ExcelConnector()


excel.conectar(
    "C:\\COPILOTO_PRICE_ACTION_AI\\dados\\mercado1.xlsx"
)


profit = ProfitReader(
    excel
)


dados = profit.obter_dados()


print("================")
print("DADOS PROFIT")
print("================")


print(dados)