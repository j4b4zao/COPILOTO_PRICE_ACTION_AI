from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REFERENCE_SHA256 = (
    "3b01f874b8ad9bd0237241a85a827b47113435f71ee55bc7c45cc5681692d81e"
)

EXPECTED = {
    12: (
        "17689276ee52055f3fded0892da965816dd592e3",
        "72507b6df1a8ac4b79110384a87826a54247cf98434a5594b6fbf9fee2deb4c6",
    ),
    13: (
        "f20f0b2e90772b9919dcd9c9d00ac1e0f16d1d68",
        "e6974c449acc89ff94e8c5dc4326cc6e5b260a6434b72c91e5cebbc6d686292e",
    ),
    14: (
        "8eb42f8a72ff691d4cc58c877429df5469196b66",
        "cf162d48195d700af8856f61247fc93cb18a8a59db5f38fbd676844e6ac35d01",
    ),
    15: (
        "2a17ce70fffbd3e1203aa86059e5c86f1ff472d0",
        "d146df3ba9322e99fc90b0bc0be0cb352fb0d1af5071503490431d30599a1ea8",
    ),
    16: (
        "9d1c2666a2ff97d9ac6c54256f9dc45741a87d08",
        "13024a0913721f3791281ce673dec308a500f8e0ca155a59daacf06465454379",
    ),
    17: (
        "08e875dacb1dab9b38d750c910fb443bb1fb698a",
        "aadfb8d358d1a27c1acd4951f632626315a2b4f58ffff90c0b541456bff2cf2c",
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_lines(data: bytes) -> bytes:
    if b"\r" in data.replace(b"\r\n", b""):
        raise RuntimeError("TERMINACAO_LINHA_INVALIDA")
    return data.replace(b"\r\n", b"\n")


def expected_path(stage: int) -> str:
    return (
        f"checkpoints/F3_INT121_A14_{stage}_20261103/"
        f"MANIFESTO_A14_{stage}_20261103.json"
    )


def verify_references(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError("REFERENCIAS_AUSENTES")

    raw = path.read_bytes()

    if sha256(raw) != REFERENCE_SHA256:
        raise RuntimeError("REFERENCIAS_SHA256_DIVERGENTE")

    records = json.loads(raw.decode("utf-8"))

    if set(records) != {str(stage) for stage in EXPECTED}:
        raise RuntimeError("REFERENCIAS_CONJUNTO_INVALIDO")

    for stage, (commit, git_hash) in EXPECTED.items():
        record = records[str(stage)]

        if record["commit"] != commit:
            raise RuntimeError(f"COMMIT_REFERENCIA_INVALIDO_A14_{stage}")

        if record["path"] != expected_path(stage):
            raise RuntimeError(f"CAMINHO_REFERENCIA_INVALIDO_A14_{stage}")

        if record["sha256_git"] != git_hash:
            raise RuntimeError(f"HASH_REFERENCIA_INVALIDO_A14_{stage}")

    print("REFERENCIAS_SHA256_AUTENTICADAS: PASS")
    return records


def verify_manifest(root: Path, stage: int, record: dict) -> None:
    relative = expected_path(stage)
    local = root / relative

    if not local.is_file():
        raise RuntimeError(f"MANIFESTO_AUSENTE_A14_{stage}")

    committed = subprocess.check_output(
        [
            "git",
            "-C",
            str(root),
            "show",
            f"{record['commit']}:{relative}",
        ],
        stderr=subprocess.PIPE,
    )

    if sha256(committed) != record["sha256_git"]:
        raise RuntimeError(f"GIT_SHA256_DIVERGENTE_A14_{stage}")

    if normalize_lines(local.read_bytes()) != normalize_lines(committed):
        raise RuntimeError(f"MANIFESTO_ADULTERADO_A14_{stage}")

    print(f"MANIFESTO_A14_{stage}: PASS")


def run_inner_auditor(root: Path) -> None:
    auditor = root / "auditoria_consolidada_a14_18.py"

    if not auditor.is_file():
        raise RuntimeError("AUDITOR_A14_18_AUSENTE")

    command = [sys.executable]

    if sys.flags.optimize > 0:
        command.append("-O")

    command.extend(["-B", str(auditor), str(root)])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=180,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("AUDITOR_INTERNO_REPROVADO")

    if "A14_18_AUDITORIA_CONSOLIDADA_APROVADA" not in result.stdout:
        raise RuntimeError("MARCADOR_AUDITOR_INTERNO_AUSENTE")

    print(
        "AUDITOR_INTERNO_MODO:",
        "OTIMIZADO" if sys.flags.optimize else "NORMAL",
    )
    print("AUDITOR_INTERNO: PASS")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "USO: auditoria_a14_20.py RAIZ_REPOSITORIO REFERENCIAS_JSON"
        )

    root = Path(sys.argv[1]).resolve()
    references_path = Path(sys.argv[2]).resolve()

    records = verify_references(references_path)

    for stage in sorted(EXPECTED):
        verify_manifest(root, stage, records[str(stage)])

    run_inner_auditor(root)

    print("A14_20_AUDITORIA_APROVADA")


if __name__ == "__main__":
    main()