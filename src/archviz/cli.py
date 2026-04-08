from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .features import (
    build_feature_views,
    discover_feature_map_path,
    feature_slug,
    load_feature_map,
    write_feature_docs,
)
from .io import write_feature_ir, write_graph_ir
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
    parser.add_argument(
        "--feature-map",
        default=None,
        help="Optional feature map config path (yaml/json)",
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
    features_dir = output_dir / "features"
    features_dir.mkdir(parents=True, exist_ok=True)

    explicit_feature_map = Path(args.feature_map).resolve() if args.feature_map else None
    feature_map = load_feature_map(project_dir, output_dir=output_dir, explicit_path=explicit_feature_map)
    feature_map_path = discover_feature_map_path(
        project_dir,
        output_dir=output_dir,
        explicit_path=explicit_feature_map,
    )

    pipeline = ArchitecturePipeline()
    result = pipeline.run(project_dir, feature_map=feature_map)

    write_graph_ir(result.graph, output_dir / "architecture.ir.json")
    write_feature_ir(result.features, output_dir / "feature.ir.json")

    container_view = build_container_view(result.graph)
    module_view = build_module_view(result.graph)

    container_render = render_view(container_view, views_dir)
    module_render = render_view(module_view, views_dir)

    feature_views = build_feature_views(result.graph, result.features)
    feature_renders = [
        render_view(feature_view.view, features_dir / feature_slug(feature_view.feature_id))
        for feature_view in feature_views
    ]

    write_feature_docs(result.features, output_dir, feature_map=feature_map)

    write_report(result.graph, output_dir / "report.md", features=result.features)

    print("Architecture extraction complete")
    print(f"- Project: {project_dir}")
    print(f"- Output: {output_dir}")
    for key, value in result.scan_summary.items():
        print(f"- {key}: {value}")
    print(f"- D2: {container_render.d2_path}")
    print(f"- D2: {module_render.d2_path}")
    print(f"- Feature docs: {output_dir / 'feature-index.md'}")
    print(f"- Feature IR: {output_dir / 'feature.ir.json'}")
    print(f"- Feature diagrams: {len(feature_renders)}")
    if feature_map_path:
        print(f"- Feature map: {feature_map_path}")
    else:
        print("- Feature map: not used")
    if container_render.svg_path:
        print(f"- SVG: {container_render.svg_path}")
    else:
        print("- SVG (container): skipped (d2 CLI missing or failed)")
    if module_render.svg_path:
        print(f"- SVG: {module_render.svg_path}")
    else:
        print("- SVG (module): skipped (d2 CLI missing or failed)")
    feature_svg_count = sum(1 for render in feature_renders if render.svg_path)
    if feature_renders and feature_svg_count != len(feature_renders):
        print(f"- SVG (feature): {feature_svg_count}/{len(feature_renders)} rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
