class OptimizationEngine:


    def __init__(self):


        self.melhor_resultado = None

        self.melhor_configuracao = None




    def testar(

        self,

        configuracao,

        resultado

    ):



        score = resultado["profit_factor"]



        if self.melhor_resultado is None:


            self.melhor_resultado = score

            self.melhor_configuracao = configuracao



        elif score > self.melhor_resultado:



            self.melhor_resultado = score


            self.melhor_configuracao = configuracao




    def executar(

        self,

        backtest

    ):



        configuracoes = [



            {


            "score_minimo":60,

            "rr":2


            },


            {


            "score_minimo":70,

            "rr":3


            },


            {


            "score_minimo":80,

            "rr":3


            },


            {


            "score_minimo":90,

            "rr":4


            }



        ]




        for config in configuracoes:



            resultado = backtest.executar(

                config

            )



            self.testar(

                config,

                resultado

            )





        return {


            "configuracao":

            self.melhor_configuracao,


            "profit_factor":

            self.melhor_resultado


        }