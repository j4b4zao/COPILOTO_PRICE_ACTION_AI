"""
risk/risk_manager.py

Risk Manager

<<<<<<< HEAD
RC10.1
=======
RC10.2
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1

Responsável por:

- validar a estratégia
- determinar entrada
- calcular stop estrutural
- identificar alvo estrutural
- considerar liquidez como objetivo
- calcular R:R real
- avaliar qualidade do risco
- aprovar ou rejeitar a operação

Regra importante do RC10.1:

Se existir um alvo estrutural identificável e ele
não oferecer o R:R mínimo, a operação será rejeitada.

O fallback de 2R somente será utilizado quando
NÃO existir alvo estrutural disponível.

Não executa ordens.
<<<<<<< HEAD
=======

Correção RC10.2:

- níveis estruturais SELL zerados ou negativos não contam como
  alvo encontrado e permitem o fallback quando não há alvo real.
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
"""

from ai.engine_base import EngineBase


class RiskManager(EngineBase):

    NAME = "RiskManager"

<<<<<<< HEAD
    VERSION = "RC10.1"
=======
    VERSION = "RC10.2"
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1

    ENABLED = True

    PRIORITY = 90

    # ==========================================================
    # CONFIGURAÇÃO
    # ==========================================================

    MIN_RISK_REWARD = 1.50

    FALLBACK_RISK_REWARD = 2.00

    MAX_STOP_DISTANCE = 500.0

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        risk = context.risk

        strategy = context.strategy

        market = context.market

        structure = context.structure

        liquidity = context.liquidity

        order_block = context.order_block

        fair_value_gap = context.fair_value_gap

        risk.clear()

        # ======================================================
        # ESTRATÉGIA
        # ======================================================

        if not strategy.valid:

            risk.add_reason(
                "Nenhum setup válido."
            )

            return context

        # ======================================================
        # DIREÇÃO
        # ======================================================

        direction = str(
            strategy.signal
        ).upper()

        if direction not in (
            "BUY",
            "SELL",
        ):

            risk.add_reason(
                "Direção da estratégia inválida."
            )

            return context

        # ======================================================
        # ENTRADA
        # ======================================================

        entry = self._get_entry_price(
            market,
            order_block,
        )

        if entry <= 0:

            risk.add_reason(
                "Preço de entrada inválido."
            )

            return context

        risk.entry_price = entry

        # ======================================================
        # STOP
        # ======================================================

        if direction == "BUY":

            stop = self._calculate_buy_stop(
                entry,
                order_block,
                fair_value_gap,
                liquidity,
            )

            if stop <= 0 or stop >= entry:

                risk.add_reason(
                    "Stop BUY inválido."
                )

                return context

        else:

            stop = self._calculate_sell_stop(
                entry,
                order_block,
                fair_value_gap,
                liquidity,
            )

            if stop <= entry:

                risk.add_reason(
                    "Stop SELL inválido."
                )

                return context

        risk.stop_loss = stop

        # ======================================================
        # DISTÂNCIA DE RISCO
        # ======================================================

        risk_distance = abs(
            risk.entry_price -
            risk.stop_loss
        )

        if risk_distance <= 0:

            risk.add_reason(
                "Distância de risco inválida."
            )

            return context

        if risk_distance > self.MAX_STOP_DISTANCE:

            risk.add_reason(
                "Stop estrutural excessivamente distante."
            )

            return context

        # ======================================================
        # TARGET ESTRUTURAL
        #
        # Retorna:
        #
        # target
        # source
        # structural_found
        # ======================================================

        (
            target,
            target_source,
            structural_found,
        ) = self._calculate_structural_target(
            context,
            entry,
            stop,
            direction,
        )

        # ======================================================
        # REGRA RC10.1
        #
        # Se encontrou estrutura mas nenhum alvo estrutural
        # possui R:R mínimo, NÃO usar fallback.
        # ======================================================

        if structural_found:

            if target <= 0:

                risk.add_reason(
                    "Alvo estrutural encontrado, "
                    "mas não existe nível válido."
                )

                risk.risk_level = "HIGH"

                risk.approved = False

                risk.valid = False

                risk.confidence = 0.0

                return context

            # --------------------------------------------------
            # VALIDAÇÃO DO TARGET ESTRUTURAL
            # --------------------------------------------------

            if direction == "BUY":

                if target <= entry:

                    risk.add_reason(
                        "Alvo estrutural BUY inválido."
                    )

                    risk.risk_level = "HIGH"

                    risk.approved = False

                    risk.valid = False

                    risk.confidence = 0.0

                    return context

            else:

                if target >= entry:

                    risk.add_reason(
                        "Alvo estrutural SELL inválido."
                    )

                    risk.risk_level = "HIGH"

                    risk.approved = False

                    risk.valid = False

                    risk.confidence = 0.0

                    return context

            # --------------------------------------------------
            # R:R ESTRUTURAL
            # --------------------------------------------------

            reward_distance = abs(
                target - entry
            )

            structural_rr = (
                reward_distance /
                risk_distance
            )

            risk.take_profit = target

            risk.risk_reward = structural_rr

            # --------------------------------------------------
            # R:R INSUFICIENTE
            # --------------------------------------------------

            if (
                structural_rr
                <
                self.MIN_RISK_REWARD
            ):

                risk.risk_level = "HIGH"

                risk.approved = False

                risk.valid = False

                risk.risk_score = 0.0

                risk.confidence = 0.0

                risk.add_reason(
                    f"Alvo estrutural: "
                    f"{target:.2f}"
                )

                risk.add_reason(
                    f"Fonte do alvo: "
                    f"{target_source}"
                )

                risk.add_reason(
                    f"R:R estrutural "
                    f"{structural_rr:.2f}"
                )

                risk.add_reason(
                    f"R:R mínimo "
                    f"{self.MIN_RISK_REWARD:.2f}"
                )

                risk.add_reason(
                    "Operação rejeitada: "
                    "alvo estrutural não oferece "
                    "relação risco/retorno suficiente."
                )

                return context

        # ======================================================
        # SEM TARGET ESTRUTURAL
        #
        # Somente aqui podemos utilizar fallback 2R.
        # ======================================================

        else:

            target = (
                self._calculate_fallback_target(
                    entry,
                    stop,
                    direction,
                )
            )

            target_source = "FALLBACK_RR"

            risk.take_profit = target

            reward_distance = abs(
                target - entry
            )

            risk.risk_reward = (
                reward_distance /
                risk_distance
            )

        # ======================================================
        # VALIDAÇÃO FINAL DO TARGET
        # ======================================================

        if direction == "BUY":

            if risk.take_profit <= entry:

                risk.add_reason(
                    "Alvo BUY inválido."
                )

                return context

        else:

            if risk.take_profit >= entry:

                risk.add_reason(
                    "Alvo SELL inválido."
                )

                return context

        # ======================================================
        # R:R MÍNIMO FINAL
        # ======================================================

        if (
            risk.risk_reward
            <
            self.MIN_RISK_REWARD
        ):

            risk.risk_level = "HIGH"

            risk.approved = False

            risk.valid = False

            risk.risk_score = 0.0

            risk.confidence = 0.0

            risk.add_reason(
                f"R:R insuficiente: "
                f"{risk.risk_reward:.2f}"
            )

            return context

        # ======================================================
        # SCORE DE RISCO
        # ======================================================

        risk.risk_score = (
            self._calculate_risk_score(
                context,
                direction,
            )
        )

        # ======================================================
        # CLASSIFICAÇÃO
        # ======================================================

        if risk.risk_score >= 85:

            risk.risk_level = "LOW"

        elif risk.risk_score >= 70:

            risk.risk_level = "MEDIUM"

        else:

            risk.risk_level = "HIGH"

        # ======================================================
        # APROVAÇÃO
        # ======================================================

        risk.approved = (

            risk.risk_score >= 70

            and

            risk.risk_reward
            >=
            self.MIN_RISK_REWARD

        )

        risk.valid = risk.approved

        risk.confidence = (
            risk.risk_score / 100.0
        )

        # ======================================================
        # CONFLUÊNCIAS
        # ======================================================

        risk.confluences = (
            self._count_confluences(
                context,
                direction,
            )
        )

        # ======================================================
        # MOTIVOS
        # ======================================================

        risk.add_reason(
            f"Entrada "
            f"{risk.entry_price:.2f}"
        )

        risk.add_reason(
            f"Stop "
            f"{risk.stop_loss:.2f}"
        )

        risk.add_reason(
            f"Alvo "
            f"{risk.take_profit:.2f}"
        )

        risk.add_reason(
            f"Fonte do alvo: "
            f"{target_source}"
        )

        risk.add_reason(
            f"R:R "
            f"{risk.risk_reward:.2f}"
        )

        risk.add_reason(
            f"Risk Score "
            f"{risk.risk_score:.0f}"
        )

        risk.add_reason(
            f"Confluências "
            f"{risk.confluences}"
        )

        if risk.approved:

            risk.add_reason(
                "Risco aprovado."
            )

        else:

            risk.add_reason(
                "Risco não aprovado."
            )

        return context

    # ==========================================================
    # ENTRADA
    # ==========================================================

    @staticmethod
    def _get_entry_price(
        market,
        order_block,
    ):

        price = float(
            getattr(
                market,
                "last_price",
                0.0,
            )
            or 0.0
        )

        if price > 0:

            return price

        return float(
            getattr(
                order_block,
                "entry_price",
                0.0,
            )
            or 0.0
        )

    # ==========================================================
    # STOP BUY
    # ==========================================================

    @staticmethod
    def _calculate_buy_stop(
        entry,
        order_block,
        fair_value_gap,
        liquidity,
    ):

        candidates = []

        if (
            getattr(
                order_block,
                "valid",
                False,
            )
            and
            getattr(
                order_block,
                "bullish",
                False,
            )
        ):

            low = float(
                getattr(
                    order_block,
                    "low",
                    0.0,
                )
                or 0.0
            )

            if low > 0:

                candidates.append(
                    low
                )

        if (
            getattr(
                fair_value_gap,
                "valid",
                False,
            )
            and
            getattr(
                fair_value_gap,
                "bullish",
                False,
            )
        ):

            low = float(
                getattr(
                    fair_value_gap,
                    "low",
                    0.0,
                )
                or 0.0
            )

            if low > 0:

                candidates.append(
                    low
                )

        if getattr(
            liquidity,
            "sweep_down",
            False,
        ):

            price = float(
                getattr(
                    liquidity,
                    "liquidity_price",
                    0.0,
                )
                or 0.0
            )

            if price > 0:

                candidates.append(
                    price
                )

        if not candidates:

            return 0.0

        valid = [
            price
            for price in candidates
            if price < entry
        ]

        if not valid:

            return 0.0

        # Para BUY, o stop protetor deve ser o nível válido
        # mais próximo da entrada. Escolher o menor nível
        # aumentaria desnecessariamente a distância de risco.
        #
        # Exemplo deste cenário:
        #
        # entry = 172400
        # liquidity = 172100
        # estrutura/OB/FVG podem estar em 170000
        #
        # O stop correto entre os níveis válidos é 172100.
        return max(valid)

    # ==========================================================
    # STOP SELL
    # ==========================================================

    @staticmethod
    def _calculate_sell_stop(
        entry,
        order_block,
        fair_value_gap,
        liquidity,
    ):

        candidates = []

        if (
            getattr(
                order_block,
                "valid",
                False,
            )
            and
            getattr(
                order_block,
                "bearish",
                False,
            )
        ):

            high = float(
                getattr(
                    order_block,
                    "high",
                    0.0,
                )
                or 0.0
            )

            if high > 0:

                candidates.append(
                    high
                )

        if (
            getattr(
                fair_value_gap,
                "valid",
                False,
            )
            and
            getattr(
                fair_value_gap,
                "bearish",
                False,
            )
        ):

            high = float(
                getattr(
                    fair_value_gap,
                    "high",
                    0.0,
                )
                or 0.0
            )

            if high > 0:

                candidates.append(
                    high
                )

        if getattr(
            liquidity,
            "sweep_up",
            False,
        ):

            price = float(
                getattr(
                    liquidity,
                    "liquidity_price",
                    0.0,
                )
                or 0.0
            )

            if price > 0:

                candidates.append(
                    price
                )

        if not candidates:

            return 0.0

        valid = [
            price
            for price in candidates
            if price > entry
        ]

        if not valid:

            return 0.0

        # Para SELL, o stop protetor deve ser o nível válido
        # mais próximo da entrada. Assim, entre os níveis acima
        # da entrada, escolhemos o menor.
        return min(valid)

    # ==========================================================
    # TARGET ESTRUTURAL
    # ==========================================================

    def _calculate_structural_target(
        self,
        context,
        entry,
        stop,
        direction,
    ):

        structure = context.structure

        liquidity = context.liquidity

        risk_distance = abs(
            entry - stop
        )

        minimum_target_distance = (
            risk_distance *
            self.MIN_RISK_REWARD
        )

        candidates = []

        # ======================================================
        # BUY
        # ======================================================

        if direction == "BUY":

            for field in (
                "last_high",
                "swing_high",
            ):

                value = float(
                    getattr(
                        structure,
                        field,
                        0.0,
                    )
                    or 0.0
                )

                if value > entry:

                    candidates.append(
                        (
                            value,
                            f"STRUCTURE_{field.upper()}",
                        )
                    )

            liquidity_price = float(
                getattr(
                    liquidity,
                    "liquidity_price",
                    0.0,
                )
                or 0.0
            )

            if liquidity_price > entry:

                candidates.append(
                    (
                        liquidity_price,
                        "LIQUIDITY",
                    )
                )

            # --------------------------------------------------
            # NENHUM ALVO ESTRUTURAL
            # --------------------------------------------------

            if not candidates:

                return (
                    0.0,
                    "NONE",
                    False,
                )

            # --------------------------------------------------
            # ALVOS QUE RESPEITAM R:R
            # --------------------------------------------------

            valid = [
                item
                for item in candidates
                if (
                    item[0] - entry
                    >=
                    minimum_target_distance
                )
            ]

            if valid:

                # Menor alvo que ainda respeita R:R.
                selected = min(
                    valid,
                    key=lambda item: item[0],
                )

                return (
                    selected[0],
                    selected[1],
                    True,
                )

            # --------------------------------------------------
            # EXISTE ESTRUTURA, MAS NENHUM ALVO
            # POSSUI R:R SUFICIENTE.
            #
            # Retorna o alvo estrutural mais próximo para
            # que executar() possa rejeitar corretamente.
            # --------------------------------------------------

            nearest = min(
                candidates,
                key=lambda item: item[0],
            )

            return (
                nearest[0],
                nearest[1],
                True,
            )

        # ======================================================
        # SELL
        # ======================================================

        for field in (
            "last_low",
            "swing_low",
        ):

            value = float(
                getattr(
                    structure,
                    field,
                    0.0,
                )
                or 0.0
            )

<<<<<<< HEAD
            if value < entry:
=======
            if 0.0 < value < entry:
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1

                candidates.append(
                    (
                        value,
                        f"STRUCTURE_{field.upper()}",
                    )
                )

        liquidity_price = float(
            getattr(
                liquidity,
                "liquidity_price",
                0.0,
            )
            or 0.0
        )

        if (
            liquidity_price > 0
            and
            liquidity_price < entry
        ):

            candidates.append(
                (
                    liquidity_price,
                    "LIQUIDITY",
                )
            )

        # ------------------------------------------------------
        # NENHUM ALVO ESTRUTURAL
        # ------------------------------------------------------

        if not candidates:

            return (
                0.0,
                "NONE",
                False,
            )

        # ------------------------------------------------------
        # ALVOS QUE RESPEITAM R:R
        # ------------------------------------------------------

        valid = [
            item
            for item in candidates
            if (
                entry - item[0]
                >=
                minimum_target_distance
            )
        ]

        if valid:

            # Maior alvo abaixo da entrada que ainda
            # respeita o R:R mínimo.
            selected = max(
                valid,
                key=lambda item: item[0],
            )

            return (
                selected[0],
                selected[1],
                True,
            )

        # ------------------------------------------------------
        # EXISTE ESTRUTURA, MAS NENHUM ALVO
        # POSSUI R:R SUFICIENTE.
        # ------------------------------------------------------

        nearest = max(
            candidates,
            key=lambda item: item[0],
        )

        return (
            nearest[0],
            nearest[1],
            True,
        )

    # ==========================================================
    # TARGET FALLBACK
    # ==========================================================

    def _calculate_fallback_target(
        self,
        entry,
        stop,
        direction,
    ):

        risk_distance = abs(
            entry - stop
        )

        reward_distance = (
            risk_distance *
            self.FALLBACK_RISK_REWARD
        )

        if direction == "BUY":

            return (
                entry +
                reward_distance
            )

        return (
            entry -
            reward_distance
        )

    # ==========================================================
    # SCORE DE RISCO
    # ==========================================================

    def _calculate_risk_score(
        self,
        context,
        direction,
    ):

        score = 0.0

        strategy = context.strategy

        volume = context.volume

        liquidity = context.liquidity

        structure = context.structure

        order_block = context.order_block

        fair_value_gap = context.fair_value_gap

        # ------------------------------------------------------
        # STRATEGY
        # ------------------------------------------------------

        if strategy.score >= 95:

            score += 30

        elif strategy.score >= 90:

            score += 27

        elif strategy.score >= 80:

            score += 23

        elif strategy.score >= 70:

            score += 18

        else:

            score += 10

        # ------------------------------------------------------
        # ESTRUTURA
        # ------------------------------------------------------

        if direction == "BUY":

            if structure.bos_up:

                score += 15

            elif structure.trend.name == "UP":

                score += 10

        else:

            if structure.bos_down:

                score += 15

            elif structure.trend.name == "DOWN":

                score += 10

        # ------------------------------------------------------
        # ORDER BLOCK
        # ------------------------------------------------------

        if (
            order_block.valid
            and
            (
                (
                    direction == "BUY"
                    and order_block.bullish
                )
                or
                (
                    direction == "SELL"
                    and order_block.bearish
                )
            )
            and
            not order_block.mitigated
        ):

            score += 15

        # ------------------------------------------------------
        # FVG
        # ------------------------------------------------------

        if (
            fair_value_gap.valid
            and
            (
                (
                    direction == "BUY"
                    and fair_value_gap.bullish
                )
                or
                (
                    direction == "SELL"
                    and fair_value_gap.bearish
                )
            )
            and
            not fair_value_gap.filled
        ):

            score += 10

        # ------------------------------------------------------
        # VOLUME
        # ------------------------------------------------------

        if volume.high:

            score += 10

        elif volume.medium:

            score += 5

        # ------------------------------------------------------
        # LIQUIDEZ DIRECIONAL
        # ------------------------------------------------------

        if direction == "BUY":

            if liquidity.buy_side:

                score += 5

            if liquidity.sell_side:

                score -= 5

        else:

            if liquidity.sell_side:

                score += 5

            if liquidity.buy_side:

                score -= 5

        # ------------------------------------------------------
        # LIMITE
        # ------------------------------------------------------

        return min(
            max(
                score,
                0.0,
            ),
            100.0,
        )

    # ==========================================================
    # CONFLUÊNCIAS
    # ==========================================================

    @staticmethod
    def _count_confluences(
        context,
        direction,
    ):

        count = 0

        strategy = context.strategy

        structure = context.structure

        liquidity = context.liquidity

        order_block = context.order_block

        fair_value_gap = context.fair_value_gap

        volume = context.volume

        # ------------------------------------------------------
        # ESTRATÉGIA
        # ------------------------------------------------------

        if strategy.valid:

            count += 1

        # ------------------------------------------------------
        # ESTRUTURA
        # ------------------------------------------------------

        if direction == "BUY":

            if (
                structure.hh
                or structure.hl
                or structure.bos_up
            ):

                count += 1

        else:

            if (
                structure.lh
                or structure.ll
                or structure.bos_down
            ):

                count += 1

        # ------------------------------------------------------
        # LIQUIDEZ
        # ------------------------------------------------------

        if direction == "BUY":

            if (
                liquidity.buy_side
                or liquidity.sweep_down
            ):

                count += 1

        else:

            if (
                liquidity.sell_side
                or liquidity.sweep_up
            ):

                count += 1

        # ------------------------------------------------------
        # ORDER BLOCK
        # ------------------------------------------------------

        if (
            order_block.valid
            and
            (
                (
                    direction == "BUY"
                    and order_block.bullish
                )
                or
                (
                    direction == "SELL"
                    and order_block.bearish
                )
            )
        ):

            count += 1

        # ------------------------------------------------------
        # FVG
        # ------------------------------------------------------

        if (
            fair_value_gap.valid
            and
            (
                (
                    direction == "BUY"
                    and fair_value_gap.bullish
                )
                or
                (
                    direction == "SELL"
                    and fair_value_gap.bearish
                )
            )
        ):

            count += 1

        # ------------------------------------------------------
        # VOLUME
        # ------------------------------------------------------

        if volume.high:

            count += 1

        elif volume.medium:

            count += 1

<<<<<<< HEAD
        return count
=======
        return count
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
