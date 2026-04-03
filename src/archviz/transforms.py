from __future__ import annotations

from collections import defaultdict

from .models import Edge, EvidenceRef, GraphIR, Node


def enrich_graph(graph: GraphIR) -> GraphIR:
    node_map = {node.id: node for node in graph.nodes}
    edges = list(graph.edges)
    existing_keys = {(edge.source, edge.target, edge.type, edge.label) for edge in edges}

    for edge in graph.edges:
        if edge.type != "imports":
            continue
        source_node = node_map.get(edge.source)
        target_node = node_map.get(edge.target)
        if not source_node or not target_node:
            continue
        if source_node.type != "module" or target_node.type != "module":
            continue
        source_container = _container_for(source_node)
        target_container = _container_for(target_node)
        if not source_container or not target_container or source_container == target_container:
            continue
        key = (source_container, target_container, "depends_on", "module import")
        if key in existing_keys:
            continue
        existing_keys.add(key)
        edges.append(
            Edge(
                source=source_container,
                target=target_container,
                type="depends_on",
                label="module import",
                confidence=0.9,
                evidence_refs=edge.evidence_refs,
            )
        )

    for edge in graph.edges:
        if edge.type not in {"http", "reads", "writes", "publishes", "subscribes"}:
            continue
        source_node = node_map.get(edge.source)
        target_node = node_map.get(edge.target)
        if not source_node or source_node.type != "module" or not target_node:
            continue
        source_container = _container_for(source_node)
        if not source_container:
            continue
        key = (source_container, target_node.id, edge.type, edge.label)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        edges.append(
            Edge(
                source=source_container,
                target=target_node.id,
                type=edge.type,
                label=edge.label,
                confidence=max(0.5, edge.confidence - 0.1),
                evidence_refs=edge.evidence_refs,
            )
        )

    frameworks = _framework_hints(graph.nodes, graph.edges)
    updated_nodes: list[Node] = []
    for node in graph.nodes:
        if node.type != "container":
            updated_nodes.append(node)
            continue
        node_frameworks = sorted(frameworks.get(node.id, set()))
        metadata = dict(node.metadata)
        if node_frameworks:
            metadata["frameworks"] = node_frameworks
        updated_nodes.append(
            Node(
                id=node.id,
                type=node.type,
                name=node.name,
                path=node.path,
                tags=node.tags,
                confidence=node.confidence,
                evidence_refs=node.evidence_refs,
                metadata=metadata,
            )
        )
    return GraphIR(nodes=updated_nodes, edges=edges, metadata=graph.metadata)


def _container_for(node: Node) -> str | None:
    container_id = node.metadata.get("container_id")
    if isinstance(container_id, str):
        return container_id
    return None


def _framework_hints(nodes: list[Node], edges: list[Edge]) -> dict[str, set[str]]:
    framework_by_package = {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "express": "Express",
        "@nestjs/core": "NestJS",
        "next": "Next.js",
    }
    package_names = {
        node.id: node.name for node in nodes if node.type == "package" and isinstance(node.name, str)
    }
    results: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge.type != "depends_on":
            continue
        if not edge.source.startswith("container:"):
            continue
        package_name = package_names.get(edge.target)
        if not package_name:
            continue
        framework = framework_by_package.get(package_name)
        if framework:
            results[edge.source].add(framework)
    return results


def summarize_graph(graph: GraphIR) -> dict[str, int]:
    language_coverage: set[str] = set()
    for node in graph.nodes:
        for tag in node.tags:
            language_coverage.add(tag)

    return {
        "containers": sum(1 for node in graph.nodes if node.type == "container"),
        "modules": sum(1 for node in graph.nodes if node.type == "module"),
        "packages": sum(1 for node in graph.nodes if node.type == "package"),
        "endpoints": sum(1 for node in graph.nodes if node.type == "api_endpoint"),
        "edges": len(graph.edges),
        "language_tags": len(language_coverage),
    }


def low_confidence_edges(graph: GraphIR, threshold: float = 0.8) -> list[Edge]:
    return [edge for edge in graph.edges if edge.confidence < threshold]


def container_dependency_edges(graph: GraphIR) -> list[Edge]:
    return [
        edge
        for edge in graph.edges
        if edge.source.startswith("container:")
        and (
            edge.target.startswith("container:")
            or edge.target.startswith("external_api:")
            or edge.target.startswith("database:")
            or edge.target.startswith("queue:")
            or edge.target.startswith("cache:")
            or edge.target.startswith("package:")
        )
    ]
