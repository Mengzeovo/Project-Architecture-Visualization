from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import GraphBuilder
from ..scanner import ScanResult
from ..utils import normalize_rel_path


@dataclass(slots=True)
class ExtractionContext:
    root: Path
    scan: ScanResult
    graph: GraphBuilder
    service_roots: list[Path]

    def container_root_for(self, path: Path) -> Path:
        matches = [candidate for candidate in self.service_roots if candidate in (path, *path.parents)]
        if not matches:
            return self.root
        return max(matches, key=lambda item: len(item.parts))

    def container_id_for(self, path: Path) -> str:
        container_root = self.container_root_for(path)
        rel = normalize_rel_path(container_root, self.root)
        return "container:root" if rel == "." else f"container:{rel}"

    def container_name_for(self, path: Path) -> str:
        container_root = self.container_root_for(path)
        rel = normalize_rel_path(container_root, self.root)
        if rel == ".":
            return self.root.name
        return rel


class Extractor:
    name = "base"

    def run(self, context: ExtractionContext) -> None:
        raise NotImplementedError
