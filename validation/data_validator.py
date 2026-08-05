class DataValidator:


    def __init__(self):

        self.erros = []




    # =====================================
    # VALIDAR DADOS DE MERCADO
    # =====================================


    def validar(

        self,

        dados

    ):


        self.erros = []



        valido = True




        # ===============================
        # PREÇO
        # ===============================


        if dados is None:


            self.erros.append(

                "Dados vazios"

            )


            return False




        preco = dados.get(

            "close"

        )



        if preco is None:


            valido = False


            self.erros.append(

                "Preço inexistente"

            )



        elif preco <= 0:


            valido = False


            self.erros.append(

                "Preço inválido"

            )





        # ===============================
        # CANDLE
        # ===============================


        open_price = dados.get(

            "open"

        )


        high = dados.get(

            "high"

        )


        low = dados.get(

            "low"

        )




        if None in [

            open_price,

            high,

            low

        ]:


            valido = False


            self.erros.append(

                "Candle incompleto"

            )





        # ===============================
        # VALIDAÇÃO OHLC
        # ===============================


        if valido:


            if high < max(

                open_price,

                preco

            ):


                valido = False


                self.erros.append(

                    "Máxima inválida"

                )



            if low > min(

                open_price,

                preco

            ):


                valido = False


                self.erros.append(

                    "Mínima inválida"

                )





        # ===============================
        # VOLUME
        # ===============================


        volume = dados.get(

            "volume",

            0

        )



        if volume < 0:


            valido = False


            self.erros.append(

                "Volume inválido"

            )





        return valido





    # =====================================
    # RESULTADO
    # =====================================


    def resultado(self):


        return {


            "valido":

            len(self.erros) == 0,


            "erros":

            self.erros


        }