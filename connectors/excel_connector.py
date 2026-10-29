import os

import xlwings as xw


def _normalized_path(value):
    return os.path.normcase(os.path.abspath(os.fspath(value)))


class ExcelConnector:
    def __init__(self):
        self.app = None
        self.book = None

    def conectar(self, arquivo):
        created_app = None
        stage = 'localizar planilha aberta'
        try:
            target = _normalized_path(arquivo)
            matches = []
            for app in xw.apps:
                for book in app.books:
                    if _normalized_path(book.fullname) == target:
                        matches.append((app, book))

            if len(matches) > 1:
                raise RuntimeError('Arquivo aberto em mais de uma instancia do Excel.')
            if matches:
                self.app, self.book = matches[0]
            else:
                stage = 'criar instancia do Excel'
                created_app = xw.App(visible=False)
                stage = 'abrir planilha na instancia criada'
                book = created_app.books.open(arquivo)
                self.app, self.book = created_app, book

            print('Excel conectado')
            return True
        except Exception as erro:
            if created_app is not None:
                try:
                    created_app.quit()
                except Exception:
                    pass
            self.app = None
            self.book = None
            print(f'Erro Excel ({stage}): {erro}')
            return False

    def ler_celula(self, aba, celula):
        try:
            return self.book.sheets[aba].range(celula).value
        except Exception:
            return None
