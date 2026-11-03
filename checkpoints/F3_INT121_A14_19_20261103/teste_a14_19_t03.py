from pathlib import Path
import hashlib
import subprocess
import sys

clone = Path(sys.argv[1])
auditor = Path(sys.argv[2])
references = Path(sys.argv[3])
python = sys.argv[4]

zip_path = (
    clone / "checkpoints" /
    "F3_INT121_A14_13_20261103" /
    "F3_INT121_A14_13_VALIDACAO_20261103.zip"
)

if not zip_path.is_file():
    raise SystemExit("ZIP_A14_13_AUSENTE")

original = zip_path.read_bytes()
original_sha = hashlib.sha256(original).hexdigest()

if len(original) < 128:
    raise SystemExit("ZIP_INVALIDO")

alterado = bytearray(original)
alterado[100] ^= 1

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

    print(f"T03_{mode}_CODIGO:", result.returncode)
    print(output[-1400:])

    if result.returncode == 0:
        raise RuntimeError(f"T03_{mode}_ZIP_ADULTERADO_ACEITO")

    if "ZIP_SHA256" not in output:
        raise RuntimeError(f"T03_{mode}_MOTIVO_INESPERADO")

    print(f"T03_{mode}: PASS")

try:
    zip_path.write_bytes(alterado)

    execute("NORMAL")
    execute("OTIMIZADO")

finally:
    zip_path.write_bytes(original)

    if hashlib.sha256(zip_path.read_bytes()).hexdigest() != original_sha:
        raise RuntimeError("T03_RESTAURACAO_FALHOU")

    print("T03_ZIP_RESTAURADO: PASS")

print("A14_19_T03_APROVADO")