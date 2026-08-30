"""Unit tests for the Gaussian splat cleanup filter."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

FIELDS = ["x", "y", "z", "opacity", "scale_0", "scale_1", "scale_2"]


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "clean_splat.py"
    spec = importlib.util.spec_from_file_location("clean_splat", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


clean_splat = _load_module()


def _splat(opacity_logits: np.ndarray, scales: np.ndarray | None = None) -> np.ndarray:
    count = len(opacity_logits)
    data = np.zeros(count, dtype=np.dtype([(name, "<f4") for name in FIELDS]))
    data["opacity"] = opacity_logits
    if scales is None:
        scales = np.full((count, 3), -3.0)
    for i in range(3):
        data[f"scale_{i}"] = scales[:, i]
    return data


def test_round_trip_preserves_values(tmp_path: Path) -> None:
    rng = np.random.default_rng(0)
    data = _splat(rng.normal(size=64).astype(np.float32))
    data["x"] = rng.normal(size=64)
    path = tmp_path / "splat.ply"

    clean_splat.write_ply(path, data, FIELDS)
    restored, names = clean_splat.read_ply(path)

    assert names == FIELDS
    assert len(restored) == len(data)
    assert np.allclose(restored["x"], data["x"])
    assert np.allclose(restored["opacity"], data["opacity"])


def test_reads_ascii_ply(tmp_path: Path) -> None:
    data = _splat(np.array([2.0, -6.0], dtype=np.float32))
    path = tmp_path / "ascii.ply"
    header = ["ply", "format ascii 1.0", f"element vertex {len(data)}"]
    header += [f"property float {name}" for name in FIELDS] + ["end_header"]
    rows = [" ".join(str(float(row[name])) for name in FIELDS) for row in data]
    path.write_text("\n".join(header + rows) + "\n")

    restored, names = clean_splat.read_ply(path)

    assert names == FIELDS
    assert np.allclose(restored["opacity"], data["opacity"], atol=1e-5)


def test_opacity_filter_cuts_on_sigmoid_not_logit() -> None:
    # sigmoid(-4) is about 0.018, sigmoid(0) is 0.5: a raw comparison would keep both.
    data = _splat(np.array([-4.0, 0.0], dtype=np.float32))

    keep = clean_splat.opacity_keep(data, FIELDS, 0.05)

    assert keep.tolist() == [False, True]


def test_anisotropy_filter_drops_needles() -> None:
    scales = np.log(np.array([[1.0, 1.0, 1.0], [100.0, 1.0, 1.0]]))
    data = _splat(np.zeros(2, dtype=np.float32), scales)

    keep = clean_splat.anisotropy_keep(data, FIELDS, 20.0)

    assert keep.tolist() == [True, False]


def test_scale_filter_is_relative_to_the_population() -> None:
    scales = np.log(np.tile(np.array([1.0, 2.0, 3.0, 400.0])[:, None], (1, 3)))
    data = _splat(np.zeros(4, dtype=np.float32), scales)

    keep = clean_splat.scale_keep(data, FIELDS, 0.75)

    assert keep.tolist() == [True, True, True, False]


def test_missing_property_is_reported_not_ignored() -> None:
    data = _splat(np.zeros(2, dtype=np.float32))

    with pytest.raises(clean_splat.PlyError, match="scale_0"):
        clean_splat.anisotropy_keep(data, ["x", "y", "z", "opacity"], 20.0)


def test_stages_compose_and_write_a_smaller_file(tmp_path: Path) -> None:
    logits = np.concatenate([np.full(50, 4.0), np.full(50, -8.0)]).astype(np.float32)
    data = _splat(logits)
    source = tmp_path / "in.ply"
    target = tmp_path / "out.ply"
    clean_splat.write_ply(source, data, FIELDS)

    assert clean_splat.main([str(source), "-o", str(target), "--opacity", "0.05"]) == 0

    kept, _ = clean_splat.read_ply(target)
    assert len(kept) == 50
    assert target.stat().st_size < source.stat().st_size


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    data = _splat(np.full(10, 4.0, dtype=np.float32))
    source = tmp_path / "in.ply"
    target = tmp_path / "out.ply"
    clean_splat.write_ply(source, data, FIELDS)

    assert clean_splat.main([str(source), "-o", str(target), "--dry-run"]) == 0
    assert not target.exists()


def test_refuses_to_write_an_empty_splat(tmp_path: Path) -> None:
    data = _splat(np.full(10, -20.0, dtype=np.float32))
    source = tmp_path / "in.ply"
    target = tmp_path / "out.ply"
    clean_splat.write_ply(source, data, FIELDS)

    assert clean_splat.main([str(source), "-o", str(target), "--opacity", "0.5"]) == 1
    assert not target.exists()


def test_rejects_an_out_of_range_opacity(tmp_path: Path) -> None:
    source = tmp_path / "in.ply"
    clean_splat.write_ply(source, _splat(np.zeros(4, dtype=np.float32)), FIELDS)

    assert clean_splat.main([str(source), "--opacity", "1.5"]) == 2


def test_round_trip_preserves_non_float_widths(tmp_path: Path) -> None:
    """A PLY carrying integer properties has to survive rewriting unchanged.

    The header is generated from the numpy dtype, so an unmapped width used to
    be written out as "float" while the payload kept its original size, leaving
    a file no reader can parse correctly.
    """
    names = ["x", "red", "material_id", "cluster"]
    dtype = np.dtype([("x", "<f4"), ("red", "u1"), ("material_id", "<i2"), ("cluster", "<u4")])
    data = np.zeros(4, dtype=dtype)
    data["x"] = [0.5, 1.5, 2.5, 3.5]
    data["red"] = [0, 127, 200, 255]
    data["material_id"] = [-2, -1, 300, 32000]
    data["cluster"] = [0, 1, 70000, 4000000000]
    path = tmp_path / "typed.ply"

    clean_splat.write_ply(path, data, names)
    restored, restored_names = clean_splat.read_ply(path)

    assert restored_names == names
    for name in names:
        assert restored.dtype[name] == dtype[name], name
        assert np.array_equal(restored[name], data[name]), name


def test_unwritable_property_type_is_reported(tmp_path: Path) -> None:
    """A dtype with no PLY spelling raises instead of writing a wrong header."""
    dtype = np.dtype([("x", "<f4"), ("stamp", "<i8")])
    data = np.zeros(2, dtype=dtype)

    with pytest.raises(clean_splat.PlyError, match="stamp"):
        clean_splat.write_ply(tmp_path / "bad.ply", data, ["x", "stamp"])


def test_crop_keeps_the_core_and_drops_the_shell() -> None:
    # 30 core Gaussians at the origin, 10 shell Gaussians at radius 10. The counts
    # must be unequal: with a half-and-half split the 0.6 quantile of the distance
    # distribution falls inside the shell and the crop would keep it.
    data = _splat(np.full(40, 4.0, dtype=np.float32))
    data["x"][:30] = 0.05
    data["x"][30:] = 10.0
    keep, origin, cut = clean_splat.crop_keep(data, FIELDS, 0.6, None, None)
    assert keep.tolist() == [True] * 30 + [False] * 10
    assert np.allclose(origin, [0.05, 0.0, 0.0], atol=1e-4)
    assert cut == pytest.approx(0.0, abs=1e-4)


def test_crop_centre_is_median_not_mean() -> None:
    # A one-sided shell drags a mean to x = 20 but cannot move the median.
    data = _splat(np.full(60, 4.0, dtype=np.float32))
    data["x"][40:] = 50.0
    keep, origin, _ = clean_splat.crop_keep(data, FIELDS, 0.5, None, None)
    assert np.all(np.abs(origin) < 0.5)
    assert keep[:40].all() and not keep[40:].any()


def test_crop_radius_overrides_the_quantile() -> None:
    data = _splat(np.full(60, 4.0, dtype=np.float32))
    data["x"][40:] = 50.0
    keep, _, cut = clean_splat.crop_keep(data, FIELDS, 1.0, 1.0, None)
    assert keep.tolist() == [True] * 40 + [False] * 20
    assert cut == 1.0


def test_crop_quantile_ignores_faint_fog() -> None:
    # sigmoid(-8) is about 0.0003, far below the 0.1 visibility gate, so the
    # radius quantile must be computed over the visible population alone. If the
    # fog were counted, the 0.9 quantile would land inside it and keep it.
    logits = np.full(50, 4.0, dtype=np.float32)
    logits[30:] = -8.0
    data = _splat(logits)
    data["x"][30:] = 50.0
    keep, _, _ = clean_splat.crop_keep(data, FIELDS, 0.9, None, None)
    assert keep[:30].all() and not keep[30:].any()
