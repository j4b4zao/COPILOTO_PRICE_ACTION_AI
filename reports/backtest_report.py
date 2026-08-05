class BacktestReport:


    def __init__(self):

        self.resultados = []



    def adicionar(

        self,

        resultado

    ):


        self.resultados.append(

            resultado

        )




    def calcular(self):


        total = len(

            self.resultados

        )


        if total == 0:

            return {}



        wins = []

        losses = []



        for r in self.resultados:


            if r["resultado"] == "WIN":


                wins.append(

                    r["pontos"]

                )


            else:


                losses.append(

                    r["pontos"]

                )



        ganhos = sum(

            wins

        )


        perdas = abs(

            sum(losses)

        )



        win_rate = (

            len(wins)

            /

            total

        ) * 100



        if perdas > 0:


            profit_factor = ganhos / perdas


        else:


            profit_factor = 0




        media_gain = 0


        if len(wins):

            media_gain = ganhos / len(wins)



        media_loss = 0


        if len(losses):

            media_loss = perdas / len(losses)




        return {


            "operacoes": total,


            "win_rate": round(
                win_rate,
                2
            ),


            "profit_factor": round(
                profit_factor,
                2
            ),


            "media_gain": round(
                media_gain,
                2
            ),


            "media_loss": round(
                media_loss,
                2
            )

        }




    def mostrar(self):


        dados = self.calcular()



        print("\n")

        print("==============================")

        print("BACKTEST REPORT")

        print("==============================")



        for chave, valor in dados.items():


            print(

                chave,

                ":",

                valor

            )


        print("==============================")