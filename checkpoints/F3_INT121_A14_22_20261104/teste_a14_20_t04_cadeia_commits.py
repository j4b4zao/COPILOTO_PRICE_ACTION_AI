"""A14.22: reproducao independente do teste historico T04."""

import subprocess
import sys
from pathlib import Path


COMMITS = (
    ("A14.12", "17689276ee52055f3fded0892da965816dd592e3"),
    ("A14.13", "f20f0b2e90772b9919dcd9c9d00ac1e0f16d1d68"),
    ("A14.14", "8eb42f8a72ff691d4cc58c877429df5469196b66"),
    ("A14.15", "2a17ce70fffbd3e1203aa86059e5c86f1ff472d0"),
    ("A14.16", "9d1c2666a2ff97d9ac6c54256f9dc45741a87d08"),
    ("A14.17", "08e875dacb1dab9b38d750c910fb443bb1fb698a"),
    ("A14.18", "cfc6f64c9a1bd30586dc90ff0a91bd936aebb0cf"),
    ("A14.19", "01384da2387819af3efecc94929d2f18e9ec0366"),
    ("A14.20", "d361e35383efec65c041a70540d994444b58c352"),
    ("A14.21", "d42d35b385e7cf76406cf70fc5a38a5ea277a61d"),
)

EXPECTED_BRANCH = "checkpoint/f3-int121-a14-22-20261104"


def run_git(repo, *args):
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"GIT_FALHOU: {' '.join(args)}: {result.stderr.strip()}"
        )

    return result.stdout.strip()


def main():
    if len(sys.argv) != 2:
        raise RuntimeError("USO: script.py CAMINHO_REPOSITORIO")

    repo = Path(sys.argv[1]).resolve()

    if not repo.is_dir():
        raise RuntimeError("REPOSITORIO_AUSENTE")

    branch = run_git(repo, "branch", "--show-current")

    if branch != EXPECTED_BRANCH:
        raise RuntimeError("BRANCH_INCORRETA")

    head = run_git(repo, "rev-parse", "HEAD")

    if head != COMMITS[-1][1]:
        raise RuntimeError("HEAD_INCORRETO")

    print("BRANCH: PASS")
    print("HEAD: PASS")

    for etapa, commit in COMMITS:
        actual = run_git(
            repo,
            "rev-parse",
            "--verify",
            f"{commit}^{{commit}}",
        )

        if actual != commit:
            raise RuntimeError(f"COMMIT_DIVERGENTE: {etapa}")

        print(f"COMMIT_{etapa}: PASS")

    for index in range(1, len(COMMITS)):
        etapa_anterior, commit_anterior = COMMITS[index - 1]
        etapa_atual, commit_atual = COMMITS[index]

        linha = run_git(
            repo,
            "rev-list",
            "--parents",
            "-n",
            "1",
            commit_atual,
        )

        partes = linha.split()

        if len(partes) != 2:
            raise RuntimeError(f"PARENTS_INVALIDOS: {etapa_atual}")

        if partes[0] != commit_atual:
            raise RuntimeError(f"COMMIT_ATUAL_DIVERGENTE: {etapa_atual}")

        if partes[1] != commit_anterior:
            raise RuntimeError(
                f"CADEIA_DIVERGENTE: {etapa_anterior} -> {etapa_atual}"
            )

        print(f"CADEIA_{etapa_anterior}_{etapa_atual}: PASS")

    print("COMMITS_VERIFICADOS:", len(COMMITS))
    print("LIGACOES_PARENT:", len(COMMITS) - 1)
    print("MODIFICACOES_PELO_SCRIPT: NENHUMA")
    print("A14_22_T02_T04_APROVADO")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"A14_22_T02_FALHOU: {exc}", file=sys.stderr)
        sys.exit(1)