"""Explicit adapter from one external producer cycle to Bot presentation.

The adapter owns no provider, clock, cache or operational state.  Its caller
supplies the completed-cycle policy inputs explicitly.  The returned audit is
the only object passed to Bot.mostrar(), whose existing presentation seam
remains responsible only for rendering completed observational evidence.
"""

from analysis.research.intermarket_external_context_bridge import ExternalBridgeAudit


class ExternalObservationalPresentationCycle:
    NAME = "ExternalObservationalPresentationCycle"
    VERSION = "RC1"

    def __init__(self, producer):
        if not callable(getattr(producer, "produce", None)):
            raise TypeError("producer must expose produce()")
        self._producer = producer

    def produce_for_presentation(
        self,
        *,
        reference_timestamp,
        maximum_staleness_seconds,
        symbol_map=None,
    ) -> ExternalBridgeAudit:
        """Produce exactly one completed audit; never render or retain it."""
        audit = self._producer.produce(
            reference_timestamp=reference_timestamp,
            maximum_staleness_seconds=maximum_staleness_seconds,
            symbol_map=symbol_map,
        )
        if not isinstance(audit, ExternalBridgeAudit):
            raise TypeError("producer must return ExternalBridgeAudit")
        if audit.observational_only is not True:
            raise ValueError("presentation cycle accepts observational-only audit evidence")
        return audit

    def present(
        self,
        bot,
        context,
        *,
        reference_timestamp,
        maximum_staleness_seconds,
        symbol_map=None,
    ):
        """Run one explicit producer cycle and pass only its completed audit to Bot."""
        if not callable(getattr(bot, "mostrar", None)):
            raise TypeError("bot must expose mostrar()")

        audit = self.produce_for_presentation(
            reference_timestamp=reference_timestamp,
            maximum_staleness_seconds=maximum_staleness_seconds,
            symbol_map=symbol_map,
        )
        return bot.mostrar(
            context,
            external_audit=audit,
            external_presentation_enabled=True,
        )
