"""Mini-mesh Python process defaults."""

from __future__ import annotations

import os
import sys


def _configure_float32_matmul_precision() -> None:
    precision = os.environ.get("MINI_MESH_FLOAT32_MATMUL_PRECISION", "high")
    if precision == "default":
        return
    if precision not in {"highest", "high", "medium"}:
        print(
            "[mini-mesh] Ignoring invalid MINI_MESH_FLOAT32_MATMUL_PRECISION="
            f"{precision!r}; expected highest, high, medium, or default.",
            file=sys.stderr,
        )
        return

    try:
        import torch
    except ModuleNotFoundError:
        return

    torch.set_float32_matmul_precision(precision)


_configure_float32_matmul_precision()
