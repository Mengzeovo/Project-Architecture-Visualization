from __future__ import annotations

from pathlib import Path

from archviz.features.config import load_feature_map


def test_load_feature_map_from_project_root(tmp_path: Path) -> None:
    config_path = tmp_path / "feature-map.yaml"
    config_path.write_text(
        "\n".join(
            [
                "features:",
                "  auth:",
                "    include:",
                "      - \"services/auth/**\"",
                "  billing:",
                "    include:",
                "      - \"services/billing/**\"",
                "shared:",
                "  - \"utils/**\"",
                "infra:",
                "  - \"services/api/**\"",
                "",
            ]
        ),
        encoding="utf-8",
    )

    feature_map = load_feature_map(tmp_path)

    assert feature_map.source_path == config_path.resolve()
    assert "auth" in feature_map.features
    assert "billing" in feature_map.features
    assert feature_map.classify_path("services/auth/login.py") == (
        "auth",
        0.99,
        "feature-map.include",
    )
    assert feature_map.classify_path("utils/helpers.py") == (
        "shared",
        0.98,
        "feature-map.shared",
    )
    assert feature_map.classify_path("services/api/router.py") == (
        "infra",
        0.98,
        "feature-map.infra",
    )


def test_feature_map_exclude_rule(tmp_path: Path) -> None:
    config_path = tmp_path / "feature-map.yaml"
    config_path.write_text(
        "\n".join(
            [
                "features:",
                "  auth:",
                "    include:",
                "      - \"services/auth/**\"",
                "    exclude:",
                "      - \"**/*.test.py\"",
                "",
            ]
        ),
        encoding="utf-8",
    )

    feature_map = load_feature_map(tmp_path)

    assert feature_map.classify_path("services/auth/login.py") == (
        "auth",
        0.99,
        "feature-map.include",
    )
    assert feature_map.classify_path("services/auth/login.test.py") is None


def test_load_feature_map_handles_bom_prefix(tmp_path: Path) -> None:
    config_path = tmp_path / "feature-map.yaml"
    config_path.write_text("\ufefffeatures:\n  tests:\n    include:\n      - \"tests/**\"\n", encoding="utf-8")

    feature_map = load_feature_map(tmp_path)

    assert "tests" in feature_map.features
    assert feature_map.classify_path("tests/example.py") == (
        "tests",
        0.99,
        "feature-map.include",
    )
