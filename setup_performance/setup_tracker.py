import json
import os



class SetupTracker:


    def __init__(self):


        self.arquivo = (

            "dados/setups.json"

        )


        self.dados = {}


        self.carregar()




    # =====================================
    # CARREGAR MEMÓRIA
    # =====================================

    def carregar(self):


        if os.path.exists(

            self.arquivo

        ):



            with open(

                self.arquivo,

                "r",

                encoding="utf-8"

            ) as arquivo:



                self.dados = json.load(

                    arquivo

                )



        else:


            self.dados = {}





    # =====================================
    # SALVAR MEMÓRIA
    # =====================================

    def salvar(self):


        with open(

            self.arquivo,

            "w",

            encoding="utf-8"

        ) as arquivo:



            json.dump(

                self.dados,

                arquivo,

                indent=4

            )





    # =====================================
    # REGISTRAR RESULTADO
    # =====================================

    def registrar(

        self,

        setup,

        resultado,

        pontos

    ):


        if setup is None:

            return



        nome = setup["setup"]



        if nome == "NENHUM":

            return




        if nome not in self.dados:


            self.dados[nome] = {


                "operacoes":0,


                "wins":0,


                "loss":0,


                "pontos":0


            }




        self.dados[nome]["operacoes"] += 1



        self.dados[nome]["pontos"] += pontos




        if resultado == "WIN":


            self.dados[nome]["wins"] += 1



        elif resultado == "LOSS":


            self.dados[nome]["loss"] += 1




        self.salvar()





    # =====================================
    # ESTATÍSTICA
    # =====================================

    def calcular(self):


        resultado = {}



        for nome, dados in self.dados.items():



            total = dados["operacoes"]



            if total > 0:


                win_rate = (

                    dados["wins"]

                    /

                    total

                ) * 100



            else:


                win_rate = 0




            resultado[nome] = {


                "operacoes": total,


                "wins": dados["wins"],


                "loss": dados["loss"],


                "win_rate": round(

                    win_rate,

                    2

                ),


                "pontos": dados["pontos"]


            }



        return resultado





    # =====================================
    # MOSTRAR
    # =====================================

    def mostrar(self):


        print("\n")

        print("==============================")

        print("MEMÓRIA DOS SETUPS")

        print("==============================")



        for nome, dados in self.calcular().items():


            print()

            print(nome)

            print(dados)



        print("==============================")