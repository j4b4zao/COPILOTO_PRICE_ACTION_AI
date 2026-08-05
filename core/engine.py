import time



class CopilotEngine:


    def __init__(
        self,
        intervalo=1
    ):

        self.intervalo = intervalo

        self.ativo = True



    def iniciar(self, funcao):


        print(
            "COPILOTO INICIADO"
        )


        while self.ativo:


            try:

                funcao()


            except Exception as erro:

                print(
                    "ERRO:",
                    erro
                )


            time.sleep(
                self.intervalo
            )



    def parar(self):

        self.ativo = False