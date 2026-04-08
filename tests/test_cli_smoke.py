from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_cli_smoke_generates_feature_outputs(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "archviz-output"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [sys.executable, "-m", "archviz.cli", str(project_root), "--output", str(output_dir)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "architecture.ir.json").exists()
    assert (output_dir / "feature.ir.json").exists()
    assert (output_dir / "feature-index.md").exists()
    assert (output_dir / "features").exists()


def test_cli_accepts_feature_map_arg(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "archviz-output"
    feature_map_path = tmp_path / "feature-map.yaml"
    feature_map_path.write_text(
        "\n".join(
            [
                "features:",
                "  tests:",
                "    include:",
                "      - \"tests/**\"",
                "",
            ]
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "archviz.cli",
            str(project_root),
            "--output",
            str(output_dir),
            "--feature-map",
            str(feature_map_path),
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    index_text = (output_dir / "feature-index.md").read_text(encoding="utf-8")
    assert "Feature map:" in index_text
