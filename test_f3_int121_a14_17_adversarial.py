"""F3-INT-121 A14.17: testes adversariais offline do auditor A14.16.

Executar a partir da raiz do projeto:
  python -B -m unittest -v test_f3_int121_a14_17_adversarial
  python -O -B -m unittest -v test_f3_int121_a14_17_adversarial

Os testes negativos modificam apenas copias em diretorios temporarios.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AUDITOR = ROOT / "auditoria_cruzada_a14_16.py"
STAGE_DIR = Path("checkpoints/F3_INT121_A14_13_20261103")
MANIFEST_NAME = "MANIFESTO_A14_13_20261103.json"
ZIP_NAME = "F3_INT121_A14_13_VALIDACAO_20261103.zip"


class TestA1417Adversarial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not AUDITOR.is_file():
            raise RuntimeError(f"AUDITOR_A14_16_AUSENTE: {AUDITOR}")
        if not (ROOT / STAGE_DIR / MANIFEST_NAME).is_file():
            raise RuntimeError("CHECKPOINT_A14_13_AUSENTE")

    def run_auditor(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(AUDITOR), str(root)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
            timeout=45,
        )

    def fixture(self, destination: Path) -> Path:
        """Copia somente A14.13 e seus tres arquivos, sem alterar originais."""
        source = ROOT / STAGE_DIR
        target = destination / STAGE_DIR
        target.mkdir(parents=True, exist_ok=False)
        manifest = json.loads((source / MANIFEST_NAME).read_text(encoding="utf-8"))
        for filename in (MANIFEST_NAME, ZIP_NAME, ZIP_NAME + ".sha256"):
            shutil.copyfile(source / filename, target / filename)
        for record in manifest["files"]:
            name = record["name"]
            if Path(name).name != name:
                raise RuntimeError("NOME_DE_ARQUIVO_INSEGURO_NA_FIXTURE")
            shutil.copyfile(ROOT / name, destination / name)
        return target

    def expect_rejected(self, root: Path, marker: str) -> None:
        result = self.run_auditor(root)
        combined = result.stdout + "\n" + result.stderr
        self.assertNotEqual(result.returncode, 0, combined)
        self.assertIn(marker, combined, combined)
        self.assertNotIn("A14_16_AUDITORIA_CRUZADA_APROVADA", combined)

    def test_t01_manifesto_adulterado_rejeitado(self):
        with tempfile.TemporaryDirectory(prefix="a1417_t01_") as tmp:
            stage = self.fixture(Path(tmp))
            path = stage / MANIFEST_NAME
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["offline"] = False
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.expect_rejected(Path(tmp), "OFFLINE_INVALIDO")

    def test_t02_sha256_lateral_adulterado_rejeitado(self):
        with tempfile.TemporaryDirectory(prefix="a1417_t02_") as tmp:
            stage = self.fixture(Path(tmp))
            (stage / (ZIP_NAME + ".sha256")).write_text(
                "0" * 64 + "  " + ZIP_NAME + "\n", encoding="ascii"
            )
            self.expect_rejected(Path(tmp), "ARQUIVO_SHA256_INCORRETO")

    def test_t03_zip_adulterado_rejeitado(self):
        with tempfile.TemporaryDirectory(prefix="a1417_t03_") as tmp:
            stage = self.fixture(Path(tmp))
            path = stage / ZIP_NAME
            data = bytearray(path.read_bytes())
            self.assertTrue(data)
            data[len(data) // 2] ^= 0x01
            path.write_bytes(data)
            self.expect_rejected(Path(tmp), "HASH_ZIP_INCORRETO")

    def test_t04_arquivo_ausente_rejeitado(self):
        with tempfile.TemporaryDirectory(prefix="a1417_t04_") as tmp:
            stage = self.fixture(Path(tmp))
            manifest = json.loads((stage / MANIFEST_NAME).read_text(encoding="utf-8"))
            (Path(tmp) / manifest["files"][0]["name"]).unlink()
            result = self.run_auditor(Path(tmp))
            combined = result.stdout + "\n" + result.stderr
            self.assertNotEqual(result.returncode, 0, combined)
            self.assertIn("FileNotFoundError", combined)
            self.assertNotIn("A14_16_AUDITORIA_CRUZADA_APROVADA", combined)

    def test_t05_cadeia_manifesto_adulterada_rejeitada(self):
        with tempfile.TemporaryDirectory(prefix="a1417_t05_") as tmp:
            stage = self.fixture(Path(tmp))
            path = stage / MANIFEST_NAME
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["parent_commit"] = "0" * 40
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.expect_rejected(Path(tmp), "CADEIA_MANIFESTO_INCORRETA")

    def test_t06_evidencias_originais_aprovadas(self):
        result = self.run_auditor(ROOT)
        combined = result.stdout + "\n" + result.stderr
        self.assertEqual(result.returncode, 0, combined)
        self.assertIn("CHECKPOINTS_AUDITADOS: 3", combined)
        self.assertIn("ENTRADAS_ZIP_VERIFICADAS: 9", combined)
        self.assertIn("A14_16_AUDITORIA_CRUZADA_APROVADA", combined)


if __name__ == "__main__":
    unittest.main()
