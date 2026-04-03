from __future__ import annotations

from dataclasses import dataclass

from .models import Edge, GraphIR, Node


@dataclass(slots=True)
class View:
    name: str
    title: str
    nodes: list[Node]
    edges: list[Edge]


def build_container_view(graph: GraphIR) -> View:
    allowed_types = {"container", "external_api", "database", "queue", "cache", "package"}
    nodes = [node for node in graph.nodes if node.type in allowed_types]
    node_ids = {node.id for node in nodes}
    edges = [
        edge
        for edge in graph.edges
        if edge.source in node_ids and edge.target in node_ids and edge.type != "contains"
    ]
    return View(
        name="container-view",
        title="Container Architecture",
        nodes=sorted(nodes, key=lambda item: (item.type, item.id)),
        edges=sorted(edges, key=lambda item: (item.source, item.target, item.type)),
    )


def build_module_view(graph: GraphIR) -> View:
    allowed_types = {"module", "external_api", "database", "queue", "cache", "api_endpoint"}
    nodes = [node for node in graph.nodes if node.type in allowed_types]
    node_ids = {node.id for node in nodes}
    allowed_edge_types = {
        "imports",
        "http",
        "reads",
        "writes",
        "publishes",
        "subscribes",
        "exposes",
    }
    edges = [
        edge
        for edge in graph.edges
        if edge.source in node_ids and edge.target in node_ids and edge.type in allowed_edge_types
    ]
    return View(
        name="module-view",
        title="Module Dependency View",
        nodes=sorted(nodes, key=lambda item: (item.type, item.id)),
        edges=sorted(edges, key=lambda item: (item.source, item.target, item.type)),
    )
