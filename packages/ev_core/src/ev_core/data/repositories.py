"""Repository abstractions for processed datasets and metadata tables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class DatasetHandle:
    """Lightweight pointer to a named dataset artifact."""

    name: str
    path: Path
    format_hint: str = "unknown"


class DatasetRepository(Protocol):
    """Protocol for future dataset catalogs and storage backends."""

    def get(self, name: str) -> DatasetHandle:
        """Return the dataset handle for the requested artifact name."""

    def list(self) -> list[DatasetHandle]:
        """Return the known dataset handles."""


class FileSystemDatasetRepository:
    """Placeholder filesystem-backed repository for future use."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def get(self, name: str) -> DatasetHandle:
        raise NotImplementedError("TODO: implement dataset lookup conventions.")

    def list(self) -> list[DatasetHandle]:
        raise NotImplementedError("TODO: implement dataset discovery.")
