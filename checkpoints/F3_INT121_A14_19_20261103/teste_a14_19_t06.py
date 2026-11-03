from pathlib import Path
import hashlib
import json
import subprocess
import sys

repo = Path(sys.argv[1])
clone = Path(sys.argv[2])
auditor = Path(sys.argv[3])
references = Path(sys.argv[4])
python = sys.argv[5]

records = json.loads(references.read_text(encoding="utf-8"))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def normalize(data):
    if b"\r" in data.replace(b"\r\n", b""):
        raise RuntimeError("CR_ISOLADO")
    return data.replace(b"\r\n", b"\n")

if set(records) != {str(n) for n in range(12, 18)}:
    raise RuntimeError("REFERENCIAS_INCOMPLETAS")

for stage in range(12, 18):
    record = records[str(stage)]
    relative = record["path"]

    original = (repo / relative).read_bytes()
    isolated = (clone / relative).read_bytes()

    committed = subprocess.check_output(
        [
            "git", "-C", str(repo),
            "show",
            f"{record['commit']}:{relative}"
        ],
        stderr=subprocess.PIPE,
    )

    if sha(committed) != record["sha256_git"]:
        raise RuntimeError(f"GIT_MANIFESTO_DIVERGENTE_A14_{stage}")

    if normalize(original) != normalize(committed):
        raise RuntimeError(f"LOCAL_MANIFESTO_DIVERGENTE_A14_{stage}")

    if normalize(isolated) != normalize(committed):
        raise RuntimeError(f"CLONE_MANIFESTO_DIVERGENTE_A14_{stage}")

    if sha(original) != record["sha256_local"]:
        raise RuntimeError(f"LOCAL_HASH_DIVERGENTE_A14_{stage}")

    if sha(isolated) != record["sha256_local"]:
        raise RuntimeError(f"CLONE_HASH_DIVERGENTE_A14_{stage}")

    print(f"T06_MANIFESTO_A14_{stage}: PASS")

    zip_relative = (
        f"checkpoints/F3_INT121_A14_{stage}_20261103/"
        f"F3_INT121_A14_{stage}_VALIDACAO_20261103.zip"
    )

    zip_local = repo / zip_relative
    zip_clone = clone / zip_relative

    if not zip_local.is_file() or not zip_clone.is_file():
        raise RuntimeError(f"ZIP_AUSENTE_A14_{stage}")

    if sha(zip_local.read_bytes()) != sha(zip_clone.read_bytes()):
        raise RuntimeError(f"ZIP_DIVERGENTE_A14_{stage}")

    print(f"T06_ZIP_A14_{stage}: PASS")

auditor_original = repo / "auditoria_consolidada_a14_18.py"
auditor_clone = clone / "auditoria_consolidada_a14_18.py"

if not auditor_original.is_file() or not auditor_clone.is_file():
    raise RuntimeError("AUDITOR_A14_18_AUSENTE")

if normalize(auditor_original.read_bytes()) != normalize(auditor_clone.read_bytes()):
    raise RuntimeError("AUDITOR_A14_18_DIVERGENTE")

print("T06_AUDITOR_A14_18: PASS")

for mode in ("NORMAL", "OTIMIZADO"):
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

    if result.returncode != 0:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        raise RuntimeError(f"T06_AUDITOR_{mode}_FALHOU")

    if "A14_19_AUDITORIA_COMPLEMENTAR_APROVADA" not in result.stdout:
        raise RuntimeError(f"T06_MARCADOR_{mode}_AUSENTE")

    print(f"T06_AUDITOR_{mode}: PASS")

print("T06_ORIGINAIS_PRESERVADOS: PASS")
print("A14_19_T06_APROVADO")