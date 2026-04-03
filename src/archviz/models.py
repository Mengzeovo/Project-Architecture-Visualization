from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EvidenceRef:
    file: str
    line: int
    rule_id: str
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "rule_id": self.rule_id,
            "snippet": self.snippet,
        }


@dataclass(slots=True)
class Node:
    id: str
    type: str
    name: str
    path: str | None = None
    tags: list[str] = field(default_factory=list)
    confidence: float = 1.0
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "path": self.path,
            "tags": self.tags,
            "confidence": self.confidence,
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class Edge:
    source: str
    target: str
    type: str
    label: str | None = None
    confidence: float = 1.0
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "label": self.label,
            "confidence": self.confidence,
            "evidence_refs": [e.to_dict() for e in self.evidence_refs],
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class GraphIR:
    nodes: list[Node]
    edges: list[Edge]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": self.metadata,
        }


class GraphBuilder:
    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: dict[tuple[str, str, str, str | None], Edge] = {}

    def add_node(self, node: Node) -> None:
        existing = self._nodes.get(node.id)
        if not existing:
            self._nodes[node.id] = node
            return
        existing.confidence = max(existing.confidence, node.confidence)
        if node.path and not existing.path:
            existing.path = node.path
        existing.tags = sorted({*existing.tags, *node.tags})
        existing.evidence_refs.extend(node.evidence_refs)
        existing.metadata = {**existing.metadata, **node.metadata}

    def add_edge(self, edge: Edge) -> None:
        key = (edge.source, edge.target, edge.type, edge.label)
        existing = self._edges.get(key)
        if not existing:
            self._edges[key] = edge
            return
        existing.confidence = max(existing.confidence, edge.confidence)
        existing.evidence_refs.extend(edge.evidence_refs)
        existing.metadata = {**existing.metadata, **edge.metadata}

    def build(self, metadata: dict[str, Any] | None = None) -> GraphIR:
        nodes = sorted(self._nodes.values(), key=lambda item: item.id)
        edges = sorted(
            self._edges.values(), key=lambda item: (item.source, item.target, item.type)
        )
        return GraphIR(nodes=nodes, edges=edges, metadata=metadata or {})
