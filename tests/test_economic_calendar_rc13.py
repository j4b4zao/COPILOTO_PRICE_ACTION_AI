"""Testes offline dos pacotes de replay RC13."""

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from economic_context import (
    EconomicCalendarReplayPackageStore,
    EconomicCalendarReplayTrialRunner,
)


def payload(**changes):
    row = {
        "CalendarId": "1",
        "Date": "2026-08-25T12:30:00Z",
        "Country": "United States",
        "Event": "Non Farm Payrolls",
        "Importance": 3,
        "Currency": "USD",
        "SourceURL": "https://example.test/calendar?tracking=remover#fragmento",
    }
    row.update(changes)
    return [row]


def path(root, name="D1.calendar-replay.json"):
    return Path(root) / name


def save(store, destination, **changes):
    kwargs = {
        "session_id": "D1",
        "captured_at": datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc),
        "payload": payload(),
    }
    kwargs.update(changes)
    return store.save(destination, **kwargs)


def teste_salva_e_carrega_pacote_versionado():
    with TemporaryDirectory() as root:
        package = save(EconomicCalendarReplayPackageStore(), path(root))
        assert package.session_id == "D1"
        assert package.provider == "TRADING_ECONOMICS"
        assert package.observational_only
        assert len(package.checksum_sha256) == 64


def teste_sanitiza_query_e_fragmento_de_urls_do_payload():
    with TemporaryDirectory() as root:
        package = save(EconomicCalendarReplayPackageStore(), path(root))
        assert package.payload[0]["SourceURL"] == "https://example.test/calendar"


def teste_rejeita_chaves_sensiveis_em_qualquer_nivel():
    with TemporaryDirectory() as root:
        for key in ("api_key", "Authorization", "token", "password"):
            try:
                save(
                    EconomicCalendarReplayPackageStore(),
                    path(root, f"{key}.calendar-replay.json"),
                    payload=payload(metadata={key: "segredo"}),
                )
            except ValueError:
                continue
            raise AssertionError(f"Campo sensível aceito: {key}")


def teste_rejeita_valor_secreto_conhecido():
    with TemporaryDirectory() as root:
        try:
            save(
                EconomicCalendarReplayPackageStore(),
                path(root),
                payload=payload(Event="evento segredo123"),
                forbidden_secret_values=("segredo123",),
            )
        except ValueError:
            return
        raise AssertionError("Valor secreto deveria ser rejeitado.")


def teste_rejeita_timestamp_sem_fuso():
    with TemporaryDirectory() as root:
        try:
            save(
                EconomicCalendarReplayPackageStore(),
                path(root),
                captured_at=datetime(2026, 8, 25, 9, 0),
            )
        except ValueError:
            return
        raise AssertionError("Timestamp ingênuo deveria ser rejeitado.")


def teste_nao_sobrescreve_pacote_sem_autorizacao_explicita():
    with TemporaryDirectory() as root:
        destination = path(root)
        store = EconomicCalendarReplayPackageStore()
        save(store, destination)
        try:
            save(store, destination)
        except FileExistsError:
            return
        raise AssertionError("Pacote existente não deveria ser sobrescrito.")


def teste_checksum_detecta_alteracao_do_payload():
    with TemporaryDirectory() as root:
        destination = path(root)
        store = EconomicCalendarReplayPackageStore()
        save(store, destination)
        envelope = json.loads(destination.read_text(encoding="utf-8"))
        envelope["payload"][0]["Event"] = "Evento adulterado"
        destination.write_text(json.dumps(envelope), encoding="utf-8")
        try:
            store.load(destination)
        except ValueError as exc:
            assert "Checksum" in str(exc)
            return
        raise AssertionError("Adulteração deveria invalidar o checksum.")


def teste_rejeita_flags_operacionais_mesmo_com_checksum_recalculado():
    with TemporaryDirectory() as root:
        destination = path(root)
        store = EconomicCalendarReplayPackageStore()
        save(store, destination)
        envelope = json.loads(destination.read_text(encoding="utf-8"))
        envelope["score_influence_allowed"] = True
        body = {key: value for key, value in envelope.items() if key != "checksum_sha256"}
        envelope["checksum_sha256"] = store._checksum(body)
        destination.write_text(json.dumps(envelope), encoding="utf-8")
        try:
            store.load(destination)
        except ValueError:
            return
        raise AssertionError("Flag operacional deveria ser rejeitada.")


def teste_importa_pacote_diretamente_no_runner_offline():
    with TemporaryDirectory() as root:
        destination = path(root)
        store = EconomicCalendarReplayPackageStore()
        save(store, destination)
        runner = EconomicCalendarReplayTrialRunner()
        session = store.replay_into(
            runner,
            destination,
            expected_event_count=1,
            maximum_clock_error_seconds=15,
        )
        assert session.session_id == "D1"
        assert session.event_count == 1
        assert runner.report().evidence.completed_sessions == 1


def teste_extensao_especifica_e_obrigatoria():
    with TemporaryDirectory() as root:
        try:
            save(EconomicCalendarReplayPackageStore(), Path(root) / "replay.json")
        except ValueError:
            return
        raise AssertionError("Extensão genérica não deveria ser aceita.")


def main():
    tests = [value for name, value in globals().items() if name.startswith("teste_")]
    for test in tests:
        test()
        print(f"✅ {test.__name__}")
    print("🏆 ECONOMIC CALENDAR RC13 APROVADO")


if __name__ == "__main__":
    main()
