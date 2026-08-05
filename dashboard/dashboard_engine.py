class DashboardEngine:


    def __init__(self):

        self.estado = {}



    # =====================================
    # ATUALIZAR PAINEL
    # =====================================

    def atualizar(

        self,

        resultado

    ):


        self.estado = {


            "ativo":

            self.buscar_ativo(resultado),



            "tendencia":

            self.buscar_tendencia(resultado),



            "regime":

            self.buscar_regime(resultado),



            "setup":

            self.buscar_setup(resultado),



            "score":

            resultado.score,



            "qualidade":

            self.buscar_qualidade(resultado),



            "decisao":

            self.buscar_decisao(resultado),



            "sinal":

            self.buscar_sinal(resultado)



        }



        return self.estado





    # =====================================
    # BUSCAS
    # =====================================


    def buscar_ativo(

        self,

        resultado

    ):


        if resultado.market:


            return getattr(

                resultado.market,

                "ativo",

                "N/A"

            )


        return "N/A"





    def buscar_tendencia(

        self,

        resultado

    ):


        if resultado.structure:


            return getattr(

                resultado.structure,

                "tendencia",

                "N/A"

            )


        return "N/A"





    def buscar_regime(

        self,

        resultado

    ):


        if resultado.regime:


            return resultado.regime.get(

                "regime"

            )


        return "N/A"





    def buscar_setup(

        self,

        resultado

    ):


        if resultado.setup:


            return resultado.setup.get(

                "setup"

            )


        return "NENHUM"





    def buscar_qualidade(

        self,

        resultado

    ):


        if resultado.quality:


            return resultado.quality.get(

                "qualidade"

            )


        return 0





    def buscar_decisao(

        self,

        resultado

    ):


        if resultado.decision:


            return resultado.decision.get(

                "acao"

            )


        return "AGUARDANDO"





    def buscar_sinal(

        self,

        resultado

    ):


        if resultado.signal:


            return resultado.signal.get(

                "status"

            )


        return "SEM SINAL"





    # =====================================
    # EXIBIR
    # =====================================


    def mostrar(self):


        print("\n")

        print("================================")

        print(" COPILOTO PRICE ACTION AI ")

        print("================================")



        for chave, valor in self.estado.items():


            print(

                chave.upper(),

                ":",

                valor

            )



        print("================================")