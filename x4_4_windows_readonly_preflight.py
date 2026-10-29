"""X4.4 Windows read-only environment preflight.

No imports of xlwings/win32com, no Excel COM binding, no workbook open,
no RTD reads, no subprocess launch, and no order placement.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import sys

SAFETY_FLAGS = {'orders_allowed': False, 'live_certified': False, 'flow_complete': False}


def inspect_environment(project_root: str, workbook: str, *, system=None, exists=None):
    """Pure metadata inspection; existence is not proof of a valid RTD connection."""
    if not isinstance(project_root, str) or not project_root.strip():
        raise ValueError('PROJECT_ROOT_REQUIRED')
    if not isinstance(workbook, str) or not workbook.strip():
        raise ValueError('WORKBOOK_PATH_REQUIRED')
    system = platform.system() if system is None else system
    exists = Path.is_file if exists is None else exists
    root = Path(project_root).expanduser().resolve(strict=False)
    book = Path(workbook).expanduser()
    if not book.is_absolute():
        book = root / book
    book = book.resolve(strict=False)
    checks = {
        'windows': system == 'Windows',
        'project_root_exists': root.is_dir(),
        'workbook_exists': bool(exists(book)),
        'excel_connector_exists': (root / 'connectors' / 'excel_connector.py').is_file(),
        'collector_exists': (root / 'market_data' / 'collector.py').is_file(),
        'supervisor_exists': (root / 'tools' / 'h10_rc3_18_3_3x2_observational_session.py').is_file(),
    }
    # Never assert a real Excel/Profit/RTD connection is ready from file checks.
    return {
        'phase': 'X4.4_WINDOWS_READONLY_PREFLIGHT',
        'mode': 'METADATA_ONLY',
        'python_version': platform.python_version(),
        'python_executable': sys.executable,
        'project_root': str(root),
        'workbook': str(book),
        'checks': checks,
        'safety': dict(SAFETY_FLAGS),
        'excel_com_accessed': False,
        'rtd_accessed': False,
        'orders_sent': False,
        'windows_metadata_ready': all(checks.values()),
        'live_rtd_certified': False,
        'next_gate': 'HUMAN_REVIEW_BEFORE_EXCEL_ACCESS',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', required=True)
    parser.add_argument('--workbook', required=True)
    parser.add_argument('--output', help='Optional JSON output path; no files modified except this output')
    args = parser.parse_args(argv)
    result = inspect_environment(args.project_root, args.workbook)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        dest = Path(args.output).expanduser().resolve(strict=False)
        if dest.exists():
            parser.error('OUTPUT_EXISTS_REFUSING_OVERWRITE')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(payload + '\n', encoding='utf-8')
    print(payload)
    return 0 if result['windows_metadata_ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
