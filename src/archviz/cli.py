from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .io import write_graph_ir
from .pipeline import ArchitecturePipeline
from .renderers import render_view
from .report import write_report
from .views import build_container_view, build_module_view


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="archviz",
        description=(
            "Scan mixed-language projects and generate D2+SVG architecture diagrams. "
            "Deep extraction currently targets TS/JS and Python, with generic support for other ecosystems."
        ),
    )
    parser.add_argument("project", help="Path to project directory")
    parser.add_argument(
        "--output",
        default=".archviz",
        help="Output directory (default: .archviz)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    project_dir = Path(args.project).resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        parser.error(f"Project directory does not exist: {project_dir}")

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    views_dir = output_dir / "views"
    views_dir.mkdir(parents=True, exist_ok=True)

    pipeline = ArchitecturePipeline()
    result = pipeline.run(project_dir)

    write_graph_ir(result.graph, output_dir / "architecture.ir.json")

    container_view = build_container_view(result.graph)
    module_view = build_module_view(result.graph)

    container_render = render_view(container_view, views_dir)
    module_render = render_view(module_view, views_dir)

    write_report(result.graph, output_dir / "report.md")

    print("Architecture extraction complete")
    print(f"- Project: {project_dir}")
    print(f"- Output: {output_dir}")
    for key, value in result.scan_summary.items():
        print(f"- {key}: {value}")
    print(f"- D2: {container_render.d2_path}")
    print(f"- D2: {module_render.d2_path}")
    if container_render.svg_path:
        print(f"- SVG: {container_render.svg_path}")
    else:
        print("- SVG (container): skipped (d2 CLI missing or failed)")
    if module_render.svg_path:
        print(f"- SVG: {module_render.svg_path}")
    else:
        print("- SVG (module): skipped (d2 CLI missing or failed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
