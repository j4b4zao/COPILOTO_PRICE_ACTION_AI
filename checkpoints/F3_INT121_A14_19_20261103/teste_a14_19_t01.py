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

original = manifesto.read_bytes()
original_hash = hashlib.sha256(original).hexdigest()

try:
    manifesto.write_bytes(original + b" ")

    result = subprocess.run(
        [python, "-B", str(auditor), str(clone), str(references)],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=180,
    )

    output = result.stdout + result.stderr

    print("CODIGO_SAIDA:", result.returncode)
    print("SAIDA_FINAL:")
    print(output[-1500:])

    if result.returncode == 0:
        raise RuntimeError("T01_ADULTERACAO_ACEITA")

    if "MANIFESTO_BYTES_DIVERGENTES_A14_13" not in output:
        raise RuntimeError("T01_REJEICAO_INESPERADA")

    print("T01_ADULTERACAO_REJEITADA: PASS")

finally:
    manifesto.write_bytes(original)

    if hashlib.sha256(manifesto.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError("T01_RESTAURACAO_FALHOU")

    print("T01_MANIFESTO_RESTAURADO: PASS")

print("A14_19_T01_APROVADO")