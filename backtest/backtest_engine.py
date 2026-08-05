from market.market_engine import MarketEngine

from simulation.paper_trader import PaperTrader

from bot import analisar

from reports.backtest_report import BacktestReport

import csv



class BacktestEngine:


    def __init__(self):

        self.engine = MarketEngine()

        self.trader = PaperTrader()

        self.report = BacktestReport()

        self.operacoes = []



    def carregar_candles(self, arquivo):


        candles = []


        with open(

            arquivo,

            "r",

            encoding="utf-8"

        ) as f:


            leitor = csv.DictReader(f)


            for linha in leitor:

                candles.append(linha)



        return candles




    def executar(self, arquivo):


        candles = self.carregar_candles(

            arquivo

        )


        print(
            "\nIniciando Backtest..."
        )



        for candle in candles:



            dados = {


                "data": candle["data"],


                "hora": candle["hora"],


                "open": float(candle["open"]),


                "high": float(candle["high"]),


                "low": float(candle["low"]),


                "close": float(candle["close"]),


                "volume": float(candle["volume"])

            }



            resultado = analisar(

                dados,

                self.engine

            )



            self.trader.executar(

                resultado

            )



            status = self.trader.monitorar(

                dados["close"]

            )



            if isinstance(status, dict):


                pontos = 0



                if status["lado"] == "COMPRA":


                    pontos = (

                        status["alvo"]

                        -

                        status["entrada"]

                    )



                else:


                    pontos = (

                        status["entrada"]

                        -

                        status["alvo"]

                    )



                self.report.adicionar({


                    "resultado": status["status"],


                    "pontos": pontos


                })



        self.report.mostrar()