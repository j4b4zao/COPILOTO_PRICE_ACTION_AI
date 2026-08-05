from datetime import datetime



class Scheduler:


    def __init__(self, config_manager=None):


        self.config = config_manager


        self.ativo = False



    # =====================================
    # VERIFICAR HORÁRIO
    # =====================================


    def mercado_aberto(self):


        agora = datetime.now().time()



        inicio = "09:00"

        fim = "17:00"



        if self.config:


            inicio = self.config.pegar(

                "horario_inicio"

            )


            fim = self.config.pegar(

                "horario_fim"

            )




        hora_inicio = datetime.strptime(

            inicio,

            "%H:%M"

        ).time()



        hora_fim = datetime.strptime(

            fim,

            "%H:%M"

        ).time()




        return (

            agora >= hora_inicio

            and

            agora <= hora_fim

        )





    # =====================================
    # INICIAR
    # =====================================


    def iniciar(self):


        if self.mercado_aberto():


            self.ativo = True


            return {


                "status":

                "OPERANDO",


                "hora":

                datetime.now().strftime(

                    "%H:%M:%S"

                )


            }





        else:


            self.ativo = False


            return {


                "status":

                "FORA_DO_HORARIO"



            }





    # =====================================
    # PARAR
    # =====================================


    def parar(self):


        self.ativo = False



        return {


            "status":

            "ENCERRADO",


            "hora":

            datetime.now().strftime(

                "%H:%M:%S"

            )

        }