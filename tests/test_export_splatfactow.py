"""Unit tests for the splatfacto-w-light PLY exporter helpers."""

from __future__ import annotations

import importlib.util
from collections import OrderedDict
from pathlib import Path
from types import ModuleType

import numpy as np


def _load_exporter_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "export_splatfactow.py"
    spec = importlib.util.spec_from_file_location("export_splatfactow", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_finite_and_opacity_filter = _load_exporter_module()._finite_and_opacity_filter


def test_filter_handles_1d_fields_and_vector_opacity() -> None:
    """A single bad 1-D field entry should drop only that Gaussian."""
    tensors: OrderedDict[str, np.ndarray] = OrderedDict(
        [
            ("x", np.array([0.0, 1.0, 2.0], dtype=np.float32)),
            ("y", np.array([0.0, np.nan, 2.0], dtype=np.float32)),
            ("z", np.array([0.0, 1.0, 2.0], dtype=np.float32)),
            ("nx", np.zeros(3, dtype=np.float32)),
            ("ny", np.zeros(3, dtype=np.float32)),
            ("nz", np.zeros(3, dtype=np.float32)),
            ("red", np.array([10, 20, 30], dtype=np.uint8)),
            ("green", np.array([40, 50, 60], dtype=np.uint8)),
            ("blue", np.array([70, 80, 90], dtype=np.uint8)),
            ("opacity", np.array([0.0, 0.0, -6.0], dtype=np.float32)),
            ("scale_0", np.ones((3, 1), dtype=np.float32)),
        ]
    )

    count = _finite_and_opacity_filter(tensors, 3)

    assert count == 1
    assert tensors["x"].tolist() == [0.0]
    assert tensors["red"].tolist() == [10]


def test_filter_handles_column_opacity() -> None:
    """Nerfstudio checkpoints usually store opacity as (N, 1)."""
    tensors: OrderedDict[str, np.ndarray] = OrderedDict(
        [
            ("x", np.array([0.0, 1.0], dtype=np.float32)),
            ("y", np.array([0.0, 1.0], dtype=np.float32)),
            ("z", np.array([0.0, 1.0], dtype=np.float32)),
            ("opacity", np.array([[0.0], [-6.0]], dtype=np.float32)),
        ]
    )

    count = _finite_and_opacity_filter(tensors, 2)

    assert count == 1
    assert tensors["x"].tolist() == [0.0]
