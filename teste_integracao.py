from connectors.excel_connector import ExcelConnector
from connectors.profit_reader import ProfitReader

from market.market_state import MarketState



excel = ExcelConnector()


excel.conectar(
    "C:\\COPILOTO_PRICE_ACTION_AI\\dados\\mercado1.xlsx"
)



profit = ProfitReader(
    excel
)



dados = profit.obter_dados()



mercado = MarketState()


mercado.atualizar(
    dados
)



print("================")
print("MARKET STATE")
print("================")


mercado.mostrar()