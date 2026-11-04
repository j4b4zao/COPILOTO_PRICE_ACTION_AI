"""Reexecuta offline os testes T01–T06 preservados pela A14.21 e A14.22."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from zipfile import ZipFile


BASE = "ecb79b4f792301503599cf8dea5d876352477a68"
BRANCH = "checkpoint/f3-int121-a14-22-20261104"
A14_18 = "cfc6f64c9a1bd30586dc90ff0a91bd936aebb0cf"
A14_21 = "d42d35b385e7cf76406cf70fc5a38a5ea277a61d"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], timeout=180)


def extract(repo, tree, path, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(git(repo, "cat-file", "blob", f"{tree}:{path}"))
    return target


def run_case(name, script, args, marker, optimize=False):
    flags = ["-O", "-B"] if optimize else ["-B"]
    result = subprocess.run(
        [sys.executable, *flags, str(script), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240,
    )
    if result.returncode or marker not in result.stdout.splitlines():
        raise RuntimeError(f"{name} (exit={result.returncode})\n{result.stdout}{result.stderr}")
    return {"caso": name, "codigo": result.returncode, "saida": result.stdout.splitlines()}


def replay(source, temp):
    repo = temp / "repo"
    subprocess.run(
        ["git", "clone", "--quiet", "--shared", "--no-checkout", str(source), str(repo)],
        check=True, timeout=180,
    )
    git(repo, "rev-parse", "--verify", f"{BASE}^{{commit}}")
    git(repo, "branch", BRANCH, A14_21)
    git(repo, "symbolic-ref", "HEAD", f"refs/heads/{BRANCH}")
    tools = temp / "scripts"
    refs_name = "a14_19_manifestos_referencias.json"
    tools.mkdir()
    refs = tools / refs_name
    package = "F3_INT121_A14_19_VALIDACAO_20261103.zip"
    extract(repo, BASE, f"checkpoints/F3_INT121_A14_19_20261103/{package}", tools / package)
    with ZipFile(tools / package) as archive:
        refs.write_bytes(archive.read(refs_name))
    auditor = extract(repo, BASE, "checkpoints/F3_INT121_A14_20_20261104/auditoria_a14_20.py", tools / "auditoria_a14_20.py")
    inner_name = "auditoria_consolidada_a14_18.py"
    inner = extract(repo, BASE, inner_name, repo / inner_name)
    for stage in range(12, 18):
        folder = f"checkpoints/F3_INT121_A14_{stage}_20261103"
        package = f"F3_INT121_A14_{stage}_VALIDACAO_20261103.zip"
        for name in (f"MANIFESTO_A14_{stage}_20261103.json", package, f"{package}.sha256"):
            path = f"{folder}/{name}"
            extract(repo, BASE, path, repo / path)

        if stage >= 13:
            manifest = json.loads((repo / folder / f"MANIFESTO_A14_{stage}_20261103.json").read_bytes())
            with ZipFile(repo / folder / package) as archive:
                for record in manifest["files"]:
                    name = record["name"]
                    if Path(name).name != name or ":" in name:
                        raise RuntimeError(f"Nome de fixture inesperado: {name}")
                    content = archive.read(name)
                    if hashlib.sha256(content).hexdigest() != record["sha256"]:
                        raise RuntimeError(f"Hash de fixture divergente: {name}")
                    target = repo / name
                    if target.exists() and target.read_bytes() != content:
                        raise RuntimeError(f"Fixture compartilhada divergente: {name}")
                    target.write_bytes(content)

    cases = []
    for optimize in (False, True):
        mode = "otimizado" if optimize else "normal"
        cases.append(run_case(f"auditor_{mode}", auditor, (repo, refs), "A14_20_AUDITORIA_APROVADA", optimize))
    common = (repo, auditor, refs, sys.executable)
    for stage, suffix, args in (
        (1, "t01.ps_python", common),
        (2, "t02", common),
        (3, "t03_corrigido", common),
        (5, "t05", (repo, inner, A14_18)),
        (6, "t06", (repo, auditor, inner, refs, sys.executable)),
    ):
        name = f"teste_a14_20_{suffix}.py"
        script = extract(repo, BASE, f"checkpoints/F3_INT121_A14_21_20261104/{name}", tools / name)
        cases.append(run_case(f"T{stage:02}", script, args, f"A14_20_T{stage:02}_APROVADO"))

    name = "teste_a14_20_t04_cadeia_commits.py"
    script = extract(repo, BASE, f"checkpoints/F3_INT121_A14_22_20261104/{name}", tools / name)
    for optimize in (False, True):
        mode = "otimizado" if optimize else "normal"
        cases.append(run_case(f"T04_{mode}", script, (repo,), "A14_22_T02_T04_APROVADO", optimize))
    if git(repo, "rev-parse", "HEAD").decode().strip() != A14_21:
        raise RuntimeError("HEAD do cenário histórico foi alterado")
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="a14_28_") as temp:
        cases = replay(args.repo.resolve(), Path(temp))
    print(json.dumps({
        "etapa": "F3-INT-121 A14.28",
        "commit_base": BASE,
        "python": sys.version.split()[0],
        "sha256_script": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "estado_operacional": {
            "f3": "OPEN", "offline": True, "simulation_only": True,
            "certification": False, "real_operations_authorized": False,
            "production_api_changed": False,
        },
        "execucoes": cases,
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
