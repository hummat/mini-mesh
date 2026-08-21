#!/usr/bin/env python3
"""Filter a 3D Gaussian Splatting PLY down to what is worth shipping.

A trained splat carries a large tail of Gaussians that contribute almost nothing
to a rendered view: near-transparent blobs, a few enormous ones covering half the
scene, and needle-shaped slivers. They cost file size and viewer performance
without earning it back in quality.

Only the opacity stage is on by default, because it is the only one whose quality
cost has been measured (by filtering a checkpoint and re-running ns-eval): at 0.05
it removes roughly 38% of Gaussians for an LPIPS change well inside the per-image
spread on both a cluttered outdoor capture and a sharp object capture. 0.10 is
free on the former and costs a full spread on the latter, so it is not a safe
default. The scale, anisotropy and outlier stages are implemented but off until
they have been measured the same way; see hummat/mini-mesh#30.

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
    reverse = {
        value: key
        for key, value in PLY_DTYPES.items()
        if key in ("uchar", "int", "float", "double")
    }
    for name in names:
        kind = out.dtype[name].str[1:]
        header.append(f"property {reverse.get(kind, 'float')} {name}")
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

    try:
        data, names = read_ply(args.input)
    except (PlyError, OSError) as exc:
        print(f"[ERROR]: {exc}", file=sys.stderr)
        return 1

    stages: list[tuple[str, np.ndarray]] = []
    try:
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
