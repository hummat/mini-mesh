#!/usr/bin/env python3
"""Filter a 3D Gaussian Splatting PLY down to what is worth shipping.

A trained splat carries a large tail of Gaussians that contribute almost nothing
to a rendered view: near-transparent blobs, a few enormous ones covering half the
scene, and needle-shaped slivers. They cost file size and viewer performance
without earning it back in quality.

Only the opacity stage is on by default, because it is the only one whose cost has
been measured. Matched pairs tested frame by frame put the LPIPS change at 0.05 at
+0.0007 on a cluttered outdoor capture and +0.0059 on a sharp object capture, with
the sign holding on every frame of both; at 0.10 it is +0.0042 and +0.0373. Those
are changes in an objective metric, not measured perceptual costs.

0.05 is provisional, not validated. What the measurements establish is the shape
of the tradeoff rather than the right point on it: moving from 0.05 to 0.10
removes a further 18 to 30 percentage points of Gaussians and multiplies the
deviation from the unpruned render by six to seven (0.0032 and 0.0078 LPIPS at
0.05, 0.020 and 0.054 at 0.10). Choosing a point needs a viewer study or an
objective acceptance bound set in advance, and there is neither. An earlier
version of this note called 0.10 free on the outdoor capture, which compared it
to the per-image spread instead of to its own paired noise; see
docs/evaluation.md and hummat/mini-mesh#34.

The scale, anisotropy and outlier stages are implemented but off until they have
been measured the same way; see hummat/mini-mesh#30.

The crop stage is likewise off by default, and for the same reason: it has not
been measured. It exists for object-centric captures, where a shell of
background and reconstruction noise is as opaque and as compact as the subject,
so no per-Gaussian statistic separates the two and a spatial crop is the only
stage that removes the shell. The stage masks are each computed on the
unfiltered population and combined with AND, so the quantile stages always
describe the whole capture; only the crop's cut has a spatial meaning.

The output is always binary_little_endian, whatever the input was.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# PLY scalar names and their numpy equivalents, both the short and long spellings.
PLY_DTYPES = {
    "char": "i1",
    "int8": "i1",
    "uchar": "u1",
    "uint8": "u1",
    "short": "i2",
    "int16": "i2",
    "ushort": "u2",
    "uint16": "u2",
    "int": "i4",
    "int32": "i4",
    "uint": "u4",
    "uint32": "u4",
    "float": "f4",
    "float32": "f4",
    "double": "f8",
    "float64": "f8",
}

# Every width the reader accepts needs a way back out. Falling back to "float"
# for an unmapped dtype writes a header that misdescribes the payload, and the
# file is then silently misaligned rather than rejected.
PLY_NAMES = {
    "i1": "char",
    "u1": "uchar",
    "i2": "short",
    "u2": "ushort",
    "i4": "int",
    "u4": "uint",
    "f4": "float",
    "f8": "double",
}

SCALE_FIELDS = ("scale_0", "scale_1", "scale_2")


class PlyError(RuntimeError):
    """The file is not a Gaussian splat PLY this script can work with."""


def read_ply(path: Path) -> tuple[np.ndarray, list[str]]:
    """Return the vertex data as a structured array plus the property names."""
    with path.open("rb") as handle:
        if handle.readline().strip() != b"ply":
            raise PlyError(f"{path} does not start with a ply magic line")

        fmt = ""
        count = -1
        fields: list[tuple[str, str]] = []
        in_vertex_element = False
        while True:
            raw = handle.readline()
            if not raw:
                raise PlyError(f"{path} ended before end_header")
            parts = raw.decode("ascii", errors="replace").split()
            if not parts:
                continue
            if parts[0] == "format":
                fmt = parts[1]
            elif parts[0] == "element":
                # Only the vertex element carries Gaussians; anything else would
                # need its own offsets, so refuse rather than silently mangle it.
                in_vertex_element = parts[1] == "vertex"
                if in_vertex_element:
                    count = int(parts[2])
                elif count >= 0:
                    raise PlyError(f"{path} has elements after vertex, which is not supported")
            elif parts[0] == "property" and in_vertex_element:
                if parts[1] == "list":
                    raise PlyError(f"{path} has a list property on vertex, which is not supported")
                if parts[1] not in PLY_DTYPES:
                    raise PlyError(f"{path} has unknown property type {parts[1]!r}")
                fields.append((parts[2], PLY_DTYPES[parts[1]]))
            elif parts[0] == "end_header":
                break

        if count < 0 or not fields:
            raise PlyError(f"{path} has no vertex element")

        names = [name for name, _ in fields]
        if fmt == "binary_little_endian":
            dtype = np.dtype([(name, "<" + kind) for name, kind in fields])
            data = np.frombuffer(handle.read(dtype.itemsize * count), dtype=dtype, count=count)
        elif fmt == "binary_big_endian":
            dtype = np.dtype([(name, ">" + kind) for name, kind in fields])
            data = np.frombuffer(handle.read(dtype.itemsize * count), dtype=dtype, count=count)
        elif fmt == "ascii":
            dtype = np.dtype([(name, "<" + kind) for name, kind in fields])
            flat = np.loadtxt(handle, max_rows=count, ndmin=2)
            data = np.empty(count, dtype=dtype)
            for i, name in enumerate(names):
                data[name] = flat[:, i]
        else:
            raise PlyError(f"{path} has unsupported format {fmt!r}")

    if len(data) != count:
        raise PlyError(f"{path} declares {count} vertices but holds {len(data)}")
    return data, names


def write_ply(path: Path, data: np.ndarray, names: list[str]) -> None:
    """Write a binary little-endian PLY with one vertex element."""
    out = np.empty(
        len(data), dtype=np.dtype([(name, "<" + data.dtype[name].str[1:]) for name in names])
    )
    for name in names:
        out[name] = data[name]

    header = ["ply", "format binary_little_endian 1.0", f"element vertex {len(out)}"]
    for name in names:
        kind = out.dtype[name].str[1:]
        if kind not in PLY_NAMES:
            raise PlyError(f"cannot write property {name!r} of type {kind!r}")
        header.append(f"property {PLY_NAMES[kind]} {name}")
    header.append("end_header")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(("\n".join(header) + "\n").encode("ascii"))
        handle.write(out.tobytes())


def require(names: list[str], needed: tuple[str, ...], stage: str) -> None:
    missing = [name for name in needed if name not in names]
    if missing:
        raise PlyError(f"{stage} needs properties absent from this PLY: {', '.join(missing)}")


def opacity_keep(data: np.ndarray, names: list[str], threshold: float) -> np.ndarray:
    """Keep Gaussians whose opacity is at least the threshold.

    The stored value is a logit, which is what nerfstudio's own export threshold
    (`opacity < logit(1/255)`) compares against, so it is converted rather than
    compared raw.
    """
    require(names, ("opacity",), "opacity filter")
    return 1.0 / (1.0 + np.exp(-data["opacity"].astype(np.float64))) >= threshold


def extents(data: np.ndarray) -> np.ndarray:
    """Per-Gaussian scales in world units; the PLY stores their logarithms."""
    return np.exp(np.stack([data[name].astype(np.float64) for name in SCALE_FIELDS], axis=1))


def scale_keep(data: np.ndarray, names: list[str], quantile: float) -> np.ndarray:
    """Drop the largest Gaussians by longest axis, cut at a quantile of the population.

    An absolute threshold cannot be shared between scenes because scene scale is
    arbitrary, so the cut is relative to this splat's own distribution.
    """
    require(names, SCALE_FIELDS, "scale filter")
    longest = extents(data).max(axis=1)
    return longest <= np.quantile(longest, quantile)


CENTRE_FIELDS = ("x", "y", "z")


def centres(data: np.ndarray) -> np.ndarray:
    """Per-Gaussian centres as an (N, 3) float64 array."""
    return np.stack([data[name].astype(np.float64) for name in CENTRE_FIELDS], axis=1)


def crop_keep(
    data: np.ndarray,
    names: list[str],
    quantile: float | None,
    radius: float | None,
    centre: tuple[float, ...] | None,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Keep Gaussians within a sphere around the subject.

    Object-centric captures carry a shell of background and reconstruction noise that no per-Gaussian
    statistic separates from the subject: the noise is often as opaque and as compact as the object. Cropping
    is the only stage that removes it. Stage masks compose by AND on the unfiltered population, so the
    later quantile stages still describe the whole capture rather than the post-crop subject.

    The centre defaults to the per-axis median of the visible Gaussians, which an off-centre shell cannot drag
    the way a mean can. The radius defaults to a quantile of the visible population's distance from it.
    """
    require(names, CENTRE_FIELDS, "crop")
    points = centres(data)
    if "opacity" in names:
        visible = 1.0 / (1.0 + np.exp(-data["opacity"].astype(np.float64))) >= 0.1
    else:
        visible = np.ones(len(data), dtype=bool)
    if visible.sum() < max(1, int(0.01 * len(data))):
        visible = np.ones(len(data), dtype=bool)
    origin = (
        np.asarray(centre, dtype=np.float64)
        if centre is not None
        else np.median(points[visible], axis=0)
    )
    distances = np.linalg.norm(points - origin, axis=1)
    cut = float(radius) if radius is not None else float(np.quantile(distances[visible], quantile))
    return distances <= cut, origin, cut


def anisotropy_keep(data: np.ndarray, names: list[str], ratio: float) -> np.ndarray:
    """Drop needles: Gaussians whose longest axis exceeds the shortest by `ratio`."""
    require(names, SCALE_FIELDS, "anisotropy filter")
    axes = extents(data)
    shortest = np.maximum(axes.min(axis=1), np.finfo(np.float64).tiny)
    return axes.max(axis=1) / shortest <= ratio


def outlier_keep(
    data: np.ndarray, names: list[str], neighbours: int, std_ratio: float
) -> np.ndarray:
    """Statistical outlier removal over Gaussian centres.

    Drops points whose mean distance to their k nearest neighbours is more than
    `std_ratio` standard deviations above the population mean, which is the usual
    way to strip the sparse halo of floaters around a reconstruction.
    """
    require(names, ("x", "y", "z"), "outlier filter")
    try:
        from scipy.spatial import cKDTree
    except ModuleNotFoundError as exc:  # optional: the other stages need no scipy
        raise PlyError("--sor needs scipy; install it or drop the flag") from exc

    points = np.stack([data[axis].astype(np.float64) for axis in ("x", "y", "z")], axis=1)
    # The first neighbour of a point is itself, so ask for one extra and drop it.
    distances, _ = cKDTree(points).query(points, k=neighbours + 1, workers=-1)
    mean_distance = distances[:, 1:].mean(axis=1)
    return mean_distance <= mean_distance.mean() + std_ratio * mean_distance.std()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("input", type=Path, help="Gaussian splat PLY to filter")
    parser.add_argument(
        "-o", "--output", type=Path, default=None, help="output PLY (default: overwrite input)"
    )
    parser.add_argument(
        "--crop-quantile",
        type=float,
        default=None,
        help="keep Gaussians within this distance quantile of the subject centre, e.g. 0.85 (default: off)",
    )
    parser.add_argument(
        "--crop-radius",
        type=float,
        default=None,
        help="explicit crop radius in world units; overrides --crop-quantile",
    )
    parser.add_argument(
        "--crop-centre",
        type=lambda text: tuple(float(part) for part in text.split(",")),
        default=None,
        metavar="X,Y,Z",
        help="explicit crop centre; default is the median of the visible Gaussians",
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.05,
        help="drop Gaussians below this opacity, 0 disables the stage (default: 0.05)",
    )
    parser.add_argument(
        "--max-scale-quantile",
        type=float,
        default=None,
        help="drop Gaussians whose longest axis is above this quantile, e.g. 0.999 (default: off)",
    )
    parser.add_argument(
        "--max-anisotropy",
        type=float,
        default=None,
        help="drop Gaussians whose axis ratio exceeds this, e.g. 20 (default: off)",
    )
    parser.add_argument(
        "--sor", action="store_true", help="statistical outlier removal over centres (needs scipy)"
    )
    parser.add_argument(
        "--sor-neighbours", type=int, default=16, help="neighbours for --sor (default: 16)"
    )
    parser.add_argument(
        "--sor-std-ratio", type=float, default=2.0, help="std multiplier for --sor (default: 2.0)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would be removed and write nothing"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not 0.0 <= args.opacity < 1.0:
        print("[ERROR]: --opacity must be in [0, 1)", file=sys.stderr)
        return 2
    if args.crop_quantile is not None and not 0.0 < args.crop_quantile <= 1.0:
        print("[ERROR]: --crop-quantile must be in (0, 1]", file=sys.stderr)
        return 2
    if args.crop_radius is not None and args.crop_radius <= 0.0:
        print("[ERROR]: --crop-radius must be positive", file=sys.stderr)
        return 2
    if args.crop_centre is not None and len(args.crop_centre) != 3:
        print("[ERROR]: --crop-centre needs three comma-separated numbers", file=sys.stderr)
        return 2

    try:
        data, names = read_ply(args.input)
    except (PlyError, OSError) as exc:
        print(f"[ERROR]: {exc}", file=sys.stderr)
        return 1

    stages: list[tuple[str, np.ndarray]] = []
    try:
        if args.crop_quantile is not None or args.crop_radius is not None:
            keep_crop, origin, cut = crop_keep(
                data, names, args.crop_quantile, args.crop_radius, args.crop_centre
            )
            stages.append(
                (
                    f"crop r>{cut:.3f} @ ({origin[0]:.2f}, {origin[1]:.2f}, {origin[2]:.2f})",
                    keep_crop,
                )
            )
        if args.opacity > 0.0:
            stages.append((f"opacity < {args.opacity}", opacity_keep(data, names, args.opacity)))
        if args.max_scale_quantile is not None:
            stages.append(
                (
                    f"scale > q{args.max_scale_quantile}",
                    scale_keep(data, names, args.max_scale_quantile),
                )
            )
        if args.max_anisotropy is not None:
            stages.append(
                (
                    f"anisotropy > {args.max_anisotropy}",
                    anisotropy_keep(data, names, args.max_anisotropy),
                )
            )
        if args.sor:
            stages.append(
                (
                    f"outliers (k={args.sor_neighbours}, {args.sor_std_ratio} sigma)",
                    outlier_keep(data, names, args.sor_neighbours, args.sor_std_ratio),
                )
            )
    except PlyError as exc:
        print(f"[ERROR]: {exc}", file=sys.stderr)
        return 1

    total = len(data)
    keep = np.ones(total, dtype=bool)
    for label, stage in stages:
        # Report each stage against what earlier stages left, so the numbers add up
        # to the final count instead of double-counting Gaussians two stages agree on.
        removed = int((keep & ~stage).sum())
        keep &= stage
        print(f"[clean]: {label:<40} -{removed:>9,} ({removed / total:6.2%})")

    survivors = int(keep.sum())
    print(f"[clean]: {'kept':<40}  {survivors:>9,} ({survivors / total:6.2%} of {total:,})")
    if not stages:
        print("[clean]: every stage disabled, nothing to do")

    if args.dry_run:
        print("[clean]: dry run, no file written")
        return 0
    if survivors == 0:
        print(
            "[ERROR]: every Gaussian was filtered out; refusing to write an empty splat",
            file=sys.stderr,
        )
        return 1

    output = args.output or args.input
    before = args.input.stat().st_size
    write_ply(output, data[keep], names)
    after = output.stat().st_size
    print(f"[clean]: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB  ({output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
