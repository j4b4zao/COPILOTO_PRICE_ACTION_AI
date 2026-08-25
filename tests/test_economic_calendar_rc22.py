"""Testes offline do planejador de cinco sessões Trading Economics RC22."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from economic_context import EconomicCalendarReplayPackageStore
from economic_context.trading_economics_trial_session_planner import (
    TradingEconomicsTrialSessionPlanner,
)


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def save(root, filename, *, session_id=None):
    session_id = session_id or filename.split(".", 1)[0]
    return EconomicCalendarReplayPackageStore().save(
        Path(root) / filename,
        session_id=session_id,
        captured_at=NOW,
        payload=[],
    )


def teste_diretorio_vazio_planeja_d1():
    with TemporaryDirectory() as root:
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert plan.status == "READY"
        assert plan.next_session_id == "D1"
        assert plan.next_package_name == "D1.calendar-replay.json"


def teste_total_fixo_de_cinco_sessoes():
    with TemporaryDirectory() as root:
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert plan.total_sessions == 5
        assert [item.session_id for item in plan.sessions] == [
            "D1", "D2", "D3", "D4", "D5"
        ]


def teste_d1_valido_avanca_para_d2():
    with TemporaryDirectory() as root:
        save(root, "D1.calendar-replay.json")
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert plan.completed_sessions == 1
        assert plan.remaining_sessions == 4
        assert plan.next_session_id == "D2"


def teste_progresso_parcial_escolhe_primeiro_pendente():
    with TemporaryDirectory() as root:
        save(root, "D1.calendar-replay.json")
        save(root, "D2.calendar-replay.json")
        save(root, "D3.calendar-replay.json")
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert plan.next_session_id == "D4"
        assert plan.completed_sessions == 3


def teste_cinco_pacotes_validos_concluem_plano():
    with TemporaryDirectory() as root:
        for session_id in ("D1", "D2", "D3", "D4", "D5"):
            save(root, f"{session_id}.calendar-replay.json")
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert plan.status == "COMPLETE"
        assert plan.completed_sessions == 5
        assert plan.remaining_sessions == 0
        assert plan.next_session_id is None


def teste_pacote_corrompido_bloqueia_plano():
    with TemporaryDirectory() as root:
        Path(root, "D1.calendar-replay.json").write_text(
            "{invalido",
            encoding="utf-8",
        )
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert plan.status == "BLOCKED"
        assert plan.sessions[0].status == "INVALID"
        assert plan.next_session_id is None


def teste_session_id_incompativel_bloqueia_plano():
    with TemporaryDirectory() as root:
        save(
            root,
            "D1.calendar-replay.json",
            session_id="D2",
        )
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert plan.status == "BLOCKED"
        assert not plan.sessions[0].valid


def teste_diretorio_no_lugar_do_pacote_e_invalido():
    with TemporaryDirectory() as root:
        Path(root, "D1.calendar-replay.json").mkdir()
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert plan.status == "BLOCKED"
        assert plan.sessions[0].status == "INVALID"


def teste_relatorio_nao_expoe_diretorio_completo():
    with TemporaryDirectory() as root:
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert str(root) not in str(plan)
        assert all("/" not in item.package_name for item in plan.sessions)
        assert all("\\" not in item.package_name for item in plan.sessions)


def teste_plano_permanece_observacional():
    with TemporaryDirectory() as root:
        plan = TradingEconomicsTrialSessionPlanner().evaluate(root)
        assert plan.observational_only
        assert not plan.score_influence_allowed
        assert not plan.order_execution_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC22 APROVADO")


if __name__ == "__main__":
    main()
