"""Behavioural tests for scripts/export.sh using lightweight stubs.

These tests focus on the SDF-specific mesh/texturing workflow and the new
flags:
  - --mesh-only
  - --texture-only
  - --input-mesh-filename
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _make_stub_binaries(bin_dir: Path, log_path: Path) -> None:
    """Create stub binaries that log their invocations."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script_body = "\n".join(
        [
            "#!/usr/bin/env bash",
            'echo "$0 $@" >> \"$MINI_MESH_STUB_LOG\"',
        ]
    )
    for name in ("sdf-extract-mesh", "sdf-texture-mesh", "ns-export"):
        script_path = bin_dir / name
        script_path.write_text(script_body, encoding="utf-8")
        script_path.chmod(0o755)


def _run_export_script(
    repo_root: Path,
    exp_path: Path,
    extra_args: list[str],
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke scripts/export.sh with a minimal environment."""
    cmd = [
        "bash",
        str(repo_root / "scripts" / "export.sh"),
        str(exp_path),
        *extra_args,
    ]
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


class TestExportScriptSdfWorkflow:
    """Tests for SDF export behaviour (mesh-only / texture-only flags)."""

    def test_mesh_only_calls_extract_but_not_texture(self, tmp_path: Path) -> None:
        """`--mesh-only` should only call sdf-extract-mesh for SDF models."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "neus-facto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, ["--mesh-only"], env_overrides)
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "sdf-extract-mesh" in log
        assert "sdf-texture-mesh" not in log

    def test_texture_only_uses_existing_mesh_default_path(self, tmp_path: Path) -> None:
        """`--texture-only` should texture the default mesh.ply if present."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "neus-facto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        # Default mesh path that export.sh expects.
        (exp_path / "mesh.ply").write_text("ply\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, ["--texture-only"], env_overrides)
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "sdf-texture-mesh" in log
        assert "sdf-extract-mesh" not in log

    def test_texture_only_with_custom_input_mesh(self, tmp_path: Path) -> None:
        """Custom mesh via --input-mesh-filename should be passed through."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "neus-facto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        custom_mesh = exp_path / "mesh_edited.ply"
        custom_mesh.write_text("ply\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(
            repo_root,
            exp_path,
            ["--texture-only", "--input-mesh-filename", str(custom_mesh)],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "sdf-texture-mesh" in log
        assert str(custom_mesh) in log

    def test_invalid_flag_combinations_fail_for_sdf(self, tmp_path: Path) -> None:
        """Invalid SDF flag combinations should exit non-zero with an error."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "neus-facto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        # --mesh-only and --texture-only together should fail.
        result = _run_export_script(
            repo_root,
            exp_path,
            ["--mesh-only", "--texture-only"],
            env_overrides,
        )
        assert result.returncode != 0
        assert "--mesh-only and --texture-only" in result.stdout

        # --input-mesh-filename without --texture-only should fail.
        custom_mesh = exp_path / "mesh_edited.ply"
        custom_mesh.write_text("ply\n", encoding="utf-8")
        result = _run_export_script(
            repo_root,
            exp_path,
            ["--input-mesh-filename", str(custom_mesh)],
            env_overrides,
        )
        assert result.returncode != 0
        assert "requires --texture-only" in result.stdout


class TestExportScriptNerfGuards:
    """Tests that NeRF experiments reject SDF-only flags."""

    def test_nerf_experiment_rejects_sdf_only_flags(self, tmp_path: Path) -> None:
        """NeRF/splat/ngp experiments must error on SDF-only flags."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "nerfacto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(
            repo_root,
            exp_path,
            ["--mesh-only"],
            env_overrides,
        )
        assert result.returncode != 0
        assert "only supported for SDF experiments" in result.stdout


class TestExportScriptNeus2:
    """Tests for NeuS2 export behaviour."""

    def test_neus2_export_is_noop_when_mesh_exists(self, tmp_path: Path) -> None:
        """NeuS2 export should succeed without calling SDF/NeRF exporters."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "neus2"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "mesh.obj").write_text("obj\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, [], env_overrides)
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
        # No external export tools should be invoked for NeuS2.
        assert log == ""

    def test_neus2_export_errors_when_mesh_missing(self, tmp_path: Path) -> None:
        """NeuS2 export should fail if the expected mesh is missing."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "neus2"
        exp_path.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, [], env_overrides)
        assert result.returncode != 0
