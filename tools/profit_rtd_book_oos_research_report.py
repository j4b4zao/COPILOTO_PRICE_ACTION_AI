from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.profit_rtd_book_clean_session_forward_runner import run as run_clean_forward
from tools.profit_rtd_book_oos_regime_coverage_ledger import analyze as analyze_ledger

MIN_PATTERN_N = 10
MIN_POSITIVE_COVERAGE_SESSIONS = 1
MIN_NEGATIVE_COVERAGE_SESSIONS = 1


def _max_pattern_n(forward_result):
    patterns = forward_result.get('patterns', {}) if isinstance(forward_result, dict) else {}
    best = 0
    for horizons in patterns.values():
        if not isinstance(horizons, dict):
            continue
        for stats in horizons.values():
            if isinstance(stats, dict):
                try:
                    best = max(best, int(stats.get('n', 0)))
                except (TypeError, ValueError):
                    pass
    return best


def build_report(paths):
    ledger = analyze_ledger(paths)
    runner = run_clean_forward(paths)
    forward = runner.get('forward_result', {})
    clean_sessions = int(ledger.get('clean_sessions', 0))
    quarantined_sessions = int(ledger.get('quarantined_sessions', 0))
    clean_samples = int(ledger.get('clean_samples', 0))
    pos_sessions = int(ledger.get('positive_coverage_sessions', 0))
    neg_sessions = int(ledger.get('negative_coverage_sessions', 0))
    max_pattern_n = _max_pattern_n(forward)

    evidence_reasons = []
    if clean_sessions == 0:
        evidence_reasons.append('NO_CLEAN_OOS_SESSIONS')
    if pos_sessions < MIN_POSITIVE_COVERAGE_SESSIONS:
        evidence_reasons.append('POSITIVE_REGIME_COVERAGE_MISSING')
    if neg_sessions < MIN_NEGATIVE_COVERAGE_SESSIONS:
        evidence_reasons.append('NEGATIVE_REGIME_COVERAGE_MISSING')
    if max_pattern_n < MIN_PATTERN_N:
        evidence_reasons.append('INSUFFICIENT_PATTERN_SAMPLE_SIZE')

    evidence_status = 'EVIDENCE_GATE_PASSED_FOR_FURTHER_RESEARCH' if not evidence_reasons else 'INSUFFICIENT_EVIDENCE'

    session_summary = []
    for session in ledger.get('sessions', []):
        session_summary.append({
            'file': session.get('file'),
            'eligible': bool(session.get('eligible')),
            'regime': session.get('regime'),
            'samples': session.get('samples'),
            'positive': session.get('positive'),
            'negative': session.get('negative'),
            'integrity_reasons': session.get('integrity_reasons', []),
        })

    return {
        'status': 'OOS_RESEARCH_REPORT_COMPLETED',
        'evidence_status': evidence_status,
        'evidence_reasons': evidence_reasons or ['MINIMUM_RESEARCH_EVIDENCE_GATE_PASSED'],
        'input_sessions': len(paths),
        'clean_sessions': clean_sessions,
        'quarantined_sessions': quarantined_sessions,
        'clean_samples': clean_samples,
        'positive_coverage_sessions': pos_sessions,
        'negative_coverage_sessions': neg_sessions,
        'max_pattern_n': max_pattern_n,
        'min_pattern_n_required': MIN_PATTERN_N,
        'clean_files': runner.get('clean_files', []),
        'sessions': session_summary,
        'forward_result': forward,
        'observational_only': True,
        'predictive_claim_allowed': False,
        'score_influence_allowed': False,
        'decision_influence_allowed': False,
        'order_execution_allowed': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='+')
    parser.add_argument('--output', default=None)
    args = parser.parse_args()
    report = build_report(args.paths)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        target = Path(args.output).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        print(f'output_path={target}')
    print('PROFIT_RTD_BOOK_OOS_RESEARCH_REPORT=COMPLETED')
    print(f"evidence_status={report['evidence_status']}")
    print(f"clean_sessions={report['clean_sessions']}")
    print(f"quarantined_sessions={report['quarantined_sessions']}")
    print(f"clean_samples={report['clean_samples']}")
    print(f"positive_coverage_sessions={report['positive_coverage_sessions']}")
    print(f"negative_coverage_sessions={report['negative_coverage_sessions']}")
    print(f"max_pattern_n={report['max_pattern_n']}")
    print('evidence_reasons=' + '|'.join(report['evidence_reasons']))
    print('observational_only=True')
    print('predictive_claim_allowed=False')
    print('score_influence_allowed=False')
    print('decision_influence_allowed=False')
    print('order_execution_allowed=False')


if __name__ == '__main__':
    main()
