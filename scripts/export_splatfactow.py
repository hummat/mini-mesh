#!/usr/bin/env python3
"""Export splatfacto-w-light Gaussian parameters to Nerfstudio-compatible PLY."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path
from typing import Literal

import numpy as np
import torch
from nerfstudio.data.scene_box import OrientedBox
from nerfstudio.scripts.exporter import ExportGaussianSplat
from nerfstudio.utils.eval_utils import eval_setup
from nerfstudio.utils.rich_utils import CONSOLE


def _add_sh_coefficients(
    model: object, map_to_tensors: OrderedDict[str, np.ndarray], count: int
) -> None:
    shs_0 = model.shs_0.contiguous().cpu().numpy()  # type: ignore[attr-defined]
    for i in range(shs_0.shape[1]):
        map_to_tensors[f"f_dc_{i}"] = shs_0[:, i, None]

    if getattr(model.config, "sh_degree", 0) > 0:  # type: ignore[attr-defined]
        shs_rest = model.shs_rest.transpose(1, 2).contiguous().cpu().numpy()  # type: ignore[attr-defined]
        shs_rest = shs_rest.reshape((count, -1))
        for i in range(shs_rest.shape[-1]):
            map_to_tensors[f"f_rest_{i}"] = shs_rest[:, i, None]


def _add_rgb(model: object, map_to_tensors: OrderedDict[str, np.ndarray]) -> None:
    if hasattr(model, "colors"):
        colors_tensor = model.colors  # type: ignore[attr-defined]
    else:
        colors_tensor = model.base_colors  # type: ignore[attr-defined]
    colors = torch.clamp(colors_tensor.clone(), 0.0, 1.0).data.cpu().numpy()
    colors = (colors * 255).astype(np.uint8)
    map_to_tensors["red"] = colors[:, 0]
    map_to_tensors["green"] = colors[:, 1]
    map_to_tensors["blue"] = colors[:, 2]


def _finite_and_opacity_filter(map_to_tensors: OrderedDict[str, np.ndarray], count: int) -> int:
    selected = np.ones(count, dtype=bool)
    for key, tensor in map_to_tensors.items():
        selected_before = np.sum(selected)
        selected = np.logical_and(selected, np.isfinite(tensor).all(axis=-1))
        selected_after = np.sum(selected)
        if selected_after < selected_before:
            CONSOLE.print(f"{selected_before - selected_after} NaN/Inf elements in {key}")

    nan_count = np.sum(selected) - count
    low_opacity = map_to_tensors["opacity"].squeeze(axis=-1) < -5.5373
    low_opacity_count = np.sum(low_opacity)
    selected[low_opacity] = 0

    if np.sum(selected) < count:
        CONSOLE.print(
            f"{nan_count} Gaussians have NaN/Inf and {low_opacity_count} have low opacity, "
            f"only export {np.sum(selected)}/{count}"
        )
        for key, tensor in map_to_tensors.items():
            map_to_tensors[key] = tensor[selected]
        return int(np.sum(selected))

    return count


def export_splatfactow(
    load_config: Path,
    output_dir: Path,
    output_filename: str,
    ply_color_mode: Literal["sh_coeffs", "rgb"],
    obb_center: tuple[float, float, float] | None,
    obb_rotation: tuple[float, float, float] | None,
    obb_scale: tuple[float, float, float] | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _, pipeline, _, _ = eval_setup(load_config, test_mode="inference")
    model = pipeline.model

    required_attrs = ("means", "scales", "quats", "opacities")
    missing = [attr for attr in required_attrs if not hasattr(model, attr)]
    if missing:
        raise TypeError(
            f"Model {type(model).__name__} is not Gaussian-export compatible; missing {missing}"
        )

    map_to_tensors: OrderedDict[str, np.ndarray] = OrderedDict()
    with torch.no_grad():
        positions = model.means.cpu().numpy()
        count = positions.shape[0]
        map_to_tensors["x"] = positions[:, 0]
        map_to_tensors["y"] = positions[:, 1]
        map_to_tensors["z"] = positions[:, 2]
        map_to_tensors["nx"] = np.zeros(count, dtype=np.float32)
        map_to_tensors["ny"] = np.zeros(count, dtype=np.float32)
        map_to_tensors["nz"] = np.zeros(count, dtype=np.float32)

        if ply_color_mode == "rgb":
            _add_rgb(model, map_to_tensors)
            if getattr(model.config, "sh_degree", 0) > 0:
                CONSOLE.print(
                    "Warning: model has SH colors; exporting RGB ignores higher-order SH."
                )
        else:
            _add_sh_coefficients(model, map_to_tensors, count)

        map_to_tensors["opacity"] = model.opacities.data.cpu().numpy()

        scales = model.scales.data.cpu().numpy()
        for i in range(3):
            map_to_tensors[f"scale_{i}"] = scales[:, i, None]

        quats = model.quats.data.cpu().numpy()
        for i in range(4):
            map_to_tensors[f"rot_{i}"] = quats[:, i, None]

        if obb_center is not None and obb_rotation is not None and obb_scale is not None:
            crop_obb = OrientedBox.from_params(obb_center, obb_rotation, obb_scale)
            assert crop_obb is not None
            mask = crop_obb.within(torch.from_numpy(positions)).numpy()
            for key, tensor in map_to_tensors.items():
                map_to_tensors[key] = tensor[mask]
            count = int(map_to_tensors["x"].shape[0])

    count = _finite_and_opacity_filter(map_to_tensors, count)
    ExportGaussianSplat.write_ply(str(output_dir / output_filename), count, map_to_tensors)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-filename", default="splat.ply")
    parser.add_argument("--ply-color-mode", choices=("sh_coeffs", "rgb"), default="sh_coeffs")
    parser.add_argument("--obb-center", nargs=3, type=float)
    parser.add_argument("--obb-rotation", nargs=3, type=float)
    parser.add_argument("--obb-scale", nargs=3, type=float)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    export_splatfactow(
        load_config=args.load_config,
        output_dir=args.output_dir,
        output_filename=args.output_filename,
        ply_color_mode=args.ply_color_mode,
        obb_center=tuple(args.obb_center) if args.obb_center is not None else None,
        obb_rotation=tuple(args.obb_rotation) if args.obb_rotation is not None else None,
        obb_scale=tuple(args.obb_scale) if args.obb_scale is not None else None,
    )


if __name__ == "__main__":
    main()
