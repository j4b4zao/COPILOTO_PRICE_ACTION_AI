"""
external_context/providers/semantic_symbol_resolver.py

Resolve semanticamente candidatos previamente filtrados.

RC2.3

Responsabilidade:

- receber candidatos compatíveis;
- avaliar o nome do instrumento;
- calcular confiança;
- retornar MAPPED somente quando houver
  evidência suficiente;
- bloquear ambiguidades.

O resolver NÃO consulta a API.
"""

from external_context.providers.instrument_profiles import (
    InstrumentProfiles,
)


class SemanticSymbolResolver:

    NAME = "SemanticSymbolResolver"

    VERSION = "RC2.3"

    STATUS_MAPPED = "MAPPED"

    STATUS_UNRESOLVED = "UNRESOLVED"

    STATUS_AMBIGUOUS = "AMBIGUOUS"

    def __init__(
        self,
        min_confidence: float = 0.80,
    ):

        self.min_confidence = float(
            min_confidence
        )

        self.last_internal_symbol = ""

        self.last_status = ""

        self.last_symbol = None

        self.last_confidence = 0.0

        self.last_reason = ""

        self.last_candidates = []

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.last_internal_symbol = ""

        self.last_status = ""

        self.last_symbol = None

        self.last_confidence = 0.0

        self.last_reason = ""

        self.last_candidates.clear()

    # ==========================================================
    # RESOLVE
    # ==========================================================

    def resolve(
        self,
        internal_symbol: str,
        candidates: list[dict],
    ) -> dict:

        self.clear()

        internal_symbol = str(
            internal_symbol
        ).strip().upper()

        self.last_internal_symbol = (
            internal_symbol
        )

        if not internal_symbol:

            self.last_status = (
                self.STATUS_UNRESOLVED
            )

            self.last_reason = (
                "Símbolo interno vazio."
            )

            return self.snapshot()

        if not isinstance(
            candidates,
            list,
        ):

            self.last_status = (
                self.STATUS_UNRESOLVED
            )

            self.last_reason = (
                "Lista de candidatos inválida."
            )

            return self.snapshot()

        self.last_candidates = list(
            candidates
        )

        if not candidates:

            self.last_status = (
                self.STATUS_UNRESOLVED
            )

            self.last_reason = (
                "Nenhum candidato compatível."
            )

            return self.snapshot()

        profile = (
            InstrumentProfiles.get(
                internal_symbol
            )
        )

        if profile is None:

            self.last_status = (
                self.STATUS_UNRESOLVED
            )

            self.last_reason = (
                "Perfil de instrumento "
                "não encontrado."
            )

            return self.snapshot()

        scored = []

        keywords = [
            str(keyword).strip().upper()
            for keyword
            in profile[
                "name_keywords"
            ]
        ]

        for candidate in candidates:

            if not isinstance(
                candidate,
                dict,
            ):

                continue

            symbol = str(
                candidate.get(
                    "symbol",
                    "",
                )
            ).strip()

            name = str(
                candidate.get(
                    "name",
                    "",
                )
            ).strip()

            if not symbol:

                continue

            name_upper = name.upper()

            matches = [
                keyword
                for keyword in keywords
                if keyword
                and keyword
                in name_upper
            ]

            if not matches:

                confidence = 0.0

            else:

                confidence = min(
                    1.0,
                    len(matches)
                    / max(
                        1,
                        len(keywords),
                    ),
                )

            scored.append(
                {
                    "candidate": candidate,
                    "confidence": confidence,
                    "matches": matches,
                }
            )

        if not scored:

            self.last_status = (
                self.STATUS_UNRESOLVED
            )

            self.last_reason = (
                "Nenhum candidato possui "
                "símbolo válido."
            )

            return self.snapshot()

        scored.sort(
            key=lambda item:
                item["confidence"],
            reverse=True,
        )

        best = scored[0]

        best_confidence = float(
            best["confidence"]
        )

        self.last_confidence = (
            best_confidence
        )

        # ======================================================
        # AMBIGUIDADE
        # ======================================================

        if len(scored) > 1:

            second = scored[1]

            second_confidence = float(
                second["confidence"]
            )

            if (
                best_confidence
                == second_confidence
                and best_confidence
                >= self.min_confidence
            ):

                self.last_status = (
                    self.STATUS_AMBIGUOUS
                )

                self.last_reason = (
                    "Múltiplos candidatos "
                    "possuem a mesma confiança."
                )

                return self.snapshot()

        # ======================================================
        # CONFIANÇA INSUFICIENTE
        # ======================================================

        if (
            best_confidence
            < self.min_confidence
        ):

            self.last_status = (
                self.STATUS_UNRESOLVED
            )

            self.last_reason = (
                "Confiança insuficiente para "
                "seleção automática."
            )

            return self.snapshot()

        # ======================================================
        # MAPPED
        # ======================================================

        candidate = best[
            "candidate"
        ]

        self.last_symbol = str(
            candidate.get(
                "symbol",
            )
        ).strip()

        self.last_status = (
            self.STATUS_MAPPED
        )

        self.last_reason = (
            "Candidato resolvido com "
            "confiança suficiente."
        )

        return self.snapshot()

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict:

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "internal_symbol": (
                self.last_internal_symbol
            ),
            "status": (
                self.last_status
            ),
            "symbol": (
                self.last_symbol
            ),
            "confidence": (
                self.last_confidence
            ),
            "reason": (
                self.last_reason
            ),
            "candidate_count": len(
                self.last_candidates
            ),
        }