"""Manual, explicit activation facade for one external observational cycle.

RC1 does not select providers, read clocks, create policies, bootstrap Bot, or
join Bot.executar().  It is only a caller-controlled activation gate around an
already configured ExternalObservationalCycleBoundary.
"""

from external_context.external_observational_cycle_boundary import (
    ExternalObservationalCycleBoundary,
    ExternalObservationalCyclePolicy,
)


class ExternalObservationalManualActivation:
    NAME = "ExternalObservationalManualActivation"
    VERSION = "RC1"

    def __init__(self, boundary):
        if not isinstance(boundary, ExternalObservationalCycleBoundary):
            raise TypeError("boundary must be ExternalObservationalCycleBoundary")
        self._boundary = boundary

    @staticmethod
    def _require_enabled(enabled):
        if enabled is not True:
            if enabled is False:
                raise PermissionError("external observational activation is disabled")
            raise TypeError("enabled must be an exact bool set to True")

    def produce(self, policy: ExternalObservationalCyclePolicy, *, enabled=False):
        """Produce one audit only after the explicit activation gate opens."""
        self._require_enabled(enabled)
        if not isinstance(policy, ExternalObservationalCyclePolicy):
            raise TypeError("policy must be ExternalObservationalCyclePolicy")
        return self._boundary.produce(policy)

    def present(
        self,
        bot,
        context,
        policy: ExternalObservationalCyclePolicy,
        *,
        enabled=False,
    ):
        """Present one explicit observational cycle; never alters Bot runtime."""
        self._require_enabled(enabled)
        if not isinstance(policy, ExternalObservationalCyclePolicy):
            raise TypeError("policy must be ExternalObservationalCyclePolicy")
        if not callable(getattr(bot, "mostrar", None)):
            raise TypeError("bot must expose mostrar()")
        return self._boundary.present(bot, context, policy)
