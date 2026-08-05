import sys
import os

# adiciona a raiz do projeto
sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)


from core.engine import CopilotEngine
from app.bot import analisar



motor = CopilotEngine(
    intervalo=2
)



motor.iniciar(
    analisar
)