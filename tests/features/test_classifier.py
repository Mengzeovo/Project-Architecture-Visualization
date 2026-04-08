from __future__ import annotations

from archviz.features.classifier import build_features
from archviz.features.config import FeatureMap, FeatureRule
from archviz.models import Edge, EvidenceRef, GraphIR, Node


def test_classifier_prefers_feature_map_override() -> None:
    graph = _sample_graph()
    feature_map = FeatureMap(
        features={
            "auth": FeatureRule(include=["services/auth/**"]),
            "billing": FeatureRule(include=["services/billing/**"]),
        }
    )

    result = build_features(graph, feature_map=feature_map)

    mapping = result.module_to_feature
    assert mapping["module:services/auth/login.py"] == "feature:auth"
    assert mapping["module:services/billing/charge.py"] == "feature:billing"

    auth_feature = next(item for item in result.features if item.feature_id == "feature:auth")
    reasons = {module.path: module.reason for module in auth_feature.modules}
    assert reasons["services/auth/login.py"] == "feature-map.include"


def test_classifier_generates_cross_feature_dependency() -> None:
    graph = _sample_graph()
    feature_map = FeatureMap(
        features={
            "auth": FeatureRule(include=["services/auth/**"]),
            "billing": FeatureRule(include=["services/billing/**"]),
        }
    )

    result = build_features(graph, feature_map=feature_map)

    auth_feature = next(item for item in result.features if item.feature_id == "feature:auth")
    dependency_targets = [item.target_feature_id for item in auth_feature.dependencies]
    assert "feature:billing" in dependency_targets


def _sample_graph() -> GraphIR:
    nodes = [
        Node(
            id="module:services/auth/login.py",
            type="module",
            name="services/auth/login.py",
            path="services/auth/login.py",
            tags=["python"],
            confidence=1.0,
            evidence_refs=[EvidenceRef(file="services/auth/login.py", line=1, rule_id="node.python_file")],
            metadata={"container_id": "container:root"},
        ),
        Node(
            id="module:services/billing/charge.py",
            type="module",
            name="services/billing/charge.py",
            path="services/billing/charge.py",
            tags=["python"],
            confidence=1.0,
            evidence_refs=[EvidenceRef(file="services/billing/charge.py", line=1, rule_id="node.python_file")],
            metadata={"container_id": "container:root"},
        ),
    ]
    edges = [
        Edge(
            source="module:services/auth/login.py",
            target="module:services/billing/charge.py",
            type="imports",
            confidence=1.0,
            evidence_refs=[EvidenceRef(file="services/auth/login.py", line=2, rule_id="edge.imports.python")],
        )
    ]
    return GraphIR(nodes=nodes, edges=edges, metadata={"project_root": "/tmp/example"})
