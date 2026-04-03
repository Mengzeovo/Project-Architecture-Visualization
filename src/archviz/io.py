from __future__ import annotations

import json
from pathlib import Path

from .models import GraphIR


def write_graph_ir(graph: GraphIR, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(graph.to_dict(), indent=2), encoding="utf-8")
