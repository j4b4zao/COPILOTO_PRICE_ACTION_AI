import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

root = Path(sys.argv[1])

commits = {
    12: "17689276ee52055f3fded0892da965816dd592e3",
    13: "f20f0b2e90772b9919dcd9c9d00ac1e0f16d1d68",
    14: "8eb42f8a72ff691d4cc58c877429df5469196b66",
    15: "2a17ce70fffbd3e1203aa86059e5c86f1ff472d0",
    16: "9d1c2666a2ff97d9ac6c54256f9dc45741a87d08",
    17: "08e875dacb1dab9b38d750c910fb443bb1fb698a",
}

zip_hashes = {
    12: "24277bfe9de82a95e19bb9ed2884b3af122bdc56ddc8d4a92453fbd50fdc9f62",
    13: "fdfdcd55cb9b9f2dcf78f7149465861d405efed236af3dfc331544ed95c80363",
    14: "39370f0a67c393300a20628595d56e35a55abf28b2c99d8342a1b345a5c3f49d",
    15: "f9565ba02880c35718624e4190f9cec2c17204f2ebcb0067cad9e504178f845a",
    16: "56783d9db379dfb21c2faa34ee047abc7a6773f7003177640498c919c218bc4a",
    17: "f9c903327c9610e02ec7b0596fdd21b4d91918e4ab981ce539ff55de092d733f",
}

def check(condition, message):
    if not condition:
        raise RuntimeError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        stderr=subprocess.PIPE
    ).decode().strip()

def safe_name(name):
    p = PurePosixPath(name)
    check(
        isinstance(name, str)
        and bool(name)
        and "\\" not in name
        and not p.is_absolute()
        and ".." not in p.parts
        and not re.match(r"^[A-Za-z]:", name),
        f"CAMINHO_INVALIDO: {name}"
    )

print("=== A14.18 - AUDITORIA CONSOLIDADA CORRIGIDA ===")

total_verified = 0
total_zip_entries = 0
historical_tests = 0
shared = {}

for stage in range(12, 18):

    print(f"\n=== A14.{stage} ===")

    folder = root / "checkpoints" / f"F3_INT121_A14_{stage}_20261103"
    manifest_path = folder / f"MANIFESTO_A14_{stage}_20261103.json"
    zip_path = folder / f"F3_INT121_A14_{stage}_VALIDACAO_20261103.zip"

    check(manifest_path.is_file(), "MANIFESTO_AUSENTE")
    check(zip_path.is_file(), "ZIP_AUSENTE")

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8-sig")
    )

    zip_data = zip_path.read_bytes()
    zip_sha = digest(zip_data)

    check(
        zip_sha == zip_hashes[stage],
        f"ZIP_SHA256_DIVERGENTE_A14_{stage}"
    )

    if stage >= 13:
        check(
            manifest.get("phase") == f"F3-INT-121 A14.{stage}",
            "FASE_INVALIDA"
        )
        check(
            manifest.get("branch")
            == f"checkpoint/f3-int121-a14-{stage}-20261103",
            "BRANCH_MANIFESTO_INVALIDA"
        )
        check(
            manifest.get("parent_commit") == commits[stage - 1],
            "PARENT_MANIFESTO_INVALIDO"
        )
        check(
            git("rev-parse", f"{commits[stage]}^")
            == commits[stage - 1],
            "CADEIA_GIT_INVALIDA"
        )

        for key, expected in {
            "offline": True,
            "simulation_only": True,
            "certification": False,
            "real_operations_authorized": False,
        }.items():
            check(
                manifest.get(key) is expected,
                f"RESTRICAO_INVALIDA: {key}"
            )

        if stage >= 14:
            check(manifest.get("f3") == "OPEN", "F3_INVALIDO")
            check(
                manifest.get("production_api_changed") is False,
                "API_PRODUCAO_INVALIDA"
            )

        zip_record = manifest["zip"]

        check(zip_record["name"] == zip_path.name, "ZIP_NOME_INVALIDO")
        check(zip_record["sha256"] == zip_sha, "ZIP_MANIFESTO_INVALIDO")
        check(zip_record["bytes"] == len(zip_data), "ZIP_BYTES_INVALIDO")

        sidecar = folder / (zip_path.name + ".sha256")

        check(sidecar.is_file(), "SIDECAR_AUSENTE")
        check(
            sidecar.read_text(encoding="ascii").strip()
            == f"{zip_sha}  {zip_path.name}",
            "SIDECAR_DIVERGENTE"
        )

        records = manifest["files"]
        check(isinstance(records, list) and records, "FILES_INVALIDO")

        expected = {}

        for record in records:
            name = record["name"]
            safe_name(name)
            check(name not in expected, "ARQUIVO_DUPLICADO")
            expected[name] = record

        if "tests_total" in manifest:
            normal = manifest["tests_normal"]
            optimized = manifest["tests_optimized"]
            count = manifest["tests_total"]

            check(
                type(normal) is int
                and type(optimized) is int
                and type(count) is int
                and normal >= 0
                and optimized >= 0
                and count == normal + optimized,
                "CONTAGEM_TESTES_INVALIDA"
            )

            historical_tests += count
            print("TESTES_HISTORICOS:", count)

        if stage == 16:
            check(
                manifest.get("historical_tests_registered") == 24,
                "HISTORICO_A14_16_INVALIDO"
            )
            check(
                manifest.get("historical_tests_reexecuted") is False,
                "REEXECUCAO_A14_16_INVALIDA"
            )
            print("TESTES_HISTORICOS_REFERENCIADOS: 24")

    else:
        check(manifest.get("stage") == "A14.12", "STAGE_LEGADO_INVALIDO")
        check(
            manifest.get("status") == "A14_12_VALIDADA_LOCALMENTE",
            "STATUS_LEGADO_INVALIDO"
        )

        expected = manifest["files_sha256"]

        check(
            isinstance(expected, dict) and len(expected) == 181,
            "INVENTARIO_LEGADO_INVALIDO"
        )

    with ZipFile(zip_path) as archive:

        check(archive.testzip() is None, "ZIP_CRC_INVALIDO")

        names = archive.namelist()
        check(len(names) == len(set(names)), "ZIP_NOMES_DUPLICADOS")

        for name in names:
            safe_name(name)

        if stage == 12:
            check(len(names) == 320, "ZIP_LEGADO_ENTRADAS_DIVERGENTES")
            check(
                set(expected).issubset(set(names)),
                "ZIP_LEGADO_ARQUIVO_AUSENTE"
            )
            print("ENTRADAS_ADICIONAIS:", len(set(names) - set(expected)))
        else:
            check(
                set(names) == set(expected),
                "ZIP_ENTRADAS_DIVERGENTES"
            )

        for name, record in expected.items():

            content = archive.read(name)

            declared_sha = (
                record if stage == 12 else record["sha256"]
            )

            check(
                digest(content) == declared_sha,
                f"HASH_INTERNO_DIVERGENTE: {name}"
            )

            if stage >= 13:
                check(
                    len(content) == record["bytes"],
                    f"TAMANHO_INTERNO_DIVERGENTE: {name}"
                )

                local = root / name
                check(local.is_file(), f"ARQUIVO_LOCAL_AUSENTE: {name}")

                local_data = local.read_bytes()

                if local_data != content:
                    # Git pode normalizar LF/CRLF.
                    try:
                        committed = subprocess.check_output(
                            ["git", "-C", str(root),
                             "show", f"{commits[stage]}:{name}"],
                            stderr=subprocess.PIPE
                        )
                    except subprocess.CalledProcessError:
                        raise RuntimeError(
                            f"ARQUIVO_LOCAL_DIVERGENTE: {name}"
                        )

                    check(
                        committed == content,
                        f"ARQUIVO_COMMIT_DIVERGENTE: {name}"
                    )

                if name in (
                    "f3_int121_a14_8_journal.py",
                    "f3_int121_a14_11_budget.py"
                ):
                    previous = shared.get(name)

                    if previous is not None:
                        check(
                            previous == declared_sha,
                            f"MODULO_COMPARTILHADO_DIVERGENTE: {name}"
                        )

                    shared[name] = declared_sha

        total_verified += len(expected)
        total_zip_entries += len(names)

    print("ZIP_SHA256: PASS")
    print("CRC_ZIP: PASS")
    print("HASHES_INTERNOS:", len(expected), "PASS")
    print("MANIFESTO: PASS")

print("\n=== RESULTADO CONSOLIDADO ===")
print("CHECKPOINTS_AUDITADOS: 6")
print("HASHES_INTERNOS_VERIFICADOS:", total_verified)
print("ENTRADAS_ZIP_INSPECIONADAS:", total_zip_entries)
print("MODULOS_COMPARTILHADOS:", len(shared))
print("TESTES_HISTORICOS_REGISTRADOS:", historical_tests)
print("TESTES_REEXECUTADOS_NESTA_AUDITORIA: 0")
print("MODO: SOMENTE_LEITURA")
print("A14_18_AUDITORIA_CONSOLIDADA_APROVADA")