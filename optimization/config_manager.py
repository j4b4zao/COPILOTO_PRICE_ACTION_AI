import json
import os



class ConfigManager:


    def __init__(self):


        self.arquivo = (

            "config/config.json"

        )


        self.config_padrao = {


            "score_minimo":80,


            "risk_reward":3,


            "peso_price_action":30,


            "peso_order_flow":25,


            "peso_estrutura":25,


            "peso_contexto":20


        }




    def salvar(

        self,

        configuracao

    ):



        with open(

            self.arquivo,

            "w",

            encoding="utf-8"

        ) as arquivo:



            json.dump(

                configuracao,

                arquivo,

                indent=4

            )




    def carregar(self):


        if not os.path.exists(

            self.arquivo

        ):



            self.salvar(

                self.config_padrao

            )



            return self.config_padrao



        with open(

            self.arquivo,

            "r",

            encoding="utf-8"

        ) as arquivo:



            return json.load(

                arquivo

            )




    def mostrar(self):


        config = self.carregar()



        print("\n")

        print("==============================")

        print("CONFIGURAÇÃO ATUAL")

        print("==============================")



        for chave, valor in config.items():


            print(

                chave,

                ":",

                valor

            )


        print("==============================")