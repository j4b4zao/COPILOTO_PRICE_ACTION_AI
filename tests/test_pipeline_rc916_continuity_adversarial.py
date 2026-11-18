"""Regressões de continuidade temporal da RC9.16."""

from dataclasses import replace
from datetime import timedelta

import pytest

from analysis import analysis_pipeline as pipeline_module
from tests.test_pipeline_rc915_adversarial import (
    NOW,
    BookService,
    ExternalService,
    iso,
    make_pipeline,
)
from tests.test_pipeline_rc914_stale_state import DiagnosticPipeline
from tests.test_trader_psychology_rc7 import build_pipeline


SYMBOL = "WINZ26"
SOURCE = "RC915_ADVERSARIAL"
REGRESSIVE = "TEMPORAL_REGRESSIVE_TIMESTAMP"
VALIDATION_ERROR = "TEMPORAL_VALIDATION_ERROR"
CHANNELS = [
    ("external_context_service", "_temporal_external_history", None),
    ("book_depth_service", "_temporal_book_history", (SYMBOL, SOURCE)),
]


def controlled_pipeline(clock=None):
    configured, external, book = make_pipeline(clock=clock)
    pipeline = DiagnosticPipeline(external, book)
    pipeline.temporal_external_policy = configured.temporal_external_policy
    pipeline.temporal_book_policy = configured.temporal_book_policy
    pipeline.temporal_reference_provider = configured.temporal_reference_provider
    pipeline.context.market.symbol = SYMBOL
    return pipeline, external, book


def cycle(pipeline):
    context = pipeline.executar(pipeline.context)
    return context.external_market.valid, context.book_depth.available


def rejection_reason(pipeline, channel):
    if channel == 0:
        return pipeline.context.external_market.reasons[-1]
    return pipeline.context.book_depth.source


def test_legacy_pipeline_without_init_publishes_without_temporal_policy():
    pipeline, _ = build_pipeline()
    pipeline.context.market.symbol = SYMBOL
    pipeline.external_context_service = ExternalService("INVALID_TIMESTAMP")
    pipeline.book_depth_service = BookService("INVALID_TIMESTAMP")

    def unexpected_clock():
        pytest.fail("O ciclo legado não deve consultar o relógio temporal")

    pipeline.temporal_reference_provider = unexpected_clock
    assert cycle(pipeline) == (True, True)
    assert pipeline.context.external_market.timestamp == "INVALID_TIMESTAMP"
    assert pipeline.context.book_depth.timestamp == "INVALID_TIMESTAMP"


@pytest.mark.parametrize("channel", [0, 1])
def test_reconnection_preserves_last_accepted_timestamp(channel):
    pipeline, _, _ = controlled_pipeline()
    service_attr, history_attr, stream = CHANNELS[channel]
    service = getattr(pipeline, service_attr)
    history = getattr(pipeline, history_attr)
    assert cycle(pipeline) == (True, True)
    assert history.previous(service, stream) == iso()

    setattr(pipeline, service_attr, None)
    assert cycle(pipeline)[channel] is False
    assert rejection_reason(pipeline, channel) == (
        "EXTERNAL_CONTEXT_SERVICE_UNAVAILABLE" if channel == 0
        else "BOOK_DEPTH_SERVICE_UNAVAILABLE"
    )
    assert history.previous(service, stream) == iso()

    setattr(pipeline, service_attr, service)
    service.timestamp = iso(-1)
    result = cycle(pipeline)
    assert result[channel] is False
    assert result[1 - channel] is True
    assert rejection_reason(pipeline, channel) == REGRESSIVE
    assert history.previous(service, stream) == iso()

    service.timestamp = iso(1)
    assert cycle(pipeline) == (True, True)
    assert history.previous(service, stream) == iso(1)


@pytest.mark.parametrize("channel", [0, 1])
def test_replacement_and_return_use_object_identity(monkeypatch, channel):
    pipeline, _, _ = controlled_pipeline()
    service_attr, history_attr, stream = CHANNELS[channel]
    base = type(getattr(pipeline, service_attr))

    class EqualService(base):
        __hash__ = None

        def __eq__(self, other):
            return isinstance(other, EqualService)

    original = EqualService(iso())
    replacement = EqualService(iso(-1))
    setattr(pipeline, service_attr, original)
    monkeypatch.setattr(pipeline_module, "id", lambda _: 1, raising=False)
    history = getattr(pipeline, history_attr)
    other_attr, other_history_attr, other_stream = CHANNELS[1 - channel]
    other_history = getattr(pipeline, other_history_attr)
    other_service = getattr(pipeline, other_attr)
    assert cycle(pipeline) == (True, True)

    setattr(pipeline, service_attr, replacement)
    assert cycle(pipeline) == (True, True)
    assert len(history) == 2
    assert history.previous(original, stream) == iso()
    assert history.previous(replacement, stream) == iso(-1)
    assert len(other_history) == 1
    assert other_history.previous(other_service, other_stream) == iso()

    setattr(pipeline, service_attr, original)
    original.timestamp = iso(-1)
    assert cycle(pipeline)[channel] is False
    assert rejection_reason(pipeline, channel) == REGRESSIVE
    assert history.previous(original, stream) == iso()


def test_external_history_evicts_least_recent_publication():
    pipeline, active, _ = controlled_pipeline()
    history = pipeline._temporal_external_history
    assert cycle(pipeline) == (True, True)
    services = [ExternalService(iso()) for _ in range(history.CAPACITY)]
    for service in services[:-1]:
        pipeline.external_context_service = service
        assert cycle(pipeline) == (True, True)

    pipeline.external_context_service = active
    assert cycle(pipeline) == (True, True)
    pipeline.external_context_service = services[-1]
    assert cycle(pipeline) == (True, True)
    assert len(history) == history.CAPACITY
    assert history.previous(services[0], None) is None
    assert history.previous(active, None) == iso()
    assert len(pipeline._temporal_book_history) == 1

    pipeline.external_context_service = active
    active.timestamp = iso(-1)
    assert cycle(pipeline) == (False, True)
    assert rejection_reason(pipeline, 0) == REGRESSIVE

    evicted = services[0]
    evicted.timestamp = iso(-1)
    pipeline.external_context_service = evicted
    assert cycle(pipeline) == (True, True)
    assert len(history) == history.CAPACITY


def test_book_history_bounds_symbol_and_source_pairs():
    class BookWithSource(BookService):
        source = SOURCE

        def snapshot(self, symbol):
            return replace(super().snapshot(symbol), source=self.source)

    pipeline, external, _ = controlled_pipeline()
    book = BookWithSource(iso())
    pipeline.book_depth_service = book
    history = pipeline._temporal_book_history
    assert cycle(pipeline) == (True, True)
    streams = [(f"SYMBOL{i // 2}", f"SOURCE{i % 2}") for i in range(history.CAPACITY)]
    for symbol, source in streams[:-1]:
        pipeline.context.market.symbol = symbol
        book.source = source
        assert cycle(pipeline) == (True, True)

    pipeline.context.market.symbol = SYMBOL
    book.source = SOURCE
    assert cycle(pipeline) == (True, True)
    pipeline.context.market.symbol, book.source = streams[-1]
    assert cycle(pipeline) == (True, True)
    assert len(history) == history.CAPACITY
    assert history.previous(book, streams[0]) is None
    assert history.previous(book, (SYMBOL, SOURCE)) == iso()
    assert len(pipeline._temporal_external_history) == 1
    assert pipeline._temporal_external_history.previous(external, None) == iso()

    pipeline.context.market.symbol = SYMBOL
    book.source = SOURCE
    book.timestamp = iso(-1)
    assert cycle(pipeline) == (True, False)
    assert rejection_reason(pipeline, 1) == REGRESSIVE

    pipeline.context.market.symbol, book.source = streams[0]
    assert cycle(pipeline) == (True, True)
    assert len(history) == history.CAPACITY


def test_context_reset_keeps_temporal_history():
    pipeline, external, book = controlled_pipeline()
    assert cycle(pipeline) == (True, True)

    pipeline.context.reset()
    assert pipeline.context.external_market.valid is False
    assert pipeline.context.book_depth.available is False
    assert pipeline._temporal_external_history.previous(external, None) == iso()
    assert pipeline._temporal_book_history.previous(book, (SYMBOL, SOURCE)) == iso()

    pipeline.context.market.symbol = SYMBOL
    external.timestamp = book.timestamp = iso(-1)
    assert cycle(pipeline) == (False, False)
    assert rejection_reason(pipeline, 0) == REGRESSIVE
    assert rejection_reason(pipeline, 1) == REGRESSIVE


def test_reactivating_policies_uses_history_from_before_bypass():
    clock_calls = []

    def clock():
        clock_calls.append(NOW)
        return NOW

    pipeline, external, book = controlled_pipeline(clock)
    assert cycle(pipeline) == (True, True)
    external_policy = pipeline.temporal_external_policy
    book_policy = pipeline.temporal_book_policy

    pipeline.temporal_external_policy = pipeline.temporal_book_policy = None
    external.timestamp = book.timestamp = iso(-1)
    assert cycle(pipeline) == (True, True)
    assert len(clock_calls) == 1
    assert pipeline._temporal_external_history.previous(external, None) == iso()
    assert pipeline._temporal_book_history.previous(book, (SYMBOL, SOURCE)) == iso()

    pipeline.temporal_external_policy = external_policy
    pipeline.temporal_book_policy = book_policy
    assert cycle(pipeline) == (False, False)
    assert len(clock_calls) == 2
    assert rejection_reason(pipeline, 0) == REGRESSIVE
    assert rejection_reason(pipeline, 1) == REGRESSIVE


def test_cycle_uses_same_reference_for_both_sources():
    readings = iter((NOW, NOW + timedelta(seconds=61)))
    pipeline, _, _ = controlled_pipeline(lambda: next(readings))

    assert cycle(pipeline) == (True, True)
    assert cycle(pipeline) == (False, False)
    assert rejection_reason(pipeline, 0) == "TEMPORAL_STALE_TIMESTAMP"
    assert rejection_reason(pipeline, 1) == "TEMPORAL_STALE_TIMESTAMP"


@pytest.mark.parametrize(
    "external_enabled,book_enabled,expected",
    [(True, True, (False, False)), (True, False, (False, True)),
     (False, True, (True, False))],
)
def test_intermittent_clock_rejects_enabled_sources_and_recovers(
    external_enabled, book_enabled, expected
):
    calls = []

    def clock():
        calls.append(NOW)
        if len(calls) == 2:
            raise RuntimeError("relógio indisponível")
        return NOW

    pipeline, external, book = controlled_pipeline(clock)
    assert cycle(pipeline) == (True, True)
    if not external_enabled:
        pipeline.temporal_external_policy = None
    if not book_enabled:
        pipeline.temporal_book_policy = None
    external.timestamp = book.timestamp = iso(1)

    assert cycle(pipeline) == expected
    for channel, accepted in enumerate(expected):
        if not accepted:
            assert rejection_reason(pipeline, channel) == VALIDATION_ERROR
    assert len(calls) == 2
    assert pipeline._temporal_external_history.previous(external, None) == iso()
    assert pipeline._temporal_book_history.previous(book, (SYMBOL, SOURCE)) == iso()

    assert cycle(pipeline) == (True, True)
    assert len(calls) == 3


def test_external_copy_failure_preserves_publication_and_history(monkeypatch):
    pipeline, external, _ = controlled_pipeline()
    assert cycle(pipeline) == (True, True)
    published = pipeline.context.external_market
    history = pipeline._temporal_external_history
    external.timestamp = iso(2)

    def fail_copy(state):
        assert state.timestamp == iso(2)
        assert history.previous(external, None) == iso()
        raise RuntimeError("falha de cópia controlada")

    with monkeypatch.context() as patch:
        patch.setattr(pipeline_module, "deepcopy", fail_copy)
        with pytest.raises(RuntimeError, match="falha de cópia controlada"):
            cycle(pipeline)

    assert history.previous(external, None) == iso()
    assert pipeline.context.external_market is published
    assert published.valid and published.timestamp == iso()

    external.timestamp = iso(1)
    assert cycle(pipeline) == (True, True)
    assert pipeline.context.external_market.timestamp == iso(1)
    assert history.previous(external, None) == iso(1)
