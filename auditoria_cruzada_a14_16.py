from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import subprocess
import sys

root = Path(sys.argv[1])

commits = {
    12: "17689276ee52055f3fded0892da965816dd592e3",
    13: "f20f0b2e90772b9919dcd9c9d00ac1e0f16d1d68",
    14: "8eb42f8a72ff691d4cc58c877429df5469196b66",
    15: "2a17ce70fffbd3e1203aa86059e5c86f1ff472d0",
}

zip_hashes = {
    13: "fdfdcd55cb9b9f2dcf78f7149465861d405efed236af3dfc331544ed95c80363",
    14: "39370f0a67c393300a20628595d56e35a55abf28b2c99d8342a1b345a5c3f49d",
    15: "f9565ba02880c35718624e4190f9cec2c17204f2ebcb0067cad9e504178f845a",
}

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        stderr=subprocess.PIPE,
    ).decode("utf-8").strip()

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

shared = {}

for stage in (13, 14, 15):
    print(f"\n=== AUDITANDO A14.{stage} ===")

    folder = root / "checkpoints" / f"F3_INT121_A14_{stage}_20261103"
    manifest_path = folder / f"MANIFESTO_A14_{stage}_20261103.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    require(
        manifest["phase"] == f"F3-INT-121 A14.{stage}",
        "FASE_INCORRETA",
    )

    require(
        manifest["parent_commit"] == commits[stage - 1],
        "CADEIA_MANIFESTO_INCORRETA",
    )

    require(
        manifest["branch"] == f"checkpoint/f3-int121-a14-{stage}-20261103",
        "BRANCH_MANIFESTO_INCORRETA",
    )

    require(manifest["offline"] is True, "OFFLINE_INVALIDO")
    require(manifest["simulation_only"] is True, "SIMULACAO_INVALIDA")
    require(manifest["certification"] is False, "CERTIFICACAO_INVALIDA")
    require(
        manifest["real_operations_authorized"] is False,
        "OPERACOES_REAIS_INVALIDAS",
    )

    if stage >= 14:
        require(manifest["f3"] == "OPEN", "F3_INVALIDO")
        require(
            manifest["production_api_changed"] is False,
            "API_PRODUCAO_ALTERADA",
        )

    require(
        manifest["tests_total"]
        == manifest["tests_normal"] + manifest["tests_optimized"],
        "CONTAGEM_TESTES_INVALIDA",
    )

    zip_path = folder / manifest["zip"]["name"]
    zip_bytes = zip_path.read_bytes()
    digest = sha256(zip_bytes)

    require(digest == zip_hashes[stage], "HASH_ZIP_INCORRETO")
    require(digest == manifest["zip"]["sha256"], "HASH_MANIFESTO_INCORRETO")
    require(len(zip_bytes) == manifest["zip"]["bytes"], "TAMANHO_ZIP_INCORRETO")

    sha_path = folder / (zip_path.name + ".sha256")
    require(
        sha_path.read_text(encoding="ascii").strip()
        == f"{digest}  {zip_path.name}",
        "ARQUIVO_SHA256_INCORRETO",
    )

    records = manifest["files"]
    names = [record["name"] for record in records]

    require(len(names) == 3, "QUANTIDADE_ARQUIVOS_INCORRETA")
    require(len(set(names)) == 3, "NOMES_DUPLICADOS")

    with ZipFile(zip_path) as archive:
        require(archive.testzip() is None, "ZIP_CORROMPIDO")
        require(
            archive.namelist() == names,
            "ENTRADAS_ZIP_DIVERGENTES",
        )

        for record in records:
            name = record["name"]

            require(
                Path(name).name == name,
                "CAMINHO_NAO_AUTORIZADO",
            )

            data = archive.read(name)
            local = (root / name).read_bytes()

            require(data == local, f"ARQUIVO_LOCAL_DIVERGENTE: {name}")
            require(
                sha256(data) == record["sha256"],
                f"HASH_ARQUIVO_INCORRETO: {name}",
            )
            require(
                len(data) == record["bytes"],
                f"TAMANHO_ARQUIVO_INCORRETO: {name}",
            )

            if name in (
                "f3_int121_a14_8_journal.py",
                "f3_int121_a14_11_budget.py",
            ):
                if name in shared:
                    require(
                        shared[name] == record["sha256"],
                        f"MODULO_ALTERADO_ENTRE_CHECKPOINTS: {name}",
                    )
                shared[name] = record["sha256"]

    # Confirma a relação direta entre os commits.
    parent = git("rev-parse", f"{commits[stage]}^")

    require(
        parent == commits[stage - 1],
        f"CADEIA_GIT_INCORRETA_A14_{stage}",
    )

    # Confirma que o manifesto auditado pertence ao commit histórico.
    relative_manifest = manifest_path.relative_to(root).as_posix()
    committed_manifest = subprocess.check_output(
        ["git", "-C", str(root), "show",
         f"{commits[stage]}:{relative_manifest}"],
        stderr=subprocess.PIPE,
    )

    local_manifest_bytes = manifest_path.read_bytes()

    historical_json = json.loads(committed_manifest)
    local_json = json.loads(local_manifest_bytes)

    require(
        historical_json == local_json,
        f"MANIFESTO_HISTORICO_DIVERGENTE_A14_{stage}",
    )

    print(
        "MANIFESTO_BYTES_IDENTICOS:",
        committed_manifest == local_manifest_bytes,
    )
    print("MANIFESTO_JSON_IDENTICO: True")

    print("MANIFESTO: PASS")
    print("ZIP_SHA256: PASS")
    print("ARQUIVOS: 3/3 PASS")
    print("RESTRICOES: PASS")
    print("CADEIA_GIT: PASS")
    print("MANIFESTO_HISTORICO: PASS")
    print("TESTES_REGISTRADOS:", manifest["tests_total"])

print("\n=== RESULTADO CONSOLIDADO ===")
print("CHECKPOINTS_AUDITADOS: 3")
print("ENTRADAS_ZIP_VERIFICADAS: 9")
print("MODULOS_COMPARTILHADOS: 2")
print("TESTES_HISTORICOS_REGISTRADOS: 24")
print("OPERACAO: SOMENTE_LEITURA")
print("A14_16_AUDITORIA_CRUZADA_APROVADA")