from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..constants import ENTRYPOINT_BASENAMES
from ..models import Edge, EvidenceRef, GraphIR, Node
from ..utils import sanitize_d2_identifier
from .config import FeatureMap
from .models import (
    Feature,
    FeatureBuildResult,
    FeatureDependency,
    FeatureExternalInteraction,
    FeatureModule,
)


_SKIP_SEGMENTS = {
    "src",
    "lib",
    "app",
    "apps",
    "services",
    "service",
    "modules",
    "module",
    "features",
    "feature",
    "internal",
    "pkg",
    "cmd",
    "commands",
    "server",
    "client",
    "api",
    "core",
    "domain",
    "infra",
    "infrastructure",
    "common",
    "shared",
    "utils",
    "tests",
    "test",
    "__pycache__",
}

_ENTRYPOINT_BASENAMES = {item.lower() for item in ENTRYPOINT_BASENAMES}

_PRIMARY_EDGE_TYPES = {
    "imports",
    "http",
    "reads",
    "writes",
    "publishes",
    "subscribes",
}


@dataclass(slots=True)
class _ModuleAssignment:
    feature_key: str
    confidence: float
    reason: str
    evidence_refs: list[EvidenceRef]
    entrypoint: bool


def build_features(graph: GraphIR, feature_map: FeatureMap | None = None) -> FeatureBuildResult:
    module_nodes = [node for node in graph.nodes if node.type == "module" and isinstance(node.path, str)]
    module_by_id = {node.id: node for node in module_nodes}
    module_by_path = {node.path: node for node in module_nodes if node.path}

    route_sources = _route_source_modules(graph, module_by_path)

    assignments: dict[str, _ModuleAssignment] = {}
    for node in module_nodes:
        assignment = _assign_module(node, route_sources, feature_map=feature_map)
        assignments[node.id] = assignment

    expanded_assignments = _expand_from_entrypoints(graph, assignments)
    assignments = _merge_assignments(assignments, expanded_assignments)

    grouped_ids: dict[str, list[str]] = defaultdict(list)
    for module_id, assignment in assignments.items():
        grouped_ids[assignment.feature_key].append(module_id)

    features: list[Feature] = []
    for feature_key, module_ids in sorted(grouped_ids.items(), key=lambda item: item[0]):
        module_ids_sorted = sorted(module_ids)
        feature_id = _feature_id(feature_key)
        feature_name = _feature_name(feature_key)

        feature_modules: list[FeatureModule] = []
        feature_evidence: list[EvidenceRef] = []
        entrypoints: list[str] = []
        confidences: list[float] = []

        for module_id in module_ids_sorted:
            node = module_by_id[module_id]
            assignment = assignments[module_id]
            path = node.path or node.name
            feature_modules.append(
                FeatureModule(
                    module_id=module_id,
                    path=path,
                    confidence=assignment.confidence,
                    reason=assignment.reason,
                    entrypoint=assignment.entrypoint,
                    evidence_refs=assignment.evidence_refs,
                )
            )
            feature_evidence.extend(assignment.evidence_refs)
            confidences.append(assignment.confidence)
            if assignment.entrypoint:
                entrypoints.append(path)

        feature = Feature(
            feature_id=feature_id,
            name=feature_name,
            entrypoints=sorted(set(entrypoints)),
            modules=feature_modules,
            confidence=round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
            evidence_refs=_dedupe_evidence(feature_evidence),
            metadata={
                "module_count": len(feature_modules),
                "entrypoint_count": len(set(entrypoints)),
                "feature_map": bool(feature_map and feature_map.features),
            },
        )
        features.append(feature)

    module_to_feature: dict[str, str] = {
        module_id: _feature_id(assignment.feature_key)
        for module_id, assignment in sorted(assignments.items(), key=lambda item: item[0])
    }

    _populate_feature_relationships(graph, features, module_to_feature, module_by_id)

    unassigned = [module.id for module in module_nodes if module.id not in module_to_feature]
    return FeatureBuildResult(
        features=sorted(features, key=lambda item: item.feature_id),
        module_to_feature=module_to_feature,
        unassigned_modules=sorted(unassigned),
    )


def _assign_module(
    node: Node,
    route_sources: set[str],
    feature_map: FeatureMap | None = None,
) -> _ModuleAssignment:
    path = node.path or node.name
    parts = Path(path).as_posix().split("/")
    basename = parts[-1].lower() if parts else ""

    entrypoint = basename in _ENTRYPOINT_BASENAMES or node.id in route_sources

    if feature_map is not None:
        mapped = feature_map.classify_path(path)
        if mapped:
            feature_key, confidence, reason = mapped
            return _ModuleAssignment(
                feature_key=feature_key,
                confidence=confidence,
                reason=reason,
                evidence_refs=[_path_evidence(path, reason)],
                entrypoint=entrypoint,
            )

    explicit_segment = _pick_explicit_feature_segment(parts)
    if explicit_segment:
        confidence = 0.92 if entrypoint else 0.85
        evidence = _path_evidence(path, "feature.classifier.path")
        return _ModuleAssignment(
            feature_key=explicit_segment,
            confidence=confidence,
            reason="path-segment",
            evidence_refs=[evidence],
            entrypoint=entrypoint,
        )

    stem = _feature_key_from_basename(basename)
    if stem:
        confidence = 0.88 if entrypoint else 0.72
        evidence = _path_evidence(path, "feature.classifier.basename")
        return _ModuleAssignment(
            feature_key=stem,
            confidence=confidence,
            reason="basename",
            evidence_refs=[evidence],
            entrypoint=entrypoint,
        )

    fallback = _fallback_key(parts)
    confidence = 0.78 if entrypoint else 0.62
    evidence = _path_evidence(path, "feature.classifier.fallback")
    return _ModuleAssignment(
        feature_key=fallback,
        confidence=confidence,
        reason="fallback",
        evidence_refs=[evidence],
        entrypoint=entrypoint,
    )


def _expand_from_entrypoints(
    graph: GraphIR,
    assignments: dict[str, _ModuleAssignment],
) -> dict[str, _ModuleAssignment]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        if edge.type != "imports":
            continue
        if not edge.source.startswith("module:") or not edge.target.startswith("module:"):
            continue
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)

    expanded: dict[str, _ModuleAssignment] = {}
    entry_modules = [module_id for module_id, info in assignments.items() if info.entrypoint]
    for entry_module in entry_modules:
        start = assignments[entry_module]
        feature_key = start.feature_key
        frontier = [entry_module]
        visited = {entry_module}
        depth = 0

        while frontier and depth < 3:
            next_frontier: list[str] = []
            for module_id in frontier:
                for neighbor in adjacency.get(module_id, set()):
                    if neighbor in visited:
                        continue
                    visited.add(neighbor)
                    next_frontier.append(neighbor)
                    existing = assignments.get(neighbor)
                    if not existing:
                        continue
                    if existing.reason == "fallback" and depth <= 1:
                        expanded_conf = max(existing.confidence, 0.84 - depth * 0.05)
                        evidence = [
                            EvidenceRef(
                                file=existing.evidence_refs[0].file if existing.evidence_refs else "<unknown>",
                                line=1,
                                rule_id="feature.classifier.entrypoint_propagation",
                                snippet=f"from {entry_module}",
                            )
                        ]
                        expanded[neighbor] = _ModuleAssignment(
                            feature_key=feature_key,
                            confidence=expanded_conf,
                            reason="entrypoint-propagation",
                            evidence_refs=evidence,
                            entrypoint=existing.entrypoint,
                        )
            frontier = next_frontier
            depth += 1
    return expanded


def _merge_assignments(
    base: dict[str, _ModuleAssignment],
    updates: dict[str, _ModuleAssignment],
) -> dict[str, _ModuleAssignment]:
    merged = dict(base)
    for module_id, new_assignment in updates.items():
        existing = merged.get(module_id)
        if not existing:
            merged[module_id] = new_assignment
            continue
        if new_assignment.confidence > existing.confidence:
            merged[module_id] = new_assignment
    return merged


def _route_source_modules(graph: GraphIR, module_by_path: dict[str, Node]) -> set[str]:
    route_nodes = {node.id for node in graph.nodes if node.type == "api_endpoint"}
    results: set[str] = set()
    if not route_nodes:
        return results

    for node in graph.nodes:
        if node.type != "api_endpoint":
            continue
        for evidence in node.evidence_refs:
            module_node = module_by_path.get(evidence.file)
            if module_node:
                results.add(module_node.id)

    for edge in graph.edges:
        if edge.type != "exposes":
            continue
        if edge.target not in route_nodes:
            continue
        if edge.source.startswith("module:"):
            results.add(edge.source)
    return results


def _populate_feature_relationships(
    graph: GraphIR,
    features: list[Feature],
    module_to_feature: dict[str, str],
    module_by_id: dict[str, Node],
) -> None:
    feature_by_id = {feature.feature_id: feature for feature in features}
    dependency_map: dict[tuple[str, str], list[Edge]] = defaultdict(list)
    interaction_map: dict[tuple[str, str], list[Edge]] = defaultdict(list)

    for edge in graph.edges:
        if edge.type not in _PRIMARY_EDGE_TYPES:
            continue

        source_feature_id = module_to_feature.get(edge.source)
        target_feature_id = module_to_feature.get(edge.target)

        if source_feature_id and target_feature_id and source_feature_id != target_feature_id:
            dependency_map[(source_feature_id, target_feature_id)].append(edge)
            continue

        if source_feature_id and edge.target.startswith(
            ("external_api:", "database:", "queue:", "cache:", "package:")
        ):
            interaction_map[(source_feature_id, edge.target)].append(edge)

    for (source_feature_id, target_feature_id), edges in sorted(dependency_map.items(), key=lambda item: item[0]):
        source_feature = feature_by_id.get(source_feature_id)
        target_feature = feature_by_id.get(target_feature_id)
        if not source_feature or not target_feature:
            continue
        dependency = FeatureDependency(
            target_feature_id=target_feature_id,
            target_feature_name=target_feature.name,
            edge_types=sorted({edge.type for edge in edges}),
            sources=sorted({module_by_id[edge.source].path or edge.source for edge in edges if edge.source in module_by_id}),
            confidence=round(sum(edge.confidence for edge in edges) / len(edges), 3),
            evidence_refs=_dedupe_evidence([ref for edge in edges for ref in edge.evidence_refs]),
        )
        source_feature.dependencies.append(dependency)

    graph_nodes = {node.id: node for node in graph.nodes}
    for (feature_id, target_id), edges in sorted(interaction_map.items(), key=lambda item: item[0]):
        source_feature = feature_by_id.get(feature_id)
        target_node = graph_nodes.get(target_id)
        if not source_feature or not target_node:
            continue
        interaction = FeatureExternalInteraction(
            target_id=target_id,
            target_name=target_node.name,
            target_type=target_node.type,
            edge_types=sorted({edge.type for edge in edges}),
            sources=sorted({module_by_id[edge.source].path or edge.source for edge in edges if edge.source in module_by_id}),
            confidence=round(sum(edge.confidence for edge in edges) / len(edges), 3),
            evidence_refs=_dedupe_evidence([ref for edge in edges for ref in edge.evidence_refs]),
        )
        source_feature.external_interactions.append(interaction)

    for feature in features:
        feature.dependencies = sorted(feature.dependencies, key=lambda item: item.target_feature_id)
        feature.external_interactions = sorted(feature.external_interactions, key=lambda item: item.target_id)


def _pick_explicit_feature_segment(parts: list[str]) -> str | None:
    normalized = [segment.strip().lower() for segment in parts[:-1]]
    candidate: str | None = None
    for segment in normalized:
        if not segment or segment in _SKIP_SEGMENTS:
            continue
        if segment.startswith("_") or segment.startswith("."):
            continue
        if segment.endswith("s") and len(segment) > 4 and segment[:-1] not in _SKIP_SEGMENTS:
            candidate = segment[:-1]
        else:
            candidate = segment
    return candidate


def _feature_key_from_basename(basename: str) -> str | None:
    if not basename:
        return None
    name = basename
    if "." in name:
        name = name.split(".")[0]
    for suffix in ["_service", "_controller", "_router", "_handler", "service", "controller", "router", "handler"]:
        if name.endswith(suffix) and len(name) > len(suffix) + 2:
            name = name[: -len(suffix)]
    name = name.strip("_-")
    if not name or name in {"index", "main", "app", "server", "init", "utils", "helper"}:
        return None
    return name.lower()


def _fallback_key(parts: list[str]) -> str:
    for segment in parts[:-1]:
        value = segment.strip().lower()
        if not value or value in _SKIP_SEGMENTS:
            continue
        return value
    return "core"


def _feature_id(feature_key: str) -> str:
    return f"feature:{sanitize_d2_identifier(feature_key.lower())}"


def _feature_name(feature_key: str) -> str:
    words = feature_key.replace("-", " ").replace("_", " ").split()
    if not words:
        return "Core"
    return " ".join(word.capitalize() for word in words)


def _path_evidence(path: str, rule_id: str) -> EvidenceRef:
    return EvidenceRef(file=path, line=1, rule_id=rule_id)


def _dedupe_evidence(items: list[EvidenceRef]) -> list[EvidenceRef]:
    seen: set[tuple[str, int, str, str | None]] = set()
    deduped: list[EvidenceRef] = []
    for item in items:
        key = (item.file, item.line, item.rule_id, item.snippet)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
