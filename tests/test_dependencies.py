"""Static checks for Python dependency pins."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import Any


SPLATFACTOW_REQ = (
    "splatfacto-w @ "
    "git+https://github.com/KevinXu02/splatfacto-w.git@119a3bfb3aa03669278e174ff11c4dfdcbcf97d7"
)


def _pyproject() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    return tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))


def _test_files() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[1]
    return sorted((repo_root / "tests").glob("test_*.py"))


def test_splat_extra_installs_splatfactow_plugin() -> None:
    """The supported splatfacto-w-light model needs the Splatfacto-W plugin."""
    pyproject = _pyproject()
    extras = pyproject["project"]["optional-dependencies"]  # type: ignore[index]

    assert "mini-mesh[nerf]" in extras["splat"]  # type: ignore[index]
    assert SPLATFACTOW_REQ in extras["splat"]  # type: ignore[index]


def test_local_extra_uses_splat_stack() -> None:
    """Local setup should install the full Gaussian splatting stack."""
    pyproject = _pyproject()
    extras = pyproject["project"]["optional-dependencies"]  # type: ignore[index]

    assert extras["local"] == ["mini-mesh[core,rembg,splat,sam,vggsfm]"]  # type: ignore[index]


def test_unit_tests_do_not_import_torch_at_module_scope() -> None:
    """Core CI does not install Torch, so Torch-specific tests must import-skip lazily."""
    offenders: list[str] = []

    for test_file in _test_files():
        tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
        for node in tree.body:
            if isinstance(node, ast.Import) and any(alias.name == "torch" for alias in node.names):
                offenders.append(str(test_file.relative_to(test_file.parents[1])))
            if isinstance(node, ast.ImportFrom) and node.module == "torch":
                offenders.append(str(test_file.relative_to(test_file.parents[1])))

    assert offenders == []
