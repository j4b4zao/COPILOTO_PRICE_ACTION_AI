"""Verifica a leitura do journal após interrupção simulada do gravador."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


BASE = "c3a8169103611e16279980da00538a645783b16b"
RECORD = {
    "schema": "A14_7_STARTUP_RECORD",
    "subject_cleanup_scope": "INNER_JOB_AND_DIRECT_LAUNCH_PROCESS_ONLY",
    "f3": "OPEN",
    "offline": True,
    "simulation_only": True,
    "real_operations_authorized": False,
    "runtime_modified": False,
    "production_api_changed": False,
    "constructor_evidence_is_private": True,
    "full_subtree_exit_requires_outer_safety_proof": True,
    "sequence": 1,
}
WRITER = """
import os
from pathlib import Path
import sys

path, mode, payload = sys.argv[1:]
with Path(path).open("wb") as stream:
    data = payload.encode("utf-8")
    if mode == "interrompido":
        stream.write(data[:len(data) // 2])
        stream.flush()
        os._exit(23)
    stream.write(data)
"""
READER = """
import json
from pathlib import Path
import sys

import f3_int121_a14_11_budget as budget

result = budget.read(Path(sys.argv[1]), json.loads(sys.argv[2]))
verification = result["verification"]
print(json.dumps({
    "status": result["status"],
    "aceito": verification["accepted"],
    "sha256": verification["sha256"],
    "tentativas": len(result["attempts"]),
    "production_api_changed": result["production_api_changed"],
}))
"""


def encode(record):
    return json.dumps(record, separators=(",", ":"), sort_keys=True)


def run_case(root, optimized):
    flags = ["-O"] if optimized else []
    command = [sys.executable, *flags, "-B", "-E", "-s"]
    journal = root / "journal.json"
    original = encode(RECORD)
    steps = (
        ("original", "completo", original, 0, "CONTENT_MATCH", True),
        ("interrupcao", "interrompido", original, 23, "INVALID_JSON", False),
        ("substituicao", "completo", encode(dict(RECORD, sequence=2)), 0, "CONTENT_MISMATCH", False),
        ("recuperacao", "completo", original, 0, "CONTENT_MATCH", True),
    )
    evidence = []
    for name, mode, payload, exit_code, status, accepted in steps:
        writer = subprocess.run(
            [*command, "-c", WRITER, str(journal), mode, payload],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
        if writer.returncode != exit_code:
            raise RuntimeError(f"Gravador {name}: {writer.returncode} {writer.stderr}")
        reader = subprocess.check_output(
            [*command, "-c", READER, str(journal), original], cwd=root, timeout=30,
        )
        written = payload.encode("utf-8")
        if mode == "interrompido":
            written = written[:len(written) // 2]
        digest = hashlib.sha256(written).hexdigest()
        result = json.loads(reader)
        if result != {
            "status": status, "aceito": accepted, "sha256": digest,
            "tentativas": 1, "production_api_changed": False,
        }:
            raise RuntimeError(f"Leitor {name}: {result}")
        evidence.append({"cenario": name, "saida_gravador": exit_code, **result})
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    hashes = {}
    with tempfile.TemporaryDirectory(prefix="a14_30_") as temp:
        root = Path(temp)
        for name in ("f3_int121_a14_8_journal.py", "f3_int121_a14_11_budget.py"):
            data = subprocess.check_output(
                ["git", "-C", str(args.repo.resolve()), "cat-file", "blob", f"{BASE}:{name}"],
                timeout=60,
            )
            (root / name).write_bytes(data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        normal = run_case(root, False)
        optimized = run_case(root, True)
        if normal != optimized:
            raise RuntimeError("Resultados diferentes entre os modos")
    print(json.dumps({
        "etapa": "F3-INT-121 A14.30",
        "commit_base": BASE,
        "python": sys.version.split()[0],
        "sha256_script": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sha256_modulos": hashes,
        "escopo": "Interrupcao do gravador apos flush para o sistema operacional, com um novo leitor por cenario.",
        "estado_operacional": {
            "f3": "OPEN", "offline": True, "simulation_only": True,
            "certification": False, "real_operations_authorized": False,
            "production_api_changed": False,
        },
        "execucoes": {"normal": normal, "otimizado": optimized},
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
