"""Explicitly authorized, single-session RC17 orchestration; dry-run by default."""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools import rc17_sideways_to_directional_evolution_evaluator as evaluator
from tools import rc17_sideways_to_directional_evolution_protocol_validator as validator

VERSION = "RC1-RC17-SIDEWAYS-TO-DIRECTIONAL-SESSION-RUNNER"
BRANCH = "brooks-stop-target-exact-audit-20260912"
EXPECTED_HEAD = "fb470247f926b7dd43fe905d10104794ec267606"
ROOT = Path(__file__).resolve().parents[1]


def git_value(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_session(*args, **kwargs):
    # Import only after every live gate has passed.
    from tools.profit_rtd_microstructure_prospective_session import run_session as capture
    return capture(*args, **kwargs)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw_snapshot(directory):
    if not directory.exists():
        return set()
    return {p.resolve() for p in directory.iterdir()
            if p.is_file() and p.name.startswith("profit_rtd_rc54_3_2_")
            and p.suffix == ".json"}


def exclusive_write(path, text):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)


def run(*, session_id, symbol, requested_cycles, confirm_session_id=None,
        execute_live=False, market_structure_observability_enabled=True,
        expected_head=EXPECTED_HEAD, protocol_path=None, output_dir=None,
        date=None):
    protocol_path = Path(protocol_path or ROOT / validator.PROTOCOL_PATH)
    directory = Path(output_dir or ROOT / "data/profit_rtd_rc54_3_2").resolve()
    stamp = date or datetime.now(timezone(timedelta(hours=-3))).strftime("%Y%m%d")
    result_path = directory / f"rc17_sideways_to_directional_evolution_session{session_id}_rc1_{stamp}.json"
    report_path = directory / f"saida_rc17_sideways_to_directional_session{session_id}_rc1_{stamp}.txt"
    report = dict(STATUS="ABORT", RUNNER_VERSION=VERSION, SESSION_ID=session_id,
        CONFIRM_SESSION_ID=confirm_session_id, MODE="LIVE" if execute_live else "DRY_RUN",
        BRANCH=None, HEAD=None, PROTOCOL_VERSION=None, PROTOCOL_SHA256=None,
        PROTOCOL_VALIDATOR_STATUS="NOT_RUN", SYMBOL=symbol,
        REQUESTED_CYCLES=requested_cycles, OBSERVABILITY_ENABLED=market_structure_observability_enabled,
        PRE_FLIGHT_STATUS="FAIL", CAPTURE_CALL_COUNT=0, COLLECTOR_CALL_COUNT=0,
        RAW_FILE=None, RAW_SHA256=None, RAW_SIZE=None, EVALUATOR_VERSION=evaluator.VERSION,
        EVALUATOR_STATUS="NOT_RUN", RESULT_JSON=None, RESULT_JSON_SHA256=None,
        SESSION_CLASSIFICATION=None, SESSION_NEXT_EXECUTED=False, SESSION19_EXECUTED=False)
    reserved = False
    result_reserved = False
    try:
        def require(condition, reason):
            if not condition:
                raise ValueError(reason)
        require(type(session_id) is int and session_id in range(19, 24), "session must be 19..23")
        require(confirm_session_id is None and not execute_live or
                type(confirm_session_id) is int and confirm_session_id == session_id,
                "session confirmation missing or mismatched")
        require(type(requested_cycles) is int and requested_cycles == 600, "requested_cycles must be 600")
        require(market_structure_observability_enabled is True, "observability required")
        require(isinstance(symbol, str) and re.fullmatch(r"[A-Za-z0-9_]+", symbol) is not None,
                "explicit safe symbol required")
        require(re.fullmatch(r"\d{8}", stamp) is not None, "date must be YYYYMMDD")
        report["BRANCH"] = git_value("branch", "--show-current")
        report["HEAD"] = git_value("rev-parse", "HEAD")
        require(report["BRANCH"] == BRANCH, "branch mismatch")
        require(re.fullmatch(r"[0-9a-f]{40}", expected_head) is not None and
                report["HEAD"] == expected_head, "HEAD mismatch")
        report["PROTOCOL_SHA256"] = sha(protocol_path.read_bytes())
        require(report["PROTOCOL_SHA256"] == validator.EXPECTED_SHA256, "protocol SHA mismatch")
        validated = validator.validate(protocol_path)
        report["PROTOCOL_VALIDATOR_STATUS"] = validated["status"]
        report["PROTOCOL_VERSION"] = validated["protocol_version"]
        require(validated["status"] == "PASS", "protocol validator failed")
        if execute_live:
            require(not result_path.exists() and not report_path.exists(), "output already exists")
        report["PRE_FLIGHT_STATUS"] = "PASS"
        if not execute_live:
            report["STATUS"] = "DRY_RUN_PASS"
            return report
        directory.mkdir(parents=True, exist_ok=True)
        # Reserve both names atomically before collection, preventing concurrent invocations.
        exclusive_write(report_path, "STATUS=LIVE_RESERVED\n")
        reserved = True
        exclusive_write(result_path, "")
        result_reserved = True
        before = raw_snapshot(directory)
        require(sha(protocol_path.read_bytes()) == validator.EXPECTED_SHA256, "protocol changed before capture")
        report["CAPTURE_CALL_COUNT"] = report["COLLECTOR_CALL_COUNT"] = 1
        report["SESSION19_EXECUTED"] = session_id == 19
        capture = run_session(symbol, cycles=requested_cycles, output_dir=str(directory),
                              market_structure_observability_enabled=True)
        require(isinstance(capture, dict) and capture.get("status") == "COMPLETED", "capture failed")
        added = raw_snapshot(directory) - before
        require(len(added) == 1, f"raw identity ambiguity: {len(added)} new raws")
        raw = added.pop()
        require(raw.name.startswith(f"profit_rtd_rc54_3_2_{symbol}_"), "raw symbol filename mismatch")
        require(capture.get("output_path") and Path(capture["output_path"]).resolve() == raw,
                "capture output_path mismatch")
        data = raw.read_bytes()
        report.update(RAW_FILE=str(raw), RAW_SHA256=sha(data), RAW_SIZE=len(data))
        require(sha(protocol_path.read_bytes()) == validator.EXPECTED_SHA256, "protocol changed after capture")
        report["EVALUATOR_STATUS"] = "RUNNING"
        evaluation = evaluator.evaluate(raw_path=raw, session_id=session_id, protocol_path=protocol_path)
        require(sha(raw.read_bytes()) == report["RAW_SHA256"], "raw changed during evaluation")
        classification = evaluation["session_classification"]
        report.update(EVALUATOR_STATUS="PASS", SESSION_CLASSIFICATION=classification,
                      STATUS=classification)
        payload = json.dumps(evaluation, indent=2, allow_nan=False) + "\n"
        result_path.write_text(payload, encoding="utf-8")
        report.update(RESULT_JSON=str(result_path), RESULT_JSON_SHA256=sha(result_path.read_bytes()))
    except Exception as exc:
        report.update(STATUS="ABORT", ERROR=f"{type(exc).__name__}: {exc}")
        if report["EVALUATOR_STATUS"] == "RUNNING":
            report["EVALUATOR_STATUS"] = "FAIL"
    finally:
        if result_reserved and report["RESULT_JSON"] is None:
            result_path.unlink()
        if reserved:
            report_path.write_text("\n".join(f"{k}={v}" for k, v in report.items()) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", type=int, required=True, choices=range(19, 24))
    parser.add_argument("--confirm-session-id", type=int)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--requested-cycles", type=int, required=True)
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--expected-head", default=EXPECTED_HEAD)
    parser.add_argument("--protocol-path")
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    report = run(**vars(args))
    print(json.dumps(report, indent=2))
    return 2 if report["STATUS"] == "ABORT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
