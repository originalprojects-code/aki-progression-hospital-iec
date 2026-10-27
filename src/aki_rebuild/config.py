"""Typed, validated configuration for an approved Paper 1 rebuild run."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import tomllib


REQUIRED_BILLING_LIMIT = 5_000_000_000


@dataclass(frozen=True)
class RebuildConfig:
    source_project_id: str
    source_dataset: str
    destination_project_id: str
    destination_dataset: str
    run_id: str
    landmark_hours: int
    outcome_horizon_hours: int
    maximum_bytes_billed: int

    def __post_init__(self) -> None:
        required_strings = {
            "source_project_id": self.source_project_id,
            "source_dataset": self.source_dataset,
            "destination_project_id": self.destination_project_id,
            "destination_dataset": self.destination_dataset,
            "run_id": self.run_id,
        }
        if any(not value or not value.strip() for value in required_strings.values()):
            raise ValueError("Project, datasets, and run ID must be non-empty.")
        if self.landmark_hours != 12:
            raise ValueError("Paper 1 rebuild landmark must be exactly 12 hours.")
        if self.outcome_horizon_hours != 72:
            raise ValueError("Paper 1 rebuild outcome horizon must be exactly 72 hours.")
        if self.maximum_bytes_billed != REQUIRED_BILLING_LIMIT:
            raise ValueError(
                "maximum_bytes_billed must be exactly "
                f"{REQUIRED_BILLING_LIMIT}."
            )

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def load_config(path: str | Path) -> RebuildConfig:
    """Load a TOML config without consulting environment variables or credentials."""
    with Path(path).open("rb") as handle:
        values = tomllib.load(handle)
    return RebuildConfig(**values)
