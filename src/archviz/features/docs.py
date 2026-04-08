from __future__ import annotations

import json
from pathlib import Path

from .config import FeatureMap
from .models import Feature, FeatureBuildResult
from .views import feature_slug


def write_feature_docs(
    result: FeatureBuildResult,
    output_dir: Path,
    feature_map: FeatureMap | None = None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index_path = output_dir / "feature-index.md"
    index_path.write_text(_build_feature_index(result, feature_map=feature_map), encoding="utf-8")
    written.append(index_path)

    features_dir = output_dir / "features"
    features_dir.mkdir(parents=True, exist_ok=True)

    for feature in result.features:
        feature_dir = features_dir / feature_slug(feature.feature_id)
        feature_dir.mkdir(parents=True, exist_ok=True)

        design_path = feature_dir / "design.md"
        design_path.write_text(_build_design_doc(feature), encoding="utf-8")
        written.append(design_path)

        evidence_path = feature_dir / "evidence.json"
        evidence_payload = {
            "feature_id": feature.feature_id,
            "feature_name": feature.name,
            "confidence": feature.confidence,
            "evidence_refs": [item.to_dict() for item in feature.evidence_refs],
            "module_evidence": {
                module.path: [item.to_dict() for item in module.evidence_refs]
                for module in feature.modules
            },
            "dependency_evidence": {
                dependency.target_feature_id: [item.to_dict() for item in dependency.evidence_refs]
                for dependency in feature.dependencies
            },
            "external_interaction_evidence": {
                interaction.target_id: [item.to_dict() for item in interaction.evidence_refs]
                for interaction in feature.external_interactions
            },
        }
        evidence_path.write_text(json.dumps(evidence_payload, indent=2), encoding="utf-8")
        written.append(evidence_path)

    return written


def _build_feature_index(result: FeatureBuildResult, feature_map: FeatureMap | None = None) -> str:
    lines = [
        "# Feature Index",
        "",
        f"- Total features: {len(result.features)}",
        f"- Assigned modules: {len(result.module_to_feature)}",
        f"- Unassigned modules: {len(result.unassigned_modules)}",
        (
            f"- Feature map: `{feature_map.source_path}` ({len(feature_map.features)} rule groups)"
            if feature_map and feature_map.source_path
            else "- Feature map: not used"
        ),
        "",
        "## Features",
    ]

    if not result.features:
        lines.extend(["", "- None"])
    else:
        for feature in result.features:
            slug = feature_slug(feature.feature_id)
            lines.append(
                f"- [{feature.name}](features/{slug}/design.md) "
                f"(modules: {len(feature.modules)}, confidence: {feature.confidence:.2f}, "
                f"dependencies: {len(feature.dependencies)})"
            )

    lines.append("")
    if result.unassigned_modules:
        lines.append("## Unassigned Modules")
        for module_id in result.unassigned_modules:
            lines.append(f"- `{module_id}`")
    else:
        lines.extend(["## Unassigned Modules", "- None"])

    return "\n".join(lines).strip() + "\n"


def _build_design_doc(feature: Feature) -> str:
    lines = [
        f"# Feature: {feature.name}",
        "",
        "## Functional Goal",
        f"- This feature groups {len(feature.modules)} module(s) that implement related behavior.",
        "",
        "## Entrypoints",
    ]

    if feature.entrypoints:
        for entrypoint in feature.entrypoints:
            lines.append(f"- `{entrypoint}`")
    else:
        lines.append("- None discovered")

    lines.extend(["", "## Core Modules"])
    if feature.modules:
        for module in feature.modules:
            lines.append(
                f"- `{module.path}` (reason: {module.reason}, confidence: {module.confidence:.2f})"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Dependencies"])
    if feature.dependencies:
        for dependency in feature.dependencies:
            edge_types = "/".join(dependency.edge_types) if dependency.edge_types else "depends_on"
            lines.append(
                f"- Feature `{dependency.target_feature_name}` "
                f"({edge_types}, confidence: {dependency.confidence:.2f})"
            )
    else:
        lines.append("- No cross-feature dependency detected")

    lines.extend(["", "## External Interactions"])
    if feature.external_interactions:
        for interaction in feature.external_interactions:
            edge_types = "/".join(interaction.edge_types) if interaction.edge_types else "depends_on"
            lines.append(
                f"- `{interaction.target_name}` ({interaction.target_type}, {edge_types}, "
                f"confidence: {interaction.confidence:.2f})"
            )
    else:
        lines.append("- None detected")

    lines.extend(["", "## Evidence"])
    if feature.evidence_refs:
        for evidence in feature.evidence_refs[:50]:
            lines.append(f"- `{evidence.file}:{evidence.line}` (rule: {evidence.rule_id})")
    else:
        lines.append("- None")

    return "\n".join(lines).strip() + "\n"
