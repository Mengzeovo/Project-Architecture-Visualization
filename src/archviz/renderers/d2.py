from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from ..models import Node
from ..utils import sanitize_d2_identifier
from ..views import View


TYPE_SHAPES = {
    "container": "rectangle",
    "module": "rectangle",
    "database": "cylinder",
    "queue": "queue",
    "cache": "stored_data",
    "external_api": "cloud",
    "api_endpoint": "hexagon",
    "package": "page",
}


@dataclass(slots=True)
class D2RenderResult:
    d2_path: Path
    svg_path: Path | None


def render_view_to_d2(view: View) -> str:
    node_alias: dict[str, str] = {}
    lines = ["direction: right", ""]

    for index, node in enumerate(view.nodes, start=1):
        alias = _alias_for_node(node, index)
        node_alias[node.id] = alias
        label = node.name.replace('"', "'")
        shape = TYPE_SHAPES.get(node.type, "rectangle")
        lines.append(f"{alias}: \"{label}\"")
        lines.append(f"{alias}.shape: {shape}")
        if node.type == "container":
            lines.append(f"{alias}.style.stroke-width: 2")
        lines.append("")

    for edge in view.edges:
        source = node_alias.get(edge.source)
        target = node_alias.get(edge.target)
        if not source or not target:
            continue
        label = edge.label or edge.type
        label = label.replace('"', "'")
        lines.append(f"{source} -> {target}: \"{label}\"")

    return "\n".join(lines).strip() + "\n"


def write_d2_file(view: View, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    d2_content = render_view_to_d2(view)
    d2_path = output_dir / f"{view.name}.d2"
    d2_path.write_text(d2_content, encoding="utf-8")
    return d2_path


def render_svg_if_available(d2_path: Path) -> Path | None:
    svg_path = d2_path.with_suffix(".svg")
    command = ["d2", str(d2_path), str(svg_path)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return svg_path if svg_path.exists() else None


def render_view(view: View, output_dir: Path) -> D2RenderResult:
    d2_path = write_d2_file(view, output_dir)
    svg_path = render_svg_if_available(d2_path)
    return D2RenderResult(d2_path=d2_path, svg_path=svg_path)


def _alias_for_node(node: Node, index: int) -> str:
    seed = f"{node.type}_{node.name}_{index}"
    return sanitize_d2_identifier(seed)
