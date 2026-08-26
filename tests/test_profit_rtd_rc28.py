from models.book_depth import BookDepthSnapshot
from market_data.book_depth_quality_validator import BookDepthQualityValidator
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics


def snapshot(step):
    bid = 178000.0 + step * 5.0
    ask = bid + 15.0
    return BookDepthSnapshot.build(
        symbol="WINV26",
        timestamp=f"2026-08-26T10:00:{step:02d}",
        bids=[(bid - i * 5.0, 100 + i, 0) for i in range(5)],
        asks=[(ask + i * 5.0, 120 + i, 0) for i in range(5)],
        source="PROFIT_RTD",
    )


def main():
    diagnostics = BookDepthSourceDiagnostics()
    validator = BookDepthQualityValidator()

    # Padrão real: atualização em rajadas, com vários polls idênticos entre elas.
    for step in range(1, 6):
        snap = snapshot(step)
        report = diagnostics.observe(snap)
        quality = validator.evaluate(snap, report)
        for _ in range(7):
            report = diagnostics.observe(snap)
            quality = validator.evaluate(snap, report)

    assert report.fresh_snapshots == 5
    assert report.duplicate_snapshots == 35
    assert report.duplicate_rate > 0.80
    assert report.consecutive_duplicates == 7
    assert report.status == "READY"
    assert quality.status == "VALID"
    assert quality.anomaly_count == 0
    assert "EXCESSIVE_DUPLICATION" not in quality.reasons

    # Staleness real: 20 snapshots consecutivos sem qualquer mudança.
    stale = snapshot(6)
    diagnostics.observe(stale)
    for _ in range(BookDepthSourceDiagnostics.MAX_CONSECUTIVE_DUPLICATES):
        report = diagnostics.observe(stale)
    quality = validator.evaluate(stale, report)

    assert report.consecutive_duplicates == 20
    assert report.status == "DEGRADED"
    assert quality.status == "DEGRADED"
    assert quality.anomaly_count == 1
    assert quality.reasons == ("SOURCE_DEGRADED",)

    # Uma atualização nova recupera imediatamente da condição de staleness.
    recovered = snapshot(7)
    report = diagnostics.observe(recovered)
    quality = validator.evaluate(recovered, report)
    assert report.consecutive_duplicates == 0
    assert report.status == "READY"
    assert quality.status == "VALID"
    assert quality.anomaly_count == 0

    print("PROFIT_RTD_RC28=OK")


if __name__ == "__main__":
    main()
