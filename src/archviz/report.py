from __future__ import annotations

from pathlib import Path

from .models import GraphIR
from .transforms import low_confidence_edges, summarize_graph


def write_report(graph: GraphIR, output_path: Path) -> None:
    summary = summarize_graph(graph)
    low_conf_edges = low_confidence_edges(graph)

    lines = [
        "# Architecture Analysis Report",
        "",
        "## Summary",
        f"- Containers: {summary['containers']}",
        f"- Modules: {summary['modules']}",
        f"- Packages: {summary['packages']}",
        f"- Endpoints: {summary['endpoints']}",
        f"- Edges: {summary['edges']}",
        f"- Language tags discovered: {summary['language_tags']}",
        "",
        "## Confidence",
        f"- Low confidence edges (< 0.8): {len(low_conf_edges)}",
        "",
        "## Low confidence evidence",
    ]

    if not low_conf_edges:
        lines.append("- None")
    else:
        for edge in low_conf_edges[:50]:
            evidence = edge.evidence_refs[0] if edge.evidence_refs else None
            if evidence:
                lines.append(
                    f"- {edge.source} -> {edge.target} ({edge.type}, {edge.confidence:.2f}) from {evidence.file}:{evidence.line}"
                )
            else:
                lines.append(
                    f"- {edge.source} -> {edge.target} ({edge.type}, {edge.confidence:.2f})"
                )

    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
