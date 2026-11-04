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

relative = (
    "checkpoints/F3_INT121_A14_13_20261103/"
    "MANIFESTO_A14_13_20261103.json"
)

original = repo / relative
original_hash = hashlib.sha256(original.read_bytes()).hexdigest()

with tempfile.TemporaryDirectory(prefix="A14_20_T03_") as temp:
    clone = Path(temp) / "git"

    subprocess.run(
        [
            "git", "clone",
            "--no-local",
            "--no-checkout",
            "--quiet",
            str(repo),
            str(clone),
        ],
        check=True,
        timeout=180,
    )

    # Extrai somente os manifestos históricos necessários.
    for stage in range(12, 18):
        rel = (
            f"checkpoints/F3_INT121_A14_{stage}_20261103/"
            f"MANIFESTO_A14_{stage}_20261103.json"
        )

        commit = json.loads(
            references.read_text(encoding="utf-8")
        )[str(stage)]["commit"]

        content = subprocess.check_output(
            ["git", "-C", str(clone), "show", f"{commit}:{rel}"]
        )

        target = clone / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    target = clone / relative

    data = json.loads(target.read_text(encoding="utf-8"))
    data["simulation_only"] = False

    target.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    for mode in ("NORMAL", "OTIMIZADO"):
        command = [python]

        if mode == "OTIMIZADO":
            command.append("-O")

        command.extend([
            "-B",
            str(auditor),
            str(clone),
            str(references),
        ])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=180,
        )

        output = result.stdout + result.stderr

        print(f"T03_{mode}_CODIGO:", result.returncode)

        if result.returncode == 0:
            raise RuntimeError(
                f"T03_{mode}_MANIFESTO_ADULTERADO_ACEITO"
            )

        if "MANIFESTO_ADULTERADO_A14_13" not in output:
            print(output[-2000:])
            raise RuntimeError(
                f"T03_{mode}_REJEICAO_INESPERADA"
            )

        print(f"T03_{mode}: PASS")

if hashlib.sha256(original.read_bytes()).hexdigest() != original_hash:
    raise RuntimeError("T03_ORIGINAL_MODIFICADO")

print("T03_ORIGINAL_PRESERVADO: PASS")
print("A14_20_T03_APROVADO")