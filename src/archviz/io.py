from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .features.models import FeatureBuildResult
from .models import GraphIR


def write_graph_ir(graph: GraphIR, output_path: Path) -> None:
    write_json(output_path, graph.to_dict())


def write_feature_ir(features: FeatureBuildResult, output_path: Path) -> None:
    write_json(output_path, features.to_dict())


def write_json(output_path: Path, payload: dict[str, Any] | list[Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
