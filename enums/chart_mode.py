"""Modos de construção do gráfico principal."""

from enum import Enum


class ChartMode(Enum):

    NORMAL = "NORMAL"

    RENKO = "RENKO"

    @classmethod
    def normalize(cls, value):

        if isinstance(value, cls):

            return value

        normalized = str(value).strip().upper()

        try:

            return cls(normalized)

        except ValueError as error:

            supported = ", ".join(
                mode.value for mode in cls
            )

            raise ValueError(
                f"Modo de gráfico {value!r} inválido. "
                f"Use: {supported}."
            ) from error
