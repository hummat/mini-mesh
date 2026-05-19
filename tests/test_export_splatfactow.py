"""Unit tests for the splatfacto-w-light PLY exporter helpers."""

from __future__ import annotations

import importlib.util
from collections import OrderedDict
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest


def _load_exporter_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "export_splatfactow.py"
    spec = importlib.util.spec_from_file_location("export_splatfactow", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_exporter_module = _load_exporter_module()
_add_sh_coefficients = _exporter_module._add_sh_coefficients
_finite_and_opacity_filter = _exporter_module._finite_and_opacity_filter


def _torch_module() -> ModuleType:
    return pytest.importorskip("torch")


class _FakeColorNetwork:
    def __init__(self, torch_module: ModuleType) -> None:
        self._torch = torch_module

    def __call__(self, appearance_embed: Any, appearance_features: Any) -> Any:
        torch = self._torch
        count = appearance_features.shape[0]
        coeffs = torch.zeros((count, 4, 3), dtype=torch.float32)
        coeffs[:, 0, 0] = appearance_embed[:, 0] + appearance_features[:, 0]
        coeffs[:, 1, 1] = appearance_embed[:, 0] - appearance_features[:, 0]
        return coeffs


class _FakeSplatfactoWModel:
    def __init__(self, torch_module: ModuleType) -> None:
        torch = torch_module
        self.appearance_features = torch.tensor([[1.0, 0.0], [3.0, 0.0]])
        self.appearance_embeds = torch.nn.Embedding.from_pretrained(
            torch.tensor([[10.0, 0.0], [20.0, 0.0], [30.0, 0.0]]),
            freeze=False,
        )
        self.color_nn = _FakeColorNetwork(torch)
        self.config = type("Config", (), {"sh_degree": 1})()


def test_sh_export_bakes_mean_appearance_embedding() -> None:
    """Mean mode should bake the average embedding into standard SH coefficients."""
    tensors: OrderedDict[str, np.ndarray] = OrderedDict()

    _add_sh_coefficients(_FakeSplatfactoWModel(_torch_module()), tensors, 2, "mean", None)

    assert tensors["f_dc_0"].reshape(-1).tolist() == [21.0, 23.0]
    assert tensors["f_rest_3"].reshape(-1).tolist() == [19.0, 17.0]


def test_sh_export_bakes_indexed_appearance_embedding() -> None:
    """Index mode should bake the requested training-image embedding."""
    tensors: OrderedDict[str, np.ndarray] = OrderedDict()

    _add_sh_coefficients(_FakeSplatfactoWModel(_torch_module()), tensors, 2, "index", 2)

    assert tensors["f_dc_0"].reshape(-1).tolist() == [31.0, 33.0]


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
