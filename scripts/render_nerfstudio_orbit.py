#!/usr/bin/env python3
"""Render Nerfstudio spiral orbit frames with a portable data-path override.

Pass --image-format png when the frames will be compared against other renders
rather than looked at. JPEG artifacts largely cancel between two near-identical
images and decorrelate as the images separate, so the contamination grows with
the effect being measured instead of sitting under it as a constant floor. At
q95 the encoder's own error measured 0.00795 LPIPS and 48.5 dB, against renders
that differ from each other by 61 to 68 dB, which inflated a pruning ladder by
up to 19x. The q100 default here is not reliably safer: PSNR improves with the
quality setting but LPIPS does not, and on one of the two scenes measured q100
scores worse than q95. See docs/evaluation.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Literal


def _override_portable_paths(config: object, load_config: Path, data_path: Path) -> object:
    """Patch Docker-written paths before Nerfstudio constructs the datamanager."""
    config.data = data_path  # type: ignore[attr-defined]
    if load_config.parent.name == "run" and len(load_config.parents) >= 4:
        config.output_dir = load_config.parents[3]  # type: ignore[attr-defined]
    datamanager_config = config.pipeline.datamanager  # type: ignore[attr-defined]
    if hasattr(datamanager_config, "data"):
        datamanager_config.data = data_path
    if hasattr(datamanager_config, "dataparser") and hasattr(datamanager_config.dataparser, "data"):
        datamanager_config.dataparser.data = data_path
    return config


def _get_spiral_seed_camera(pipeline: object) -> object:
    """Return the first eval camera across Nerfstudio datamanager variants."""
    datamanager = pipeline.datamanager  # type: ignore[attr-defined]
    if hasattr(datamanager, "eval_dataloader"):
        camera, _ = datamanager.eval_dataloader.get_camera(image_idx=0)
        return camera

    if hasattr(datamanager, "eval_dataset") and hasattr(datamanager.eval_dataset, "cameras"):
        camera = datamanager.eval_dataset.cameras[0:1]
        if hasattr(camera, "to"):
            camera = camera.to(pipeline.device)  # type: ignore[attr-defined]
        return camera

    raise AttributeError("Datamanager has neither eval_dataloader nor eval_dataset.cameras")


def render_orbit_frames(
    load_config: Path,
    output_path: Path,
    data_path: Path,
    seconds: float,
    frame_rate: int,
    radius: float,
    image_format: Literal["jpeg", "png"],
    jpeg_quality: int,
    downscale_factor: float,
    eval_num_rays_per_chunk: int | None,
) -> None:
    from nerfstudio.cameras.camera_paths import get_spiral_path
    from nerfstudio.scripts.render import _render_trajectory_video
    from nerfstudio.utils import install_checks
    from nerfstudio.utils.eval_utils import eval_setup

    install_checks.check_ffmpeg_installed()

    _, pipeline, _, _ = eval_setup(
        load_config,
        eval_num_rays_per_chunk=eval_num_rays_per_chunk,
        test_mode="test",
        update_config_callback=lambda config: _override_portable_paths(
            config, load_config, data_path
        ),
    )

    steps = int(frame_rate * seconds)
    camera_start = _get_spiral_seed_camera(pipeline)
    camera_path = get_spiral_path(camera_start, steps=steps, radius=radius)

    _render_trajectory_video(
        pipeline,
        camera_path,
        output_filename=output_path,
        rendered_output_names=["rgb"],
        rendered_resolution_scaling_factor=1.0 / downscale_factor,
        seconds=seconds,
        output_format="images",
        image_format=image_format,
        jpeg_quality=jpeg_quality,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--load-config", required=True, type=Path)
    parser.add_argument("--output-path", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--frame-rate", type=int, default=1)
    parser.add_argument("--radius", type=float, default=0.1)
    parser.add_argument("--image-format", choices=["jpeg", "png"], default="jpeg")
    parser.add_argument("--jpeg-quality", type=int, default=100)
    parser.add_argument("--downscale-factor", type=float, default=1.0)
    parser.add_argument("--eval-num-rays-per-chunk", type=int, default=None)
    args = parser.parse_args()

    render_orbit_frames(
        load_config=args.load_config,
        output_path=args.output_path,
        data_path=args.data,
        seconds=args.seconds,
        frame_rate=args.frame_rate,
        radius=args.radius,
        image_format=args.image_format,
        jpeg_quality=args.jpeg_quality,
        downscale_factor=args.downscale_factor,
        eval_num_rays_per_chunk=args.eval_num_rays_per_chunk,
    )


if __name__ == "__main__":
    main()
