from pathlib import Path
import hashlib
import json
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
original_sha = hashlib.sha256(original).hexdigest()

data = json.loads(original.decode("utf-8-sig"))

if not isinstance(data.get("files"), list) or not data["files"]:
    raise SystemExit("INVENTARIO_INVALIDO")

record = data["files"][0]
old_sha = record.get("sha256")

if not isinstance(old_sha, str) or len(old_sha) != 64:
    raise SystemExit("SHA256_ORIGINAL_INVALIDO")

new_sha = ("0" if old_sha[0] != "0" else "1") + old_sha[1:]
record["sha256"] = new_sha

alterado = (
    json.dumps(data, ensure_ascii=False, indent=2) + "\n"
).encode("utf-8")

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

    print(f"T02_{mode}_CODIGO:", result.returncode)
    print(output[-1200:])

    if result.returncode == 0:
        raise RuntimeError(f"T02_{mode}_ACEITOU_HASH_ADULTERADO")

    if "MANIFESTO_BYTES_DIVERGENTES_A14_13" not in output:
        raise RuntimeError(f"T02_{mode}_REJEICAO_INESPERADA")

    print(f"T02_{mode}: PASS")

try:
    manifesto.write_bytes(alterado)

    execute("NORMAL")
    execute("OTIMIZADO")

finally:
    manifesto.write_bytes(original)

    if hashlib.sha256(manifesto.read_bytes()).hexdigest() != original_sha:
        raise RuntimeError("T02_RESTAURACAO_FALHOU")

    print("T02_MANIFESTO_RESTAURADO: PASS")

print("A14_19_T02_APROVADO")