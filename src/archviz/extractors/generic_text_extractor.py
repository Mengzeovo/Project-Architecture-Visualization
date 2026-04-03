from __future__ import annotations

from pathlib import Path

from ..models import Edge, EvidenceRef, Node
from ..utils import normalize_rel_path
from .base import ExtractionContext, Extractor


class GenericTextExtractor(Extractor):
    name = "generic-text"

    def run(self, context: ExtractionContext) -> None:
        language_file_sets = {
            "go": context.scan.go_files,
            "java": context.scan.java_files,
            "csharp": context.scan.csharp_files,
            "cpp": context.scan.cpp_files,
            "rust": context.scan.rust_files,
            "php": context.scan.php_files,
            "ruby": context.scan.ruby_files,
        }
        for language, files in language_file_sets.items():
            for path in files:
                self._add_module_node(context, path, language)

    def _add_module_node(self, context: ExtractionContext, path: Path, language: str) -> None:
        rel = normalize_rel_path(path, context.root)
        module_id = f"module:{rel}"
        container_id = context.container_id_for(path)
        evidence = EvidenceRef(file=rel, line=1, rule_id=f"node.file.{language}")

        context.graph.add_node(
            Node(
                id=module_id,
                type="module",
                name=rel,
                path=rel,
                tags=[language],
                confidence=0.9,
                evidence_refs=[evidence],
                metadata={"container_id": container_id},
            )
        )
        context.graph.add_edge(
            Edge(
                source=container_id,
                target=module_id,
                type="contains",
                confidence=0.9,
                evidence_refs=[evidence],
            )
        )
