import tkinter as tk



class Dashboard:


    def __init__(self):


        self.janela = tk.Tk()


        self.janela.title(
            "COPILOTO PRICE ACTION AI"
        )


        self.janela.geometry(
            "500x600"
        )



        self.texto = tk.Label(

            self.janela,

            text="COPILOTO INICIANDO",

            font=(

                "Arial",

                14

            ),

            justify="left"

        )


        self.texto.pack(

            padx=20,

            pady=20

        )




    def atualizar(

        self,

        resultado

    ):



        texto = """

COPILOTO PRICE ACTION AI

=========================


TENDÊNCIA:

{}



ZONA:

{}



FLUXO:

{}



SCORE:

{}



DECISÃO:

{}



ENTRADA:

{}



STOP:

{}



ALVO:

{}



STATUS:

{}

""".format(


resultado.structure.tendencia,


resultado.zone["zona"],


resultado.order_flow["pressao"],


resultado.score,


resultado.decision["acao"],


resultado.risk["entrada"],


resultado.risk["stop"],


resultado.risk["alvo"],


resultado.trade_status

)



        self.texto.config(

            text=texto

        )



        self.janela.update()




    def iniciar(self):


        self.janela.mainloop()