from datetime import datetime
import sys

from core.settings import DEBUG


class Logger:

    def __init__(self, ativo=True):
        self.ativo = ativo

    def _timestamp(self):
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def _log(self, nivel, mensagem, erro=False):

        if not self.ativo:
            return

        texto = f"[{self._timestamp()}] [{nivel}] {mensagem}"

        if erro:
            print(texto, file=sys.stderr)
        else:
            print(texto)

    def info(self, mensagem):
        self._log("INFO", mensagem)

    def sucesso(self, mensagem):
        self._log("OK", mensagem)

    def warning(self, mensagem):
        self._log("WARNING", mensagem)

    def erro(self, mensagem):
        self._log("ERRO", mensagem, erro=True)

    def debug(self, mensagem):

        if DEBUG:
            self._log("DEBUG", mensagem)

    def linha(self):
        if self.ativo:
            print("-" * 60)

    def titulo(self, texto):
        if self.ativo:
            print("\n" + "=" * 60)
            print(texto)
            print("=" * 60)


logger = Logger()