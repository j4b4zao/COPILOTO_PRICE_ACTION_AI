from pathlib import Path
import hashlib
import subprocess
import sys

clone = Path(sys.argv[1])
auditor = Path(sys.argv[2])
references = Path(sys.argv[3])
python = sys.argv[4]

manifesto = (
    clone / "checkpoints" /
    "F3_INT121_A14_13_20261103" /
    "MANIFESTO_A14_13_20261103.json"
)

if not manifesto.is_file():
    raise SystemExit("T04_PRECONDICAO_MANIFESTO_AUSENTE")

original = manifesto.read_bytes()
original_sha = hashlib.sha256(original).hexdigest()

def execute(mode):
    command = [python]

    if mode == "OTIMIZADO":
        command.append("-O")

    command += [
        "-B",
        str(auditor),
        str(clone),
        str(references),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=180,
    )

    output = result.stdout + result.stderr

    print(f"T04_{mode}_CODIGO:", result.returncode)
    print(output[-1000:])

    if result.returncode == 0:
        raise RuntimeError(
            f"T04_{mode}_ARQUIVO_AUSENTE_ACEITO"
        )

    if "MANIFESTO_AUSENTE_A14_13" not in output:
        raise RuntimeError(
            f"T04_{mode}_REJEICAO_INESPERADA"
        )

    print(f"T04_{mode}: PASS")

try:
    manifesto.unlink()

    execute("NORMAL")
    execute("OTIMIZADO")

finally:
    if not manifesto.exists():
        manifesto.write_bytes(original)

    if hashlib.sha256(manifesto.read_bytes()).hexdigest() != original_sha:
        raise RuntimeError("T04_RESTAURACAO_FALHOU")

    print("T04_MANIFESTO_RESTAURADO: PASS")

print("A14_19_T04_APROVADO")