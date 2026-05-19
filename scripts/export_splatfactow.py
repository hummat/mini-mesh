#!/usr/bin/env python3
"""Export splatfacto-w-light Gaussian parameters to Nerfstudio-compatible PLY."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path
from typing import Literal

import numpy as np


def _console_print(message: str) -> None:
    try:
        from nerfstudio.utils.rich_utils import CONSOLE
    except ModuleNotFoundError:
        print(message)
    else:
        CONSOLE.print(message)


def _add_sh_coefficients(
    model: object,
    map_to_tensors: OrderedDict[str, np.ndarray],
    count: int,
    appearance_mode: Literal["mean", "index"],
    appearance_index: int | None,
) -> None:
    if (
        hasattr(model, "color_nn")
        and hasattr(model, "appearance_embeds")
        and hasattr(model, "appearance_features")
    ):
        appearance_features = model.appearance_features  # type: ignore[attr-defined]
        appearance_embed = _select_appearance_embedding(model, appearance_mode, appearance_index)
        sh_coeffs = model.color_nn(  # type: ignore[attr-defined]
            appearance_embed.repeat(appearance_features.shape[0], 1),
            appearance_features,
        ).float()
        shs_0_tensor = sh_coeffs[:, 0, :]
        shs_rest_tensor = sh_coeffs[:, 1:, :]
    else:
        if appearance_mode != "index" or appearance_index is not None:
            raise TypeError("Appearance bake selection requires a Splatfacto-W-style model")
        shs_0_tensor = model.shs_0  # type: ignore[attr-defined]
        shs_rest_tensor = model.shs_rest  # type: ignore[attr-defined]

    shs_0 = shs_0_tensor.detach().contiguous().cpu().numpy()
    for i in range(shs_0.shape[1]):
        map_to_tensors[f"f_dc_{i}"] = shs_0[:, i, None]

    if getattr(model.config, "sh_degree", 0) > 0:  # type: ignore[attr-defined]
        shs_rest = shs_rest_tensor.detach().transpose(1, 2).contiguous().cpu().numpy()
        shs_rest = shs_rest.reshape((count, -1))
        for i in range(shs_rest.shape[-1]):
            map_to_tensors[f"f_rest_{i}"] = shs_rest[:, i, None]


def _select_appearance_embedding(
    model: object, appearance_mode: Literal["mean", "index"], appearance_index: int | None
):
    import torch

    embeddings = model.appearance_embeds  # type: ignore[attr-defined]
    if appearance_mode == "mean":
        return embeddings.weight.mean(dim=0)

    if appearance_index is None:
        raise ValueError("--appearance-index is required when --appearance-mode index is used")
    if appearance_index < 0 or appearance_index >= embeddings.weight.shape[0]:
        raise ValueError(
            "--appearance-index must be in "
            f"[0, {embeddings.weight.shape[0] - 1}], got {appearance_index}"
        )
    return embeddings(torch.tensor(appearance_index, device=embeddings.weight.device))


def _add_rgb(
    model: object,
    map_to_tensors: OrderedDict[str, np.ndarray],
    appearance_mode: Literal["mean", "index"],
    appearance_index: int | None,
) -> None:
    import torch

    if (
        hasattr(model, "color_nn")
        and hasattr(model, "appearance_embeds")
        and hasattr(model, "appearance_features")
    ):
        appearance_features = model.appearance_features  # type: ignore[attr-defined]
        appearance_embed = _select_appearance_embedding(model, appearance_mode, appearance_index)
        shs_0 = model.color_nn(  # type: ignore[attr-defined]
            appearance_embed.repeat(appearance_features.shape[0], 1),
            appearance_features,
        ).float()[:, 0, :]
        colors_tensor = shs_0 * 0.28209479177387814 + 0.5
    elif hasattr(model, "colors"):
        colors_tensor = model.colors  # type: ignore[attr-defined]
    else:
        colors_tensor = model.base_colors  # type: ignore[attr-defined]
    colors = torch.clamp(colors_tensor.clone(), 0.0, 1.0).data.cpu().numpy()
    colors = (colors * 255).astype(np.uint8)
    map_to_tensors["red"] = colors[:, 0]
    map_to_tensors["green"] = colors[:, 1]
    map_to_tensors["blue"] = colors[:, 2]


def _finite_row_mask(tensor: np.ndarray, count: int) -> np.ndarray:
    if tensor.shape[0] != count:
        raise ValueError(f"Expected first dimension {count}, got {tensor.shape[0]}")
    if count == 0:
        return np.ones(0, dtype=bool)
    return np.isfinite(tensor.reshape(count, -1)).all(axis=1)


def _finite_and_opacity_filter(map_to_tensors: OrderedDict[str, np.ndarray], count: int) -> int:
    selected = np.ones(count, dtype=bool)
    for key, tensor in map_to_tensors.items():
        selected_before = int(np.sum(selected))
        selected = np.logical_and(selected, _finite_row_mask(np.asarray(tensor), count))
        selected_after = int(np.sum(selected))
        if selected_after < selected_before:
            _console_print(f"{selected_before - selected_after} NaN/Inf elements in {key}")

    finite_count = int(np.sum(selected))
    nan_count = count - finite_count
    opacity = np.asarray(map_to_tensors["opacity"])
    if opacity.shape[0] != count:
        raise ValueError(f"Expected opacity first dimension {count}, got {opacity.shape[0]}")
    opacity_values = opacity.reshape(count, -1)[:, 0] if count > 0 else np.asarray([], dtype=float)
    low_opacity = opacity_values < -5.5373
    low_opacity_count = int(np.sum(low_opacity & selected))
    selected[low_opacity] = 0

    if np.sum(selected) < count:
        _console_print(
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
    appearance_mode: Literal["mean", "index"],
    appearance_index: int | None,
    obb_center: tuple[float, float, float] | None,
    obb_rotation: tuple[float, float, float] | None,
    obb_scale: tuple[float, float, float] | None,
) -> None:
    import torch

    from nerfstudio.data.scene_box import OrientedBox
    from nerfstudio.scripts.exporter import ExportGaussianSplat
    from nerfstudio.utils.eval_utils import eval_setup

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
            _add_rgb(model, map_to_tensors, appearance_mode, appearance_index)
            if getattr(model.config, "sh_degree", 0) > 0:
                _console_print(
                    "Warning: model has SH colors; exporting RGB ignores higher-order SH."
                )
        else:
            _add_sh_coefficients(model, map_to_tensors, count, appearance_mode, appearance_index)

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
    parser.add_argument("--appearance-mode", choices=("mean", "index"), default="mean")
    parser.add_argument("--appearance-index", type=int)
    parser.add_argument("--appearance-idx", type=int)
    parser.add_argument("--obb-center", nargs=3, type=float)
    parser.add_argument("--obb-rotation", nargs=3, type=float)
    parser.add_argument("--obb-scale", nargs=3, type=float)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    appearance_index = (
        args.appearance_index if args.appearance_index is not None else args.appearance_idx
    )
    appearance_mode = (
        "index" if args.appearance_mode == "index" or appearance_index is not None else "mean"
    )
    export_splatfactow(
        load_config=args.load_config,
        output_dir=args.output_dir,
        output_filename=args.output_filename,
        ply_color_mode=args.ply_color_mode,
        appearance_mode=appearance_mode,
        appearance_index=appearance_index,
        obb_center=tuple(args.obb_center) if args.obb_center is not None else None,
        obb_rotation=tuple(args.obb_rotation) if args.obb_rotation is not None else None,
        obb_scale=tuple(args.obb_scale) if args.obb_scale is not None else None,
    )


if __name__ == "__main__":
    main()
