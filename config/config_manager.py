import json
import os



class ConfigManager:


    def __init__(self):


        self.arquivo = (

            "config/config.json"

        )


        self.criar_config()



    # =====================================
    # CRIAR CONFIG PADRÃO
    # =====================================


    def criar_config(self):


        pasta = "config"



        if not os.path.exists(pasta):


            os.makedirs(pasta)




        if not os.path.exists(

            self.arquivo

        ):



            configuracao = {



                "score_minimo":75,



                "qualidade_minima":80,



                "peso_price_action":30,



                "peso_order_flow":25,



                "peso_estrutura":25,



                "peso_contexto":20,



                "horario_inicio":"09:00",



                "horario_fim":"17:00",



                "setup_ativo":[



                    "BOS_PULLBACK_COMPRA",


                    "BOS_PULLBACK_VENDA"



                ],



                "risco_maximo":200



            }




            with open(

                self.arquivo,

                "w",

                encoding="utf-8"

            ) as arquivo:



                json.dump(

                    configuracao,

                    arquivo,

                    indent=4,

                    ensure_ascii=False

                )





    # =====================================
    # CARREGAR CONFIG
    # =====================================


    def carregar(self):


        with open(

            self.arquivo,

            "r",

            encoding="utf-8"

        ) as arquivo:


            return json.load(

                arquivo

            )





    # =====================================
    # ALTERAR CONFIG
    # =====================================


    def atualizar(

        self,

        chave,

        valor

    ):



        config = self.carregar()



        config[chave] = valor




        with open(

            self.arquivo,

            "w",

            encoding="utf-8"

        ) as arquivo:



            json.dump(

                config,

                arquivo,

                indent=4,

                ensure_ascii=False

            )





    # =====================================
    # CONSULTAR VALOR
    # =====================================


    def pegar(

        self,

        chave

    ):


        config = self.carregar()



        return config.get(

            chave

        )