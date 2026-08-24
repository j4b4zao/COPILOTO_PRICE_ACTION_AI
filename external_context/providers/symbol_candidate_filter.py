"""
external_context/providers/symbol_candidate_filter.py

Filtro semântico inicial dos candidatos encontrados
pelo provider.

RC2.3

Responsabilidade:

- receber candidatos do Discovery;
- verificar tipo do instrumento;
- verificar país;
- verificar palavras-chave do nome;
- NÃO selecionar automaticamente um símbolo.

O filtro apenas reduz o universo de candidatos.
"""

from external_context.providers.instrument_profiles import (
    InstrumentProfiles,
)


class SymbolCandidateFilter:

    NAME = "SymbolCandidateFilter"

    VERSION = "RC2.3"

    def __init__(self):

        self.last_internal_symbol = ""

        self.last_candidates = []

        self.last_accepted = []

        self.last_rejected = []

        self.last_reason = ""

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.last_internal_symbol = ""

        self.last_candidates.clear()

        self.last_accepted.clear()

        self.last_rejected.clear()

        self.last_reason = ""

    # ==========================================================
    # FILTER
    # ==========================================================

    def filter(
        self,
        internal_symbol: str,
        candidates: list[dict],
    ) -> list[dict]:

        self.clear()

        internal_symbol = str(
            internal_symbol
        ).strip().upper()

        self.last_internal_symbol = (
            internal_symbol
        )

        if not internal_symbol:

            self.last_reason = (
                "Símbolo interno vazio."
            )

            return []

        if not isinstance(
            candidates,
            list,
        ):

            self.last_reason = (
                "Lista de candidatos inválida."
            )

            return []

        self.last_candidates = list(
            candidates
        )

        profile = (
            InstrumentProfiles.get(
                internal_symbol
            )
        )

        if profile is None:

            self.last_reason = (
                "Perfil de instrumento "
                "não encontrado."
            )

            return []

        allowed_types = {
            str(value).strip().upper()
            for value in profile[
                "allowed_types"
            ]
        }

        allowed_countries = {
            str(value).strip().upper()
            for value in profile[
                "allowed_countries"
            ]
        }

        name_keywords = [
            str(value).strip().upper()
            for value in profile[
                "name_keywords"
            ]
        ]

        for candidate in candidates:

            if not isinstance(
                candidate,
                dict,
            ):

                self.last_rejected.append(
                    {
                        "candidate": candidate,
                        "reason": (
                            "Candidato inválido."
                        ),
                    }
                )

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

            instrument_type = str(
                candidate.get(
                    "type",
                    "",
                )
            ).strip()

            country = str(
                candidate.get(
                    "country",
                    "",
                )
            ).strip()

            type_ok = (
                instrument_type.upper()
                in allowed_types
            )

            country_ok = (
                country.upper()
                in allowed_countries
            )

            name_upper = name.upper()

            keyword_ok = any(
                keyword
                in name_upper
                for keyword
                in name_keywords
                if keyword
            )

            reasons = []

            if not type_ok:

                reasons.append(
                    "tipo incompatível"
                )

            if not country_ok:

                reasons.append(
                    "país incompatível"
                )

            if not keyword_ok:

                reasons.append(
                    "nome incompatível"
                )

            if (
                type_ok
                and country_ok
                and keyword_ok
            ):

                self.last_accepted.append(
                    candidate
                )

            else:

                self.last_rejected.append(
                    {
                        "candidate": candidate,
                        "reason": (
                            "; ".join(
                                reasons
                            )
                        ),
                    }
                )

        if self.last_accepted:

            self.last_reason = (
                "Candidatos compatíveis "
                "encontrados."
            )

        else:

            self.last_reason = (
                "Nenhum candidato "
                "compatível encontrado."
            )

        return list(
            self.last_accepted
        )

    # ==========================================================
    # ACCEPTED
    # ==========================================================

    def accepted(
        self,
    ) -> list[dict]:

        return list(
            self.last_accepted
        )

    # ==========================================================
    # REJECTED
    # ==========================================================

    def rejected(
        self,
    ) -> list[dict]:

        return list(
            self.last_rejected
        )

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(
        self,
    ) -> int:

        return len(
            self.last_accepted
        )

    # ==========================================================
    # COMPLETE SNAPSHOT
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
            "candidate_count": len(
                self.last_candidates
            ),
            "accepted_count": len(
                self.last_accepted
            ),
            "rejected_count": len(
                self.last_rejected
            ),
            "accepted": list(
                self.last_accepted
            ),
            "rejected": list(
                self.last_rejected
            ),
            "reason": (
                self.last_reason
            ),
        }