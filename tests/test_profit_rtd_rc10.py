"""Offline gate do Profit RTD RC10: exportação de sessão de validação."""

import hashlib
import json
import tempfile
from pathlib import Path

from market_data.profit_rtd_validation_exporter import ProfitRTDValidationExporter
from market_data.profit_rtd_validation_recorder import ProfitRTDValidationSnapshot


def _snapshot():
    return ProfitRTDValidationSnapshot(
        total_cycles=10,
        state_updates=6,
        baseline_resets=1,
        total_new_trades=24,
        total_source_units=24,
        contiguous_cycles=8,
        no_new_trade_cycles=2,
        continuity_loss_cycles=1,
        symbol_reset_cycles=0,
        last_symbol="WINV26",
        last_continuity="CONTIGUOUS",
        last_new_trade_count=4,
        last_state_updated=True,
        update_rate=0.6,
        continuity_rate=0.8,
    )


def test_exporta_json_versionado_com_hash_dos_bytes_reais():
    exporter = ProfitRTDValidationExporter()
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "validation.json"
        receipt = exporter.export(_snapshot(), target)
        raw = target.read_bytes()
        payload = json.loads(raw.decode("utf-8"))

        assert receipt.path == str(target)
        assert receipt.schema == "PROFIT_RTD_VALIDATION_SESSION_V1"
        assert receipt.byte_size == len(raw)
        assert receipt.sha256 == hashlib.sha256(raw).hexdigest()
        assert receipt.total_cycles == 10
        assert payload["schema"] == receipt.schema
        assert payload["source"] == "PROFIT_RTD_TIMES_TRADES"
        assert payload["validation"]["total_new_trades"] == 24
        assert payload["capabilities"]["observational_only"] is True
        assert payload["capabilities"]["score_influence_allowed"] is False
        assert payload["capabilities"]["decision_influence_allowed"] is False
        assert payload["capabilities"]["order_execution_allowed"] is False


def test_overwrite_e_bloqueado_por_padrao_e_pode_ser_explicito():
    exporter = ProfitRTDValidationExporter()
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "validation.json"
        exporter.export(_snapshot(), target)
        original = target.read_bytes()
        try:
            exporter.export(_snapshot(), target)
        except FileExistsError:
            pass
        else:
            raise AssertionError("overwrite=False deveria bloquear arquivo existente")
        assert target.read_bytes() == original
        exporter.export(_snapshot(), target, overwrite=True)


def test_caminho_relativo_e_rejeitado():
    exporter = ProfitRTDValidationExporter()
    try:
        exporter.export(_snapshot(), "validation.json")
    except ValueError:
        pass
    else:
        raise AssertionError("caminho relativo deveria ser rejeitado")


def test_snapshot_permanece_estritamente_observacional():
    snapshot = _snapshot()
    assert snapshot.observational_only is True
    assert snapshot.score_influence_allowed is False
    assert snapshot.decision_influence_allowed is False
    assert snapshot.order_execution_allowed is False


def main():
    test_exporta_json_versionado_com_hash_dos_bytes_reais()
    test_overwrite_e_bloqueado_por_padrao_e_pode_ser_explicito()
    test_caminho_relativo_e_rejeitado()
    test_snapshot_permanece_estritamente_observacional()
    print("🏆 PROFIT RTD RC10 APROVADO")


if __name__ == "__main__":
    main()
