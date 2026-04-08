from __future__ import annotations

from dataclasses import dataclass

from ..models import Edge, EvidenceRef, GraphIR, Node
from ..utils import sanitize_d2_identifier
from ..views import View
from .models import FeatureBuildResult


_MODULE_EDGE_TYPES = {
    "imports",
    "http",
    "reads",
    "writes",
    "publishes",
    "subscribes",
}


@dataclass(slots=True)
class FeatureViewItem:
    feature_id: str
    slug: str
    view: View


def build_feature_views(graph: GraphIR, feature_result: FeatureBuildResult) -> list[FeatureViewItem]:
    node_map = {node.id: node for node in graph.nodes}
    edge_list = list(graph.edges)
    views: list[FeatureViewItem] = []

    for feature in feature_result.features:
        root_node = Node(
            id=feature.feature_id,
            type="container",
            name=feature.name,
            confidence=feature.confidence,
            evidence_refs=feature.evidence_refs,
            metadata={"kind": "feature"},
        )
        nodes: dict[str, Node] = {root_node.id: root_node}
        edges: list[Edge] = []
        module_ids = {module.module_id for module in feature.modules}

        for module in feature.modules:
            module_node = node_map.get(module.module_id)
            if not module_node:
                continue
            nodes[module_node.id] = module_node
            edges.append(
                Edge(
                    source=feature.feature_id,
                    target=module_node.id,
                    type="contains",
                    confidence=module.confidence,
                    evidence_refs=module.evidence_refs,
                )
            )

        for edge in edge_list:
            if edge.type not in _MODULE_EDGE_TYPES:
                continue
            if edge.source in module_ids and edge.target in module_ids:
                edges.append(edge)

        for dependency in feature.dependencies:
            dependency_node = Node(
                id=dependency.target_feature_id,
                type="container",
                name=dependency.target_feature_name,
                confidence=dependency.confidence,
                evidence_refs=dependency.evidence_refs,
                metadata={"kind": "feature_dependency"},
            )
            nodes[dependency_node.id] = dependency_node
            edges.append(
                Edge(
                    source=feature.feature_id,
                    target=dependency.target_feature_id,
                    type="depends_on",
                    label="/".join(dependency.edge_types),
                    confidence=dependency.confidence,
                    evidence_refs=dependency.evidence_refs,
                )
            )

        for interaction in feature.external_interactions:
            graph_target = node_map.get(interaction.target_id)
            if graph_target:
                nodes[graph_target.id] = graph_target
            else:
                nodes[interaction.target_id] = Node(
                    id=interaction.target_id,
                    type=interaction.target_type,
                    name=interaction.target_name,
                    confidence=interaction.confidence,
                    evidence_refs=interaction.evidence_refs,
                )
            edges.append(
                Edge(
                    source=feature.feature_id,
                    target=interaction.target_id,
                    type=interaction.edge_types[0] if interaction.edge_types else "depends_on",
                    label="/".join(interaction.edge_types),
                    confidence=interaction.confidence,
                    evidence_refs=interaction.evidence_refs,
                )
            )

        views.append(
            FeatureViewItem(
                feature_id=feature.feature_id,
                slug=feature_slug(feature.feature_id),
                view=View(
                    name="diagram",
                    title=f"Feature {feature.name}",
                    nodes=sorted(nodes.values(), key=lambda item: (item.type, item.id)),
                    edges=_dedupe_edges(edges),
                ),
            )
        )
    return views


def feature_slug(feature_id: str) -> str:
    value = feature_id.split(":", 1)[-1].strip().lower()
    if not value:
        return "feature"
    return sanitize_d2_identifier(value)


def _dedupe_edges(edges: list[Edge]) -> list[Edge]:
    deduped: dict[tuple[str, str, str, str | None], Edge] = {}
    for edge in edges:
        key = (edge.source, edge.target, edge.type, edge.label)
        existing = deduped.get(key)
        if not existing:
            deduped[key] = edge
            continue
        merged_evidence = _dedupe_evidence([*existing.evidence_refs, *edge.evidence_refs])
        deduped[key] = Edge(
            source=edge.source,
            target=edge.target,
            type=edge.type,
            label=edge.label,
            confidence=max(existing.confidence, edge.confidence),
            evidence_refs=merged_evidence,
            metadata={**existing.metadata, **edge.metadata},
        )
    return sorted(deduped.values(), key=lambda item: (item.source, item.target, item.type, item.label or ""))


def _dedupe_evidence(items: list[EvidenceRef]) -> list[EvidenceRef]:
    seen: set[tuple[str, int, str, str | None]] = set()
    results: list[EvidenceRef] = []
    for item in items:
        key = (item.file, item.line, item.rule_id, item.snippet)
        if key in seen:
            continue
        seen.add(key)
        results.append(item)
    return results
