from datetime import datetime, timedelta



class ConnectionManager:


    def __init__(self):

        self.conectado = False

        self.ultima_atualizacao = None

        self.timeout = 10




    # =====================================
    # REGISTRAR DADOS RECEBIDOS
    # =====================================

    def atualizar(self):


        self.conectado = True


        self.ultima_atualizacao = datetime.now()




    # =====================================
    # VERIFICAR CONEXÃO
    # =====================================

    def verificar(self):


        if self.ultima_atualizacao is None:


            return {


                "status":"SEM_DADOS",


                "conectado":False


            }




        diferenca = (

            datetime.now()

            -

            self.ultima_atualizacao

        )




        if diferenca > timedelta(

            seconds=self.timeout

        ):


            self.conectado = False




        return {


            "status":

            "ATIVA"

            if self.conectado

            else

            "PERDIDA",



            "conectado":

            self.conectado,



            "ultima_atualizacao":

            self.ultima_atualizacao.strftime(

                "%H:%M:%S"

            )



        }




    # =====================================
    # FORÇAR DESCONECTAR
    # =====================================

    def desconectar(self):


        self.conectado = False



        return {


            "status":

            "DESCONECTADO"



        }