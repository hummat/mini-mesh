#!/usr/bin/env python3
"""Convert nerfstudio/SDFStudio-style transforms.json to Instant-NGP/NeuS2 format.

This utility expects a transforms.json produced by sdf-process-data / nerfstudio-data
and writes a JSON that can be consumed by Instant-NGP-style loaders (including NeuS2).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _compute_focals(data: Dict[str, Any]) -> tuple[float, float]:
    w = float(data["w"])
    h = float(data["h"])

    fl_x = data.get("fl_x")
    fl_y = data.get("fl_y")
    cam_ax = data.get("camera_angle_x")
    cam_ay = data.get("camera_angle_y")

    if fl_x is None and cam_ax is not None:
        fl_x = 0.5 * w / math.tan(0.5 * float(cam_ax))
    if fl_y is None and cam_ay is not None:
        fl_y = 0.5 * h / math.tan(0.5 * float(cam_ay))

    if fl_x is None and fl_y is not None:
        fl_x = fl_y
    if fl_y is None and fl_x is not None:
        fl_y = fl_x

    if fl_x is None or fl_y is None:
        raise ValueError("Could not infer focal lengths from transforms.json")

    return float(fl_x), float(fl_y)


def _build_intrinsic(fl_x: float, fl_y: float, cx: float, cy: float) -> List[List[float]]:
    return [
        [fl_x, 0.0, cx, 0.0],
        [0.0, fl_y, cy, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def convert_transforms(input_path: Path, output_path: Path) -> None:
    """Convert SDFStudio/nerfstudio transforms.json to Instant-NGP/NeuS2 JSON."""
    data = _load_json(input_path)

    if "frames" not in data:
        raise ValueError(f"Input transforms file {input_path} has no 'frames' field")

    w = int(data["w"])
    h = int(data["h"])
    fl_x, fl_y = _compute_focals(data)

    cx = float(data.get("cx", w / 2.0))
    cy = float(data.get("cy", h / 2.0))

    intrinsic = _build_intrinsic(fl_x, fl_y, cx, cy)

    out: Dict[str, Any] = {
        "w": w,
        "h": h,
        "frames": [],
    }
    if "aabb_scale" in data:
        out["aabb_scale"] = float(data["aabb_scale"])
    if "scale" in data:
        out["scale"] = float(data["scale"])
    if "offset" in data:
        out["offset"] = list(data["offset"])

    for frame in data["frames"]:
        if "file_path" not in frame or "transform_matrix" not in frame:
            raise ValueError("Frame is missing 'file_path' or 'transform_matrix'")
        out_frame = {
            "file_path": frame["file_path"],
            "transform_matrix": frame["transform_matrix"],
            "intrinsic_matrix": intrinsic,
        }
        out["frames"].append(out_frame)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert nerfstudio/SDFStudio transforms.json to Instant-NGP/NeuS2 format."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Root data directory containing transforms.json.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional explicit path to input transforms.json "
        "(defaults to DATA_DIR/transforms.json).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output transforms file path (Instant-NGP/NeuS2 format).",
    )

    args = parser.parse_args()
    input_path = args.input or (args.data_dir / "transforms.json")

    if not input_path.is_file():
        raise SystemExit(f"[ERROR] Input transforms file not found: {input_path}")

    convert_transforms(input_path, args.output)


if __name__ == "__main__":
    main()

