from __future__ import annotations

from pathlib import Path

from archviz.features.config import FeatureMap
from archviz.features.docs import write_feature_docs
from archviz.features.models import Feature, FeatureBuildResult, FeatureModule
from archviz.models import EvidenceRef


def test_write_feature_docs_creates_expected_files(tmp_path: Path) -> None:
    feature = Feature(
        feature_id="feature:auth",
        name="Auth",
        confidence=0.95,
        entrypoints=["services/auth/login.py"],
        modules=[
            FeatureModule(
                module_id="module:services/auth/login.py",
                path="services/auth/login.py",
                confidence=0.95,
                reason="feature-map.include",
                entrypoint=True,
                evidence_refs=[
                    EvidenceRef(
                        file="services/auth/login.py",
                        line=1,
                        rule_id="feature-map.include",
                    )
                ],
            )
        ],
        evidence_refs=[
            EvidenceRef(file="services/auth/login.py", line=1, rule_id="feature-map.include")
        ],
    )
    result = FeatureBuildResult(
        features=[feature],
        module_to_feature={"module:services/auth/login.py": "feature:auth"},
        unassigned_modules=[],
    )

    write_feature_docs(result, tmp_path)

    index_path = tmp_path / "feature-index.md"
    design_path = tmp_path / "features" / "auth" / "design.md"
    evidence_path = tmp_path / "features" / "auth" / "evidence.json"

    assert index_path.exists()
    assert design_path.exists()
    assert evidence_path.exists()

    index_text = index_path.read_text(encoding="utf-8")
    assert "Total features: 1" in index_text
    assert "[Auth](features/auth/design.md)" in index_text

    design_text = design_path.read_text(encoding="utf-8")
    assert "# Feature: Auth" in design_text
    assert "services/auth/login.py" in design_text
    assert "feature-map.include" in design_text


def test_feature_index_contains_feature_map_source(tmp_path: Path) -> None:
    feature = Feature(
        feature_id="feature:auth",
        name="Auth",
        confidence=0.95,
    )
    result = FeatureBuildResult(
        features=[feature],
        module_to_feature={},
        unassigned_modules=[],
    )
    feature_map = FeatureMap(source_path=tmp_path / "feature-map.yaml")

    write_feature_docs(result, tmp_path, feature_map=feature_map)

    index_text = (tmp_path / "feature-index.md").read_text(encoding="utf-8")
    assert "Feature map:" in index_text
    assert "feature-map.yaml" in index_text
