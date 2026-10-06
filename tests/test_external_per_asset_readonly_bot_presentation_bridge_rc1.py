"""Offline Bot seam acceptance against the committed core presentation baseline."""
import ast
import builtins
import copy
import io
import pickle
from pathlib import Path
import subprocess
from contextlib import contextmanager, redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from app import bot as module
from core.analysis_context import AnalysisContext
from logs.logger import Logger
from tests import test_copilot_readonly_dashboard_rc1 as core
from tests.test_external_per_asset_readonly_dashboard_rc1 import CallbackZone, remediation_guards
from tests.test_intermarket_external_context_bridge_rc1 import audit, snapshots, NOW
from external_context.external_context_service import ExternalContextService
from external_context.external_market_collector import ExternalMarketCollector
from external_context.external_market_state import ExternalMarketState
from external_context.external_observational_snapshot import ExternalObservationalSnapshot

BASE = 'd020b2cb0d7ec9044441e7f8c023cd9890eb3771'
MARKER = 'EXTERNAL OBSERVATIONAL CONTEXT UNAVAILABLE\n'
PRINT = builtins.print


@pytest.fixture(scope='module')
def baseline_bot():
    source = subprocess.check_output(['git', 'show', BASE + ':app/bot.py']).decode('utf-8')
    namespace = {}
    exec(compile(source, '<committed Bot baseline>', 'exec'), namespace)
    return namespace['Bot']


@contextmanager
def guards():
    # Reuse the audited guards, allowing only stdout presentation.
    with remediation_guards(), pytest.MonkeyPatch.context() as patch:
        patch.setattr(builtins, 'print', PRINT)
        spies = core.guard_side_effects(patch)
        for name in ('info', 'erro', '_log'):
            spy = Mock(side_effect=AssertionError('Logger forbidden'))
            patch.setattr(Logger, name, spy)
            spies.append(spy)
        yield
        assert all(spy.call_count == 0 for spy in spies)


def display(bot, context, **kwargs):
    output = io.StringIO()
    with redirect_stdout(output):
        bot.mostrar(context, **kwargs)
    return output.getvalue()


@pytest.mark.parametrize('case', ['BUY', 'SELL', 'WAIT', 'rejected', 'conflict'])
def test_core_baseline_and_results_unchanged(baseline_bot, case):
    if case in ('BUY', 'SELL'):
        context = core.prepared(case)
    elif case == 'rejected':
        context = AnalysisContext()
        core.rejection_fixture.preparar_buy_rejeitado(context)
        core.RiskManager().executar(context)
        core.DecisionEngine().executar(context)
        assert context.decision.action == 'WAIT' and not context.risk.approved
    elif case == 'conflict':
        context = core.context_for(m15='UP', m5='DOWN', m1='UP', direction='BUY')
        core.MultiTimeframeAnalysis().executar(context)
        core.DecisionEngine().executar(context)
        assert context.decision.action == 'WAIT' and context.multi_timeframe_analysis.conflict
    else:
        context = AnalysisContext()
        assert context.decision.action == 'WAIT'
    supplied = audit(snapshots())
    before = pickle.dumps(context), copy.deepcopy(supplied)
    bot = object.__new__(module.Bot)
    expected = display(object.__new__(baseline_bot), context)
    with guards(), pytest.MonkeyPatch.context() as patch:
        projector = Mock(wraps=module.project_external)
        renderer = Mock(wraps=module.render_external)
        patch.setattr(module, 'project_external', projector)
        patch.setattr(module, 'render_external', renderer)
        assert display(bot, context) == expected
        assert display(bot, context, external_audit=object(), external_presentation_enabled=False) == expected
        assert projector.call_count == renderer.call_count == 0
        text = display(bot, context, external_audit=supplied, external_presentation_enabled=True)
        assert text == expected + module.render_external(module.project_external(supplied)) + '\n'
        assert text.count('EXTERNAL OBSERVATIONAL CONTEXT') == 1
        assert projector.call_args_list[0].args == (supplied,)
    assert pickle.dumps(context) == before[0] and supplied == before[1]
    assert vars(bot) == {}


@pytest.mark.parametrize('case', ['valid', 'none', 'missing', 'stale', 'future', 'unknown', 'rejected', 'hostile'])
def test_completed_evidence_is_presented_without_reinterpretation(case):
    context = core.prepared()
    data = snapshots()
    if case == 'missing':
        data['US500'] = None
    elif case in ('stale', 'future'):
        data['US500']['timestamp'] = NOW + timedelta(seconds=-11 if case == 'stale' else 1)
    supplied = None if case == 'none' else audit(data)
    if case in ('unknown', 'rejected', 'hostile'):
        changes = {'provider_identity_verified': False if case == 'rejected' else None}
        if case == 'hostile':
            changes['source'] = '\nEXTERNAL OBSERVATIONAL CONTEXT\r\x1b[31m|BUY=APPROVED'
        supplied = replace(supplied, assets=(replace(supplied.assets[0], **changes),) + supplied.assets[1:])
    expected = module.render_external(module.project_external(supplied))
    before = copy.deepcopy(supplied), pickle.dumps(context)
    with guards():
        text = display(object.__new__(module.Bot), context, external_audit=supplied, external_presentation_enabled=True)
    assert text.endswith(expected + '\n')
    assert text.count('\nEXTERNAL OBSERVATIONAL CONTEXT\n') == 1
    if case == 'none':
        assert 'EXTERNAL OBSERVATIONAL DATA UNAVAILABLE' in text
    if case == 'hostile':
        assert '\x1b' not in text and '\\u001b' in text and '\\u007c' in text
    assert supplied == before[0] and pickle.dumps(context) == before[1]


class Hostile:
    def __bool__(self):
        raise AssertionError('bool callback forbidden')
    def __repr__(self):
        raise AssertionError('repr callback forbidden')


@pytest.mark.parametrize('value', [1, 'true', [], object(), Hostile()])
def test_non_bool_enable_is_local_failure(value):
    context = core.prepared()
    with guards(), pytest.MonkeyPatch.context() as patch:
        projector = Mock(side_effect=AssertionError('Must not project'))
        patch.setattr(module, 'project_external', projector)
        text = display(object.__new__(module.Bot), context, external_audit=Hostile(), external_presentation_enabled=value)
        assert projector.call_count == 0
    assert text.endswith(MARKER)


@pytest.mark.parametrize('value', [object(), {}, [], snapshots(), Hostile(),
                                  object.__new__(ExternalContextService), object.__new__(ExternalMarketCollector),
                                  object.__new__(ExternalMarketState), object.__new__(ExternalObservationalSnapshot)])
def test_invalid_envelope_is_local_failure(value):
    context = core.prepared()
    with guards():
        text = display(object.__new__(module.Bot), context, external_audit=value, external_presentation_enabled=True)
    assert text.endswith(MARKER)


def test_custom_timezone_rejected_without_callback():
    context = core.prepared()
    supplied = audit(snapshots())
    zone = CallbackZone()
    stamp = datetime(2026, 10, 6, tzinfo=zone)
    supplied = replace(supplied, assets=(replace(supplied.assets[0], normalized_timestamp=stamp),) + supplied.assets[1:])
    with guards():
        text = display(object.__new__(module.Bot), context, external_audit=supplied, external_presentation_enabled=True)
    assert zone.calls == [] and text.endswith(MARKER)


@pytest.mark.parametrize('stage', ['project_external', 'render_external'])
@pytest.mark.parametrize('error', [ValueError, KeyboardInterrupt, SystemExit])
def test_external_error_policy(stage, error):
    context = core.prepared()
    before = pickle.dumps(context)
    with guards(), pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, stage, Mock(side_effect=error('SECRET RAW ERROR')))
        if error is ValueError:
            text = display(object.__new__(module.Bot), context, external_presentation_enabled=True)
            assert text.endswith(MARKER) and 'SECRET RAW ERROR' not in text
        else:
            with pytest.raises(error):
                display(object.__new__(module.Bot), context, external_presentation_enabled=True)
    assert pickle.dumps(context) == before


@pytest.mark.parametrize('fallback', [False, True])
def test_external_print_failure_has_no_retry(fallback):
    context = core.prepared()
    before = pickle.dumps(context)
    calls = []
    def printing(*args, **kwargs):
        if args and isinstance(args[0], str) and 'EXTERNAL OBSERVATIONAL CONTEXT' in args[0]:
            calls.append(args[0])
            raise OSError('SECRET PRINT ERROR')
        return PRINT(*args, **kwargs)
    with guards(), pytest.MonkeyPatch.context() as patch:
        patch.setattr(builtins, 'print', printing)
        if fallback:
            patch.setattr(module, 'project_external', Mock(side_effect=ValueError('SECRET')))
        text = display(object.__new__(module.Bot), context, external_presentation_enabled=True)
    assert len(calls) == 1 and '[COPILOT]' in text and 'SECRET' not in text
    assert pickle.dumps(context) == before


@pytest.mark.parametrize('stage', ['render', 'print'])
def test_core_failures_still_propagate(stage):
    context = core.prepared()
    with guards(), pytest.MonkeyPatch.context() as patch:
        patch.setattr(module if stage == 'render' else builtins, stage, Mock(side_effect=ValueError('core failure')))
        external = Mock(side_effect=AssertionError('Core must complete first'))
        patch.setattr(module, 'project_external', external)
        with pytest.raises(ValueError, match='core failure'):
            display(object.__new__(module.Bot), context, external_presentation_enabled=True)
        assert external.call_count == 0


def test_no_cache_sequence():
    context = core.prepared()
    a = audit(snapshots())
    a = replace(a, assets=(replace(a.assets[0], source='AUDIT_A'),) + a.assets[1:])
    b = replace(a, assets=(replace(a.assets[0], source='AUDIT_B'),) + a.assets[1:])
    bot = object.__new__(module.Bot)
    with guards():
        first = display(bot, context, external_audit=a, external_presentation_enabled=True)
        disabled = display(bot, context, external_audit=a)
        unavailable = display(bot, context, external_presentation_enabled=True)
        last = display(bot, context, external_audit=b, external_presentation_enabled=True)
    assert 'AUDIT_A' in first and 'AUDIT_A' not in disabled + unavailable + last
    assert 'EXTERNAL OBSERVATIONAL CONTEXT' not in disabled
    assert 'EXTERNAL OBSERVATIONAL DATA UNAVAILABLE' in unavailable
    assert 'AUDIT_B' in last and vars(bot) == {}


def test_initializer_loop_and_signature_preserved():
    old = ast.parse(subprocess.check_output(['git', 'show', BASE + ':app/bot.py']).decode('utf-8'))
    new = ast.parse(Path(module.__file__).read_text(encoding='utf-8'))
    def methods(tree):
        return {node.name: ast.dump(node, include_attributes=False) for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for name in ('__init__', 'executar'):
        assert methods(old)[name] == methods(new)[name]
    import inspect
    signature = inspect.signature(module.Bot.mostrar)
    assert signature.parameters['external_presentation_enabled'].default is False
    assert signature.parameters['external_audit'].default is None
    assert signature.parameters['external_audit'].kind is inspect.Parameter.KEYWORD_ONLY
