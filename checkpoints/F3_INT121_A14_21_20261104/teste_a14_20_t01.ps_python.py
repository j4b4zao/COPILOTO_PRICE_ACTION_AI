from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile

repo = Path(sys.argv[1])
auditor = Path(sys.argv[2])
references = Path(sys.argv[3])
python = sys.argv[4]

original = references.read_bytes()
original_sha = hashlib.sha256(original).hexdigest()

records = json.loads(original.decode("utf-8"))

# Altera um hash histórico mantendo o JSON válido.
records["13"]["sha256_git"] = "0" * 64

with tempfile.TemporaryDirectory(prefix="F3_INT121_A14_20_T01_") as temp:
    altered = Path(temp) / "referencias_adulteradas.json"

    altered.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if altered.read_bytes() == original:
        raise RuntimeError("T01_ADULTERACAO_NAO_APLICADA")

    for mode in ("NORMAL", "OTIMIZADO"):
        command = [python]

        if mode == "OTIMIZADO":
            command.append("-O")

        command.extend([
            "-B",
            str(auditor),
            str(repo),
            str(altered),
        ])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=180,
        )

        output = result.stdout + result.stderr

        print(f"T01_{mode}_CODIGO:", result.returncode)

        if result.returncode == 0:
            raise RuntimeError(
                f"T01_{mode}_REFERENCIAS_ADULTERADAS_ACEITAS"
            )

        if "REFERENCIAS_SHA256_DIVERGENTE" not in output:
            print(output[-2000:])
            raise RuntimeError(
                f"T01_{mode}_REJEICAO_INESPERADA"
            )

        print(f"T01_{mode}: PASS")

if hashlib.sha256(references.read_bytes()).hexdigest() != original_sha:
    raise RuntimeError("T01_REFERENCIAS_ORIGINAIS_MODIFICADAS")

print("T01_REFERENCIAS_ORIGINAIS_PRESERVADAS: PASS")
print("A14_20_T01_APROVADO")