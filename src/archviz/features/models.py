from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import EvidenceRef


@dataclass(slots=True)
class FeatureModule:
    module_id: str
    path: str
    confidence: float
    reason: str
    entrypoint: bool = False
    evidence_refs: list[EvidenceRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_id": self.module_id,
            "path": self.path,
            "confidence": self.confidence,
            "reason": self.reason,
            "entrypoint": self.entrypoint,
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
        }


@dataclass(slots=True)
class FeatureDependency:
    target_feature_id: str
    target_feature_name: str
    edge_types: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    confidence: float = 1.0
    evidence_refs: list[EvidenceRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_feature_id": self.target_feature_id,
            "target_feature_name": self.target_feature_name,
            "edge_types": self.edge_types,
            "sources": self.sources,
            "confidence": self.confidence,
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
        }


@dataclass(slots=True)
class FeatureExternalInteraction:
    target_id: str
    target_name: str
    target_type: str
    edge_types: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    confidence: float = 1.0
    evidence_refs: list[EvidenceRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "edge_types": self.edge_types,
            "sources": self.sources,
            "confidence": self.confidence,
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
        }


@dataclass(slots=True)
class Feature:
    feature_id: str
    name: str
    entrypoints: list[str] = field(default_factory=list)
    modules: list[FeatureModule] = field(default_factory=list)
    dependencies: list[FeatureDependency] = field(default_factory=list)
    external_interactions: list[FeatureExternalInteraction] = field(default_factory=list)
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "entrypoints": self.entrypoints,
            "modules": [item.to_dict() for item in self.modules],
            "dependencies": [item.to_dict() for item in self.dependencies],
            "external_interactions": [item.to_dict() for item in self.external_interactions],
            "evidence_refs": [item.to_dict() for item in self.evidence_refs],
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class FeatureBuildResult:
    features: list[Feature] = field(default_factory=list)
    module_to_feature: dict[str, str] = field(default_factory=dict)
    unassigned_modules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "features": [feature.to_dict() for feature in self.features],
            "module_to_feature": {
                key: value for key, value in sorted(self.module_to_feature.items(), key=lambda item: item[0])
            },
            "unassigned_modules": sorted(self.unassigned_modules),
        }
