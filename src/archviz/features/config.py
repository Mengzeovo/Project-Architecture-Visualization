from __future__ import annotations

from dataclasses import dataclass, field
import fnmatch
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FeatureRule:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FeatureMap:
    features: dict[str, FeatureRule] = field(default_factory=dict)
    shared: list[str] = field(default_factory=list)
    infra: list[str] = field(default_factory=list)
    source_path: Path | None = None

    def classify_path(self, path: str) -> tuple[str, float, str] | None:
        normalized_path = _normalize_path(path)

        for feature_key, rule in self.features.items():
            if not rule.include:
                continue
            if not any(_match_pattern(normalized_path, pattern) for pattern in rule.include):
                continue
            if any(_match_pattern(normalized_path, pattern) for pattern in rule.exclude):
                continue
            return feature_key, 0.99, "feature-map.include"

        if any(_match_pattern(normalized_path, pattern) for pattern in self.shared):
            return "shared", 0.98, "feature-map.shared"

        if any(_match_pattern(normalized_path, pattern) for pattern in self.infra):
            return "infra", 0.98, "feature-map.infra"

        return None


def load_feature_map(
    project_root: Path,
    output_dir: Path | None = None,
    explicit_path: Path | None = None,
) -> FeatureMap:
    config_path = _resolve_feature_map_path(project_root, output_dir=output_dir, explicit_path=explicit_path)
    if not config_path:
        return FeatureMap()

    data = _load_yaml_or_json(config_path)
    if not isinstance(data, dict):
        return FeatureMap(source_path=config_path)

    return _parse_feature_map(data, source_path=config_path)


def _resolve_feature_map_path(
    project_root: Path,
    output_dir: Path | None,
    explicit_path: Path | None,
) -> Path | None:
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(explicit_path)
    else:
        candidates.extend(
            [
                project_root / "feature-map.yaml",
                project_root / ".archviz" / "feature-map.yaml",
                project_root / "feature-map.yml",
                project_root / ".archviz" / "feature-map.yml",
            ]
        )
        if output_dir:
            candidates.extend(
                [
                    output_dir / "feature-map.yaml",
                    output_dir / "feature-map.yml",
                ]
            )

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def discover_feature_map_path(
    project_root: Path,
    output_dir: Path | None = None,
    explicit_path: Path | None = None,
) -> Path | None:
    return _resolve_feature_map_path(project_root, output_dir=output_dir, explicit_path=explicit_path)


def _load_yaml_or_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8").lstrip("\ufeff")
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    try:
        import yaml  # type: ignore
    except ImportError:
        return _parse_simple_yaml(text)

    try:
        loaded = yaml.safe_load(text)
    except Exception:
        return {}
    return loaded if loaded is not None else {}


def _parse_feature_map(raw: dict[str, Any], source_path: Path) -> FeatureMap:
    features_data = raw.get("features")
    features: dict[str, FeatureRule] = {}
    if isinstance(features_data, dict):
        for key, value in features_data.items():
            feature_key = str(key).strip().lower()
            if not feature_key or not isinstance(value, dict):
                continue
            include = _normalize_patterns(value.get("include"))
            exclude = _normalize_patterns(value.get("exclude"))
            features[feature_key] = FeatureRule(include=include, exclude=exclude)

    shared = _normalize_patterns(raw.get("shared"))
    infra = _normalize_patterns(raw.get("infra"))

    return FeatureMap(features=features, shared=shared, infra=infra, source_path=source_path)


def _normalize_patterns(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    patterns: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        pattern = _normalize_pattern(item)
        if pattern:
            patterns.append(pattern)
    return patterns


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").lstrip("./")


def _normalize_pattern(value: str) -> str:
    return _normalize_path(value.strip().strip('"').strip("'"))


def _match_pattern(path: str, pattern: str) -> bool:
    if not pattern:
        return False
    if fnmatch.fnmatch(path, pattern):
        return True
    if pattern.startswith("**/") and fnmatch.fnmatch(path, pattern[3:]):
        return True
    return False


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {"features": {}, "shared": [], "infra": []}
    section: str | None = None
    current_feature: str | None = None
    current_rule_list: str | None = None

    for raw_line in text.splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue

        indent = len(line_without_comment) - len(line_without_comment.lstrip(" "))
        token = line_without_comment.strip().lstrip("\ufeff")

        if indent == 0 and token.endswith(":"):
            section = token[:-1].strip().lower()
            current_feature = None
            current_rule_list = None
            continue

        if section == "features":
            if indent == 2 and token.endswith(":"):
                feature_name = token[:-1].strip().strip('"').strip("'").lower()
                if feature_name:
                    data["features"].setdefault(feature_name, {"include": [], "exclude": []})
                    current_feature = feature_name
                    current_rule_list = None
                continue

            if indent == 4 and token.endswith(":") and current_feature:
                list_name = token[:-1].strip().lower()
                if list_name in {"include", "exclude"}:
                    current_rule_list = list_name
                    data["features"][current_feature].setdefault(current_rule_list, [])
                continue

            if indent >= 6 and token.startswith("- ") and current_feature and current_rule_list:
                value = _normalize_pattern(token[2:].strip())
                if value:
                    data["features"][current_feature][current_rule_list].append(value)
                continue

        if section in {"shared", "infra"} and token.startswith("- "):
            value = _normalize_pattern(token[2:].strip())
            if value:
                data[section].append(value)

    return data
