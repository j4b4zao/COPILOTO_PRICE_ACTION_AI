"""Gravação explícita e atômica do catálogo psicológico (RC40)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile

from psychology.trader_psychology_session_catalog_export import (
    TraderPsychologySessionCatalogExport,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologySessionCatalogFileExportResult:
    status: str
    destination: str
    bytes_written: int
    sha256: str
    schema_version: str
    overwritten: bool
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologySessionCatalogFileExporter:
    """Persiste o catálogo somente sob chamada explícita e segura."""

    NAME = "TraderPsychologySessionCatalogFileExporter"
    VERSION = "RC40"

    def write(
        self,
        catalog_export,
        destination,
        *,
        overwrite=False,
    ):
        if not isinstance(
            catalog_export,
            TraderPsychologySessionCatalogExport,
        ):
            raise TypeError(
                "catalog_export deve ser "
                "TraderPsychologySessionCatalogExport."
            )
        if not isinstance(overwrite, bool):
            raise TypeError("overwrite deve ser booleano.")

        target = Path(destination)
        if not target.is_absolute():
            raise ValueError("destination deve ser caminho absoluto.")
        if target.suffix.casefold() != ".json":
            raise ValueError("destination deve terminar em .json.")
        if not target.parent.exists():
            raise FileNotFoundError(
                "Diretório de destino não existe."
            )
        if not target.parent.is_dir():
            raise NotADirectoryError(
                "Pai do destino não é diretório."
            )
        if target.is_symlink():
            raise ValueError(
                "Destino não pode ser link simbólico."
            )

        existed = target.exists()
        if existed and not overwrite:
            raise FileExistsError(
                "Destino já existe; use overwrite=True explicitamente."
            )

        content = (
            catalog_export.to_json(indent=2) + "\n"
        ).encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{target.name}.",
                suffix=".tmp",
                dir=target.parent,
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            if overwrite:
                os.replace(temporary, target)
            else:
                os.link(temporary, target)
                temporary.unlink()
            temporary = None
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

        return TraderPsychologySessionCatalogFileExportResult(
            status="WRITTEN",
            destination=str(target),
            bytes_written=len(content),
            sha256=digest,
            schema_version=catalog_export.schema_version,
            overwritten=existed,
        )
