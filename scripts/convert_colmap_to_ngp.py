#!/usr/bin/env python3
"""Convert COLMAP text output to Instant-NGP/NeuS2 transforms.json.

This is a focused, read-only variant of instant-ngp's colmap2nerf.py:
it assumes that COLMAP has already been run and that cameras.txt /
images.txt exist, and writes a single transforms.json.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
from typing import Any, Dict

import numpy as np


def qvec2rotmat(qvec: np.ndarray) -> np.ndarray:
    return np.array(
        [
            [
                1 - 2 * qvec[2] ** 2 - 2 * qvec[3] ** 2,
                2 * qvec[1] * qvec[2] - 2 * qvec[0] * qvec[3],
                2 * qvec[3] * qvec[1] + 2 * qvec[0] * qvec[2],
            ],
            [
                2 * qvec[1] * qvec[2] + 2 * qvec[0] * qvec[3],
                1 - 2 * qvec[1] ** 2 - 2 * qvec[3] ** 2,
                2 * qvec[2] * qvec[3] - 2 * qvec[0] * qvec[1],
            ],
            [
                2 * qvec[3] * qvec[1] - 2 * qvec[0] * qvec[2],
                2 * qvec[2] * qvec[3] + 2 * qvec[0] * qvec[1],
                1 - 2 * qvec[1] ** 2 - 2 * qvec[2] ** 2,
            ],
        ]
    )


def rotmat(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if c < -1 + 1e-10:
        return rotmat(a + np.random.uniform(-1e-2, 1e-2, 3), b)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s**2 + 1e-10))


def closest_point_2_lines(oa: np.ndarray, da: np.ndarray, ob: np.ndarray, db: np.ndarray) -> tuple[np.ndarray, float]:
    da = da / np.linalg.norm(da)
    db = db / np.linalg.norm(db)
    c = np.cross(da, db)
    denom = np.linalg.norm(c) ** 2
    t = ob - oa
    ta = np.linalg.det([t, db, c]) / (denom + 1e-10)
    tb = np.linalg.det([t, da, c]) / (denom + 1e-10)
    if ta > 0:
        ta = 0
    if tb > 0:
        tb = 0
    return (oa + ta * da + ob + tb * db) * 0.5, denom


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert COLMAP text export to Instant-NGP/NeuS2 transforms.json."
    )
    parser.add_argument(
        "--images",
        type=Path,
        required=True,
        help="Image folder used by COLMAP.",
    )
    parser.add_argument(
        "--text",
        type=Path,
        required=True,
        help="Path to COLMAP text export (must contain cameras.txt and images.txt).",
    )
    parser.add_argument(
        "--aabb_scale",
        type=int,
        default=32,
        help="Large-scene scale (power of two, e.g. 1,2,4,...,128).",
    )
    parser.add_argument(
        "--skip_early",
        type=int,
        default=0,
        help="Skip this many early images (as in colmap2nerf).",
    )
    parser.add_argument(
        "--keep_colmap_coords",
        action="store_true",
        help="Keep COLMAP coordinate frame instead of reorienting/up-scaling.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output transforms.json path.",
    )
    return parser.parse_args()


def _read_cameras(cameras_txt: Path, aabb_scale: int) -> Dict[int, Dict[str, Any]]:
    cameras: Dict[int, Dict[str, Any]] = {}
    with cameras_txt.open("r", encoding="utf-8") as f:
        for line in f:
            if not line or line[0] == "#":
                continue
            els = line.strip().split()
            camera_id = int(els[0])
            model = els[1]
            w = float(els[2])
            h = float(els[3])
            cam: Dict[str, Any] = {
                "w": w,
                "h": h,
                "fl_x": float(els[4]),
                "fl_y": float(els[4]),
                "k1": 0.0,
                "k2": 0.0,
                "k3": 0.0,
                "k4": 0.0,
                "p1": 0.0,
                "p2": 0.0,
                "cx": w / 2.0,
                "cy": h / 2.0,
                "is_fisheye": False,
            }
            if model == "SIMPLE_PINHOLE":
                cam["cx"] = float(els[5])
                cam["cy"] = float(els[6])
            elif model == "PINHOLE":
                cam["fl_y"] = float(els[5])
                cam["cx"] = float(els[6])
                cam["cy"] = float(els[7])
            elif model == "SIMPLE_RADIAL":
                cam["cx"] = float(els[5])
                cam["cy"] = float(els[6])
                cam["k1"] = float(els[7])
            elif model == "RADIAL":
                cam["cx"] = float(els[5])
                cam["cy"] = float(els[6])
                cam["k1"] = float(els[7])
                cam["k2"] = float(els[8])
            elif model == "OPENCV":
                cam["fl_y"] = float(els[5])
                cam["cx"] = float(els[6])
                cam["cy"] = float(els[7])
                cam["k1"] = float(els[8])
                cam["k2"] = float(els[9])
                cam["p1"] = float(els[10])
                cam["p2"] = float(els[11])
            elif model == "SIMPLE_RADIAL_FISHEYE":
                cam["is_fisheye"] = True
                cam["cx"] = float(els[5])
                cam["cy"] = float(els[6])
                cam["k1"] = float(els[7])
            elif model == "RADIAL_FISHEYE":
                cam["is_fisheye"] = True
                cam["cx"] = float(els[5])
                cam["cy"] = float(els[6])
                cam["k1"] = float(els[7])
                cam["k2"] = float(els[8])
            elif model == "OPENCV_FISHEYE":
                cam["is_fisheye"] = True
                cam["fl_y"] = float(els[5])
                cam["cx"] = float(els[6])
                cam["cy"] = float(els[7])
                cam["k1"] = float(els[8])
                cam["k2"] = float(els[9])
                cam["k3"] = float(els[10])
                cam["k4"] = float(els[11])

            cam["camera_angle_x"] = math.atan(cam["w"] / (cam["fl_x"] * 2.0)) * 2.0
            cam["camera_angle_y"] = math.atan(cam["h"] / (cam["fl_y"] * 2.0)) * 2.0
            cam["fovx"] = cam["camera_angle_x"] * 180.0 / math.pi
            cam["fovy"] = cam["camera_angle_y"] * 180.0 / math.pi
            cam["aabb_scale"] = aabb_scale
            cameras[camera_id] = cam
    return cameras


def main() -> None:
    args = parse_args()

    cameras_txt = args.text / "cameras.txt"
    images_txt = args.text / "images.txt"
    if not cameras_txt.is_file() or not images_txt.is_file():
        raise SystemExit(f"[ERROR] Expected cameras.txt and images.txt under {args.text}")

    cameras = _read_cameras(cameras_txt, args.aabb_scale)
    if not cameras:
        raise SystemExit("[ERROR] No cameras found in cameras.txt")

    IMAGE_FOLDER = args.images
    AABB_SCALE = int(args.aabb_scale)
    SKIP_EARLY = int(args.skip_early)

    bottom = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32).reshape((1, 4))

    if len(cameras) == 1:
        # Use the single camera as global intrinsics.
        camera_id = next(iter(cameras.keys()))
        cam = cameras[camera_id]
        out: Dict[str, Any] = {
            "camera_angle_x": cam["camera_angle_x"],
            "camera_angle_y": cam["camera_angle_y"],
            "fl_x": cam["fl_x"],
            "fl_y": cam["fl_y"],
            "k1": cam["k1"],
            "k2": cam["k2"],
            "k3": cam["k3"],
            "k4": cam["k4"],
            "p1": cam["p1"],
            "p2": cam["p2"],
            "is_fisheye": cam["is_fisheye"],
            "cx": cam["cx"],
            "cy": cam["cy"],
            "w": cam["w"],
            "h": cam["h"],
            "aabb_scale": AABB_SCALE,
            "frames": [],
        }
    else:
        out = {
            "frames": [],
            "aabb_scale": AABB_SCALE,
        }

    up = np.zeros(3, dtype=np.float64)
    with images_txt.open("r", encoding="utf-8") as f:
        i = 0
        for line in f:
            line = line.strip()
            if not line or line[0] == "#":
                continue
            i += 1
            if i < SKIP_EARLY * 2:
                continue
            if i % 2 == 1:
                elems = line.split()
                image_id = int(elems[0])
                qvec = np.array(tuple(map(float, elems[1:5])))
                tvec = np.array(tuple(map(float, elems[5:8])))
                R = qvec2rotmat(-qvec)
                t = tvec.reshape((3, 1))
                m = np.concatenate([np.concatenate([R, t], axis=1), bottom], axis=0)
                c2w = np.linalg.inv(m)

                if not args.keep_colmap_coords:
                    # Match instant-ngp convention.
                    c2w[0:3, 2] *= -1.0
                    c2w[0:3, 1] *= -1.0
                    c2w = c2w[[1, 0, 2, 3], :]
                    c2w[2, :] *= -1.0
                    up += c2w[0:3, 1]

                image_rel = os.path.relpath(IMAGE_FOLDER)
                filename = "_".join(elems[9:])
                name = str(PurePosixPath(Path(f"./{image_rel}") / filename))

                frame: Dict[str, Any] = {
                    "file_path": name,
                    "sharpness": 0.0,
                    "transform_matrix": c2w,
                }
                if len(cameras) != 1:
                    cam_id = int(elems[8])
                    frame.update(cameras[cam_id])
                out["frames"].append(frame)

    nframes = len(out["frames"])
    if args.keep_colmap_coords:
        flip_mat = np.array(
            [
                [1, 0, 0, 0],
                [0, -1, 0, 0],
                [0, 0, -1, 0],
                [0, 0, 0, 1],
            ]
        )
        for f in out["frames"]:
            f["transform_matrix"] = (f["transform_matrix"] @ flip_mat).tolist()
    else:
        up /= np.linalg.norm(up) + 1e-10
        R_up = rotmat(up, np.array([0, 0, 1], dtype=np.float64))
        R_up = np.pad(R_up, [[0, 1], [0, 1]])
        R_up[-1, -1] = 1.0

        for f in out["frames"]:
            f["transform_matrix"] = (R_up @ f["transform_matrix"])

        print("computing center of attention...")
        totw = 0.0
        totp = np.zeros(3, dtype=np.float64)
        for f_a in out["frames"]:
            mf = f_a["transform_matrix"][0:3, :]
            for f_b in out["frames"]:
                mg = f_b["transform_matrix"][0:3, :]
                p, w = closest_point_2_lines(mf[:, 3], mf[:, 2], mg[:, 3], mg[:, 2])
                if w > 0.00001:
                    totp += p * w
                    totw += w
        if totw > 0.0:
            totp /= totw

        for f in out["frames"]:
            f["transform_matrix"][0:3, 3] -= totp

        avglen = 0.0
        for f in out["frames"]:
            avglen += np.linalg.norm(f["transform_matrix"][0:3, 3])
        avglen /= max(nframes, 1)
        if avglen > 0:
            scale = 4.0 / avglen
        else:
            scale = 1.0
        for f in out["frames"]:
            f["transform_matrix"][0:3, 3] *= scale

        for f in out["frames"]:
            f["transform_matrix"] = f["transform_matrix"].tolist()

    print(f"{nframes} frames")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as outfile:
        json.dump(out, outfile, indent=2)


if __name__ == "__main__":
    main()

