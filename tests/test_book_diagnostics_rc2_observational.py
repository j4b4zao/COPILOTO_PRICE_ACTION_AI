import inspect

from ai.score_engine import ScoreEngine
from analysis.analysis_pipeline import AnalysisPipeline
from analysis.book_diagnostics_engine import BookDiagnosticsEngine
from analysis.price_action.price_action import PriceAction
from brain.context_engine import ContextEngine
from core.analysis_context import AnalysisContext
from core.event_types import EventType
from decision.decision_engine import DecisionEngine
from models.book_diagnostics_result import BookDiagnosticsResult
from risk.risk_manager import RiskManager


def test_analysis_context_owns_book_diagnostics_result():
    context = AnalysisContext()

    assert isinstance(
        context.book_diagnostics,
        BookDiagnosticsResult,
    )
    assert context.book_diagnostics.passive_only is True


def test_clear_results_resets_book_diagnostics():
    context = AnalysisContext()

    context.book_diagnostics.always_in["direction"] = "BUY"
    context.book_diagnostics.directional_bias = "BUY"
    context.book_diagnostics.alignment = "ALIGNED"
    context.book_diagnostics.quality_score = 91.0

    context.clear_results()

    result = context.book_diagnostics

    assert result.passive_only is True
    assert result.always_in == {}
    assert result.directional_bias == "NONE"
    assert result.alignment == "NEUTRAL"
    assert result.quality_score == 0.0


def test_pipeline_registers_book_diagnostics_after_price_action():
    pipeline = AnalysisPipeline()

    types = [type(engine) for engine in pipeline.engines]

    assert BookDiagnosticsEngine in types
    assert types.index(BookDiagnosticsEngine) > types.index(PriceAction)
    assert types.index(BookDiagnosticsEngine) < types.index(ContextEngine)


def test_book_diagnostics_has_observational_event():
    assert (
        EventType.BOOK_DIAGNOSTICS_UPDATED
        == "BOOK_DIAGNOSTICS_UPDATED"
    )


def test_operational_engines_do_not_read_book_diagnostics():
    protected_engines = (
        ContextEngine,
        ScoreEngine,
        RiskManager,
        DecisionEngine,
    )

    for engine_class in protected_engines:
        source = inspect.getsource(engine_class)
        assert "book_diagnostics" not in source


def test_book_diagnostics_engine_contract_remains_passive():
    assert BookDiagnosticsEngine.VERSION == "RC2-OBSERVATIONAL"
    assert BookDiagnosticsEngine.ENABLED is True
    assert BookDiagnosticsEngine.PRIORITY == 55

    result = BookDiagnosticsResult()
    assert result.passive_only is True
