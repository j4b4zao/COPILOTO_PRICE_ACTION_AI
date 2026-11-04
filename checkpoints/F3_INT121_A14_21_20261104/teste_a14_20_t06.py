from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile

repo = Path(sys.argv[1])
auditor = Path(sys.argv[2])
interno = Path(sys.argv[3])
references = Path(sys.argv[4])
python = sys.argv[5]

original_sha = hashlib.sha256(interno.read_bytes()).hexdigest()

with tempfile.TemporaryDirectory(prefix="A14_20_T06_") as temp:
    root = Path(temp)

    # Cria uma cópia isolada do auditor interno.
    altered = root / "auditoria_consolidada_a14_18.py"
    altered.write_bytes(interno.read_bytes() + b"\n# T06 ALTERACAO CONTROLADA\n")

    if hashlib.sha256(altered.read_bytes()).hexdigest() == original_sha:
        raise RuntimeError("T06_ADULTERACAO_NAO_APLICADA")

    # O auditor A14.20 será executado com raiz temporária.
    # As referências históricas são verificadas antes do auditor interno.
    # Para chegar à etapa de autenticação do auditor interno,
    # criamos somente os manifestos necessários.

    import json

    records = json.loads(references.read_text(encoding="utf-8"))

    for stage in range(12, 18):
        record = records[str(stage)]
        relative = record["path"]

        content = subprocess.check_output([
            "git",
            "-C",
            str(repo),
            "show",
            f"{record['commit']}:{relative}",
        ])

        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    # Os comandos git executados pelo auditor precisam encontrar
    # um repositório válido. Criamos um vínculo de leitura por
    # meio de um arquivo .git apontando para o repositório original.
    gitdir = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "--absolute-git-dir"],
        text=True,
    ).strip()

    (root / ".git").write_text(
        f"gitdir: {gitdir}\n",
        encoding="utf-8",
    )

    for mode in ("NORMAL", "OTIMIZADO"):
        command = [python]

        if mode == "OTIMIZADO":
            command.append("-O")

        command.extend([
            "-B",
            str(auditor),
            str(root),
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

        print(f"T06_{mode}_CODIGO:", result.returncode)

        if result.returncode == 0:
            raise RuntimeError(f"T06_{mode}_AUDITOR_ADULTERADO_ACEITO")

        if "AUDITOR_A14_18_SHA256_DIVERGENTE" not in output:
            print(output[-2500:])
            raise RuntimeError(f"T06_{mode}_REJEICAO_INESPERADA")

        print(f"T06_{mode}: PASS")

if hashlib.sha256(interno.read_bytes()).hexdigest() != original_sha:
    raise RuntimeError("T06_AUDITOR_ORIGINAL_MODIFICADO")

print("T06_AUDITOR_ORIGINAL_PRESERVADO: PASS")
print("A14_20_T06_APROVADO")