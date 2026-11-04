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

# Mantém os mesmos dados, mas altera a representação em bytes.
records = json.loads(original.decode("utf-8"))

with tempfile.TemporaryDirectory(prefix="F3_INT121_A14_20_T02_") as temp:
    altered = Path(temp) / "referencias_substituidas.json"

    altered.write_text(
        json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    if json.loads(altered.read_text(encoding="utf-8")) != records:
        raise RuntimeError("T02_DADOS_SEMANTICOS_DIVERGENTES")

    if altered.read_bytes() == original:
        raise RuntimeError("T02_BYTES_NAO_ALTERADOS")

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

        print(f"T02_{mode}_CODIGO:", result.returncode)

        if result.returncode == 0:
            raise RuntimeError(
                f"T02_{mode}_SUBSTITUICAO_ACEITA"
            )

        if "REFERENCIAS_SHA256_DIVERGENTE" not in output:
            print(output[-2000:])
            raise RuntimeError(
                f"T02_{mode}_REJEICAO_INESPERADA"
            )

        print(f"T02_{mode}: PASS")

if hashlib.sha256(references.read_bytes()).hexdigest() != original_sha:
    raise RuntimeError("T02_REFERENCIAS_ORIGINAIS_MODIFICADAS")

print("T02_REFERENCIAS_ORIGINAIS_PRESERVADAS: PASS")
print("A14_20_T02_APROVADO")