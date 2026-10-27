"""Reproducibility manifest creation; it records metadata but executes no SQL."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import importlib.metadata
import json
import platform
import subprocess
from typing import Iterable

from .config import RebuildConfig


@dataclass(frozen=True)
class ExecutionMetadata:
    run_id: str
    status: str
    started_at_utc: str
    completed_at_utc: str | None = None
    query_count: int = 0


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit(repository: str | Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
    ).strip()


def package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def build_manifest(
    *,
    config: RebuildConfig,
    repository: str | Path,
    sql_files: Iterable[str | Path],
    execution: ExecutionMetadata | None = None,
) -> dict[str, object]:
    """Build a serializable manifest from local files only."""
    metadata = execution or ExecutionMetadata(
        run_id=config.run_id,
        status="not_executed",
        started_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    if metadata.run_id != config.run_id:
        raise ValueError("Execution metadata run_id must match configuration run_id.")

    hashed_sql = {
        str(Path(path).as_posix()): sha256_file(path)
        for path in sorted(sql_files, key=lambda item: str(item))
    }
    return {
        "manifest_version": 1,
        "code_commit": git_commit(repository),
        "configuration_sha256": config.sha256(),
        "configuration": asdict(config),
        "sql_sha256": hashed_sql,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "google_cloud_bigquery": package_version("google-cloud-bigquery"),
        },
        "execution": asdict(metadata),
    }


def write_manifest(manifest: dict[str, object], path: str | Path) -> None:
    """Write a manifest explicitly requested by an approved pipeline stage."""
    Path(path).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
