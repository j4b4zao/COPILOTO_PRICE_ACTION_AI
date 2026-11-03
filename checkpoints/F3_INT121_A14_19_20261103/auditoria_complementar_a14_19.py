from pathlib import Path
import hashlib
import json
import subprocess
import sys

root = Path(sys.argv[1])
references_path = Path(sys.argv[2])

references = json.loads(
    references_path.read_text(encoding="utf-8")
)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical_lines(data):
    # Aceita LF ou CRLF, mas rejeita CR isolado.
    if b"\r" in data.replace(b"\r\n", b""):
        raise RuntimeError("TERMINACAO_LINHA_INVALIDA")

    return data.replace(b"\r\n", b"\n")

def verify_manifest(stage, record):
    path = root / record["path"]

    if not path.is_file():
        raise RuntimeError(f"MANIFESTO_AUSENTE_A14_{stage}")

    committed = subprocess.check_output(
        [
            "git", "-C", str(root),
            "show",
            f"{record['commit']}:{record['path']}"
        ],
        stderr=subprocess.PIPE,
    )

    if sha(committed) != record["sha256_git"]:
        raise RuntimeError(
            f"REFERENCIA_GIT_DIVERGENTE_A14_{stage}"
        )

    current = path.read_bytes()

    if canonical_lines(current) != canonical_lines(committed):
        raise RuntimeError(
            f"MANIFESTO_BYTES_DIVERGENTES_A14_{stage}"
        )

    print(f"MANIFESTO_A14_{stage}_INTEGRO: PASS")

def main():
    if len(references) != 6:
        raise RuntimeError("QUANTIDADE_REFERENCIAS_INVALIDA")

    for stage in range(12, 18):
        record = references[str(stage)]
        verify_manifest(stage, record)

    auditor = root / "auditoria_consolidada_a14_18.py"

    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(auditor),
            str(root)
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=180,
    )

    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("AUDITOR_A14_18_REPROVADO")

    if "A14_18_AUDITORIA_CONSOLIDADA_APROVADA" not in result.stdout:
        raise RuntimeError("MARCADOR_A14_18_AUSENTE")

    print("AUDITOR_A14_18: PASS")
    print("A14_19_AUDITORIA_COMPLEMENTAR_APROVADA")

if __name__ == "__main__":
    main()