import xlwings as xw


class ExcelConnector:


    def __init__(self):

        self.app = None
        self.book = None



    def conectar(self, arquivo):

        try:

            self.app = xw.App(
                visible=False
            )


            self.book = xw.Book(
                arquivo
            )


            print("Excel conectado")


            return True


        except Exception as erro:

            print(
                "Erro Excel:",
                erro
            )

            return False



    def ler_celula(self, aba, celula):

        try:

            valor = self.book.sheets[aba].range(celula).value

            return valor


        except:

            return None