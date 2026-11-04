"""Executa os testes unitários F3-INT-121 em um clone local descartável."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


BASE = "30cab14bf21eca4441ea3a2921c13e9b0d2035ea"
TESTS = (
    "test_f3_int121_a14_13_adversarial",
    "test_f3_int121_a14_14_consistency",
    "test_f3_int121_a14_15_persistence",
    "test_f3_int121_a14_17_adversarial",
)
MODULES = (
    "f3_int121_a14_8_journal.py",
    "f3_int121_a14_11_budget.py",
    "auditoria_cruzada_a14_16.py",
)


def materialize(repo):
    files = [*MODULES, *(f"{test}.py" for test in TESTS)]
    for stage in (13, 14, 15):
        folder = f"checkpoints/F3_INT121_A14_{stage}_20261103"
        package = f"F3_INT121_A14_{stage}_VALIDACAO_20261103.zip"
        files.extend(f"{folder}/{name}" for name in (
            f"MANIFESTO_A14_{stage}_20261103.json", package, f"{package}.sha256",
        ))
    hashes = {}
    for name in files:
        data = subprocess.check_output(
            ["git", "-C", str(repo), "cat-file", "blob", f"{BASE}:{name}"], timeout=60,
        )
        target = repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    return hashes


def run_tests(repo, optimized):
    options = ["-O"] if optimized else []
    result = subprocess.run(
        [sys.executable, *options, "-B", "-E", "-s", "-m", "unittest", "-v", *TESTS],
        cwd=repo, capture_output=True, text=True, errors="replace", timeout=180,
    )
    output = result.stdout + result.stderr
    count = re.search(r"^Ran (\d+) tests? in ", output, re.MULTILINE)
    passed = [line for line in output.splitlines() if line.endswith(" ... ok")]
    if result.returncode or not count or not passed or int(count[1]) != len(passed):
        raise RuntimeError(f"unittest (exit={result.returncode})\n{output}")
    return {
        "modo": "otimizado" if optimized else "normal",
        "testes_aprovados": len(passed),
        "testes": [line.removesuffix(" ... ok") for line in passed],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="a14_29_") as temp:
        repo = Path(temp) / "repo"
        subprocess.run(
            ["git", "clone", "--quiet", "--shared", "--no-checkout", str(args.repo.resolve()), str(repo)],
            check=True, timeout=180,
        )
        hashes = materialize(repo)
        results = [run_tests(repo, optimized) for optimized in (False, True)]
        if results[0]["testes"] != results[1]["testes"]:
            raise RuntimeError("Conjuntos de testes diferentes entre os modos")
        for name, expected in hashes.items():
            if hashlib.sha256((repo / name).read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"Fixture alterada: {name}")
    print(json.dumps({
        "etapa": "F3-INT-121 A14.29",
        "commit_base": BASE,
        "python": sys.version.split()[0],
        "sha256_script": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "estado_operacional": {
            "f3": "OPEN", "offline": True, "simulation_only": True,
            "certification": False, "real_operations_authorized": False,
            "production_api_changed": False,
        },
        "sha256_arquivos_versionados": hashes,
        "execucoes": results,
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
