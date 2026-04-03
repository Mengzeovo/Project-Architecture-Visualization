from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .containers import discover_service_roots
from .extractors import (
    DependencyMetadataExtractor,
    ExtractionContext,
    GenericTextExtractor,
    PythonExtractor,
    TypeScriptExtractor,
)
from .models import EvidenceRef, GraphBuilder, GraphIR, Node
from .scanner import scan_project
from .transforms import enrich_graph, summarize_graph
from .utils import normalize_rel_path


@dataclass(slots=True)
class PipelineResult:
    graph: GraphIR
    scan_summary: dict[str, int]


class ArchitecturePipeline:
    def run(self, root: Path) -> PipelineResult:
        root = root.resolve()
        scan = scan_project(root)
        service_roots = discover_service_roots(scan)

        builder = GraphBuilder()
        context = ExtractionContext(root=root, scan=scan, graph=builder, service_roots=service_roots)

        self._seed_containers(context)
        self._run_extractors(context)

        graph = builder.build(metadata={"project_root": root.as_posix()})
        graph = enrich_graph(graph)

        scan_summary = {
            "python_files": len(scan.python_files),
            "ts_files": len(scan.ts_files),
            "go_files": len(scan.go_files),
            "java_files": len(scan.java_files),
            "csharp_files": len(scan.csharp_files),
            "cpp_files": len(scan.cpp_files),
            "rust_files": len(scan.rust_files),
            "php_files": len(scan.php_files),
            "ruby_files": len(scan.ruby_files),
            "containers": len(service_roots),
            **summarize_graph(graph),
        }
        return PipelineResult(graph=graph, scan_summary=scan_summary)

    def _seed_containers(self, context: ExtractionContext) -> None:
        for container_root in context.service_roots:
            rel = normalize_rel_path(container_root, context.root)
            container_id = "container:root" if rel == "." else f"container:{rel}"
            name = context.root.name if rel == "." else rel
            evidence_file = rel if rel != "." else "."
            evidence = EvidenceRef(file=evidence_file, line=1, rule_id="node.container")
            context.graph.add_node(
                Node(
                    id=container_id,
                    type="container",
                    name=name,
                    path=None if rel == "." else rel,
                    confidence=0.9,
                    evidence_refs=[evidence],
                    metadata={"kind": "auto_discovered"},
                )
            )

    def _run_extractors(self, context: ExtractionContext) -> None:
        extractors = [
            DependencyMetadataExtractor(),
            PythonExtractor(),
            TypeScriptExtractor(),
            GenericTextExtractor(),
        ]
        for extractor in extractors:
            extractor.run(context)
