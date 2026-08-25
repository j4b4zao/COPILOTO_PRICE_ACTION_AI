"""Testes offline do manifesto Trading Economics RC25."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from economic_context import EconomicCalendarReplayPackageStore
from economic_context.trading_economics_trial_manifest import (
    TradingEconomicsTrialManifestBuilder,
)


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


def row(event="Non Farm Payrolls"):
    return {
        "CalendarId": "1",
        "Date": "2026-08-25T12:30:00Z",
        "Country": "United States",
        "Event": event,
        "Importance": 3,
        "Currency": "USD",
    }


def save(root, session_id, *, payload=None, captured_at=NOW):
    return EconomicCalendarReplayPackageStore().save(
        Path(root) / f"{session_id}.calendar-replay.json",
        session_id=session_id,
        captured_at=captured_at,
        payload=[row()] if payload is None else payload,
    )


def teste_manifesto_vazio_fica_em_progresso():
    with TemporaryDirectory() as root:
        manifest = TradingEconomicsTrialManifestBuilder().build(root)
        assert manifest.status == "IN_PROGRESS"
        assert manifest.completed_sessions == 0
        assert manifest.remaining_sessions == 5
        assert manifest.entries == ()


def teste_manifesto_parcial_lista_somente_concluidas():
    with TemporaryDirectory() as root:
        save(root, "D1")
        save(root, "D2")
        manifest = TradingEconomicsTrialManifestBuilder().build(root)
        assert [entry.session_id for entry in manifest.entries] == ["D1", "D2"]
        assert manifest.completed_sessions == 2


def teste_entrada_contem_metadados_auditaveis():
    with TemporaryDirectory() as root:
        package = save(root, "D1", payload=[row(), row("IPCA")])
        entry = TradingEconomicsTrialManifestBuilder().build(root).entries[0]
        assert entry.package_name == "D1.calendar-replay.json"
        assert entry.captured_at == NOW.isoformat()
        assert entry.event_count == 2
        assert entry.checksum_sha256 == package.checksum_sha256


def teste_manifesto_nao_replica_payload():
    with TemporaryDirectory() as root:
        save(root, "D1", payload=[row("EVENTO_NAO_DEVE_APARECER")])
        manifest = TradingEconomicsTrialManifestBuilder().build(root)
        assert "EVENTO_NAO_DEVE_APARECER" not in str(manifest)
        assert "CalendarId" not in str(manifest)


def teste_checksum_consolidado_e_deterministico():
    with TemporaryDirectory() as root:
        save(root, "D1")
        builder = TradingEconomicsTrialManifestBuilder()
        first = builder.build(root)
        second = builder.build(root)
        assert first.trial_checksum_sha256 == second.trial_checksum_sha256
        assert len(first.trial_checksum_sha256) == 64


def teste_checksum_muda_quando_conteudo_do_ensaio_muda():
    with TemporaryDirectory() as first_root, TemporaryDirectory() as second_root:
        save(first_root, "D1", payload=[row("NFP")])
        save(second_root, "D1", payload=[row("CPI")])
        builder = TradingEconomicsTrialManifestBuilder()
        assert (
            builder.build(first_root).trial_checksum_sha256
            != builder.build(second_root).trial_checksum_sha256
        )


def teste_cinco_sessoes_validas_concluem_manifesto():
    with TemporaryDirectory() as root:
        for session_id in ("D1", "D2", "D3", "D4", "D5"):
            save(root, session_id)
        manifest = TradingEconomicsTrialManifestBuilder().build(root)
        assert manifest.status == "COMPLETE"
        assert manifest.completed_sessions == 5
        assert manifest.remaining_sessions == 0
        assert len(manifest.entries) == 5


def teste_pacote_corrompido_bloqueia_manifesto():
    with TemporaryDirectory() as root:
        save(root, "D1")
        path = Path(root, "D1.calendar-replay.json")
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "Non Farm Payrolls",
                "ALTERADO",
            ),
            encoding="utf-8",
        )
        try:
            TradingEconomicsTrialManifestBuilder().build(root)
        except ValueError:
            return
    raise AssertionError("Pacote corrompido deveria bloquear manifesto.")


def teste_manifesto_nao_expoe_diretorio():
    with TemporaryDirectory() as root:
        save(root, "D1")
        manifest = TradingEconomicsTrialManifestBuilder().build(root)
        assert str(root) not in str(manifest)
        assert "/" not in manifest.entries[0].package_name
        assert "\\" not in manifest.entries[0].package_name


def teste_manifesto_permanece_observacional():
    with TemporaryDirectory() as root:
        manifest = TradingEconomicsTrialManifestBuilder().build(root)
        assert manifest.observational_only
        assert not manifest.score_influence_allowed
        assert not manifest.order_execution_allowed


def main():
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("teste_")
    ]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC25 APROVADO")


if __name__ == "__main__":
    main()
