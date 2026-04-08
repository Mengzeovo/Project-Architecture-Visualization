from __future__ import annotations

from pathlib import Path

from .features.models import FeatureBuildResult
from .models import GraphIR
from .transforms import low_confidence_edges, summarize_graph


def write_report(
    graph: GraphIR,
    output_path: Path,
    features: FeatureBuildResult | None = None,
) -> None:
    summary = summarize_graph(graph)
    low_conf_edges = low_confidence_edges(graph)
    low_conf_feature_modules = _low_confidence_feature_modules(features)

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
    ]

    if features is not None:
        lines.extend(
            [
                f"- Features: {len(features.features)}",
                f"- Unassigned modules: {len(features.unassigned_modules)}",
            ]
        )

    lines.extend(
        [
            "",
            "## Confidence",
            f"- Low confidence edges (< 0.8): {len(low_conf_edges)}",
            f"- Low confidence module assignments (< 0.8): {len(low_conf_feature_modules)}",
            "",
            "## Low confidence evidence",
        ]
    )

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

    if low_conf_feature_modules:
        lines.extend(["", "## Low confidence feature assignment details"])
        for feature_name, module_path, confidence in low_conf_feature_modules[:50]:
            lines.append(f"- `{module_path}` -> {feature_name} ({confidence:.2f})")

    if features is not None:
        overrides = _feature_map_overrides(features)
        lines.extend(["", "## Feature map overrides"])
        if not overrides:
            lines.append("- None")
        else:
            for feature_name, module_path, reason in overrides[:100]:
                lines.append(f"- `{module_path}` -> {feature_name} ({reason})")

        lines.extend(["", "## Unassigned modules"])
        if not features.unassigned_modules:
            lines.append("- None")
        else:
            for module_id in features.unassigned_modules[:100]:
                lines.append(f"- `{module_id}`")

    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def _low_confidence_feature_modules(
    features: FeatureBuildResult | None,
    threshold: float = 0.8,
) -> list[tuple[str, str, float]]:
    if features is None:
        return []
    rows: list[tuple[str, str, float]] = []
    for feature in features.features:
        for module in feature.modules:
            if module.confidence < threshold:
                rows.append((feature.name, module.path, module.confidence))
    rows.sort(key=lambda item: item[2])
    return rows


def _feature_map_overrides(features: FeatureBuildResult) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for feature in features.features:
        for module in feature.modules:
            if module.reason.startswith("feature-map"):
                rows.append((feature.name, module.path, module.reason))
    rows.sort(key=lambda item: (item[0], item[1]))
    return rows
