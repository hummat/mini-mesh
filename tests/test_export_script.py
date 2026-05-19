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
            'echo "$0 $@" >> "$MINI_MESH_STUB_LOG"',
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
    env.setdefault("MINI_MESH_LOCAL_PREFIX", str(repo_root / ".local-does-not-exist-for-tests"))
    env.setdefault("MINI_MESH_VENV_BIN", str(repo_root / ".venv-does-not-exist-for-tests" / "bin"))
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


class TestExportScriptNerfWorkflow:
    """Tests for NeRF export argument routing."""

    def test_splat_export_skips_existing_output_without_overwrite(self, tmp_path: Path) -> None:
        """Gaussian splat export should be idempotent when splat.ply already exists."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "splatfacto" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        (exp_path / "splat.ply").write_text("ply\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, [], env_overrides)
        assert result.returncode == 0, result.stderr
        assert not log_path.exists()

    def test_splat_export_overwrites_existing_output_when_requested(self, tmp_path: Path) -> None:
        """--overwrite should rerun Gaussian splat export even when splat.ply exists."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "splatfacto" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        (exp_path / "splat.ply").write_text("ply\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, ["--overwrite"], env_overrides)
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export gaussian-splat" in log

    def test_splatfacto_w_light_export_skips_existing_output_without_overwrite(
        self, tmp_path: Path
    ) -> None:
        """The local splatfacto-w exporter should use the same output skip rule."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "splatfacto-w-light" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        (exp_path / "splat.ply").write_text("ply\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)
        python_stub = bin_dir / "python"
        python_stub.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    'echo "$0 $@" >> "$MINI_MESH_STUB_LOG"',
                ]
            ),
            encoding="utf-8",
        )
        python_stub.chmod(0o755)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, [], env_overrides)
        assert result.returncode == 0, result.stderr
        assert not log_path.exists()

    def test_pointcloud_export_skips_existing_output_without_overwrite(
        self, tmp_path: Path
    ) -> None:
        """Point cloud export should be idempotent when point_cloud.ply already exists."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "nerfacto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        (exp_path / "point_cloud.ply").write_text("ply\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, ["--method", "pointcloud"], env_overrides)
        assert result.returncode == 0, result.stderr
        assert not log_path.exists()

    def test_tsdf_export_skips_existing_output_without_overwrite(self, tmp_path: Path) -> None:
        """TSDF export should be idempotent when tsdf_mesh.ply already exists."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "nerfacto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        (exp_path / "tsdf_mesh.ply").write_text("ply\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, ["--method", "tsdf"], env_overrides)
        assert result.returncode == 0, result.stderr
        assert not log_path.exists()

    def test_poisson_export_skips_existing_output_without_overwrite(self, tmp_path: Path) -> None:
        """Poisson export should be idempotent when poisson_mesh.ply already exists."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "nerfacto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        (exp_path / "poisson_mesh.ply").write_text("ply\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, [], env_overrides)
        assert result.returncode == 0, result.stderr
        assert not log_path.exists()

    def test_splat_export_uses_parent_model_name_for_run_timestamp(self, tmp_path: Path) -> None:
        """Pipeline paths end in /run, but the model name is the parent directory."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "splatfacto" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, [], env_overrides)
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export gaussian-splat" in log
        assert "sdf-extract-mesh" not in log

    def test_splat_mcmc_export_uses_parent_model_name_for_run_timestamp(
        self, tmp_path: Path
    ) -> None:
        """splatfacto-mcmc should route through the Nerfstudio splat exporter."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "splatfacto-mcmc" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, [], env_overrides)
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export gaussian-splat" in log
        assert "sdf-extract-mesh" not in log

    def test_splatfacto_w_light_uses_local_exporter(self, tmp_path: Path) -> None:
        """splatfacto-w-light needs the local duck-typed Gaussian exporter."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "splatfacto-w-light" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)
        python_stub = bin_dir / "python"
        python_stub.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    'echo "$0 $@" >> "$MINI_MESH_STUB_LOG"',
                ]
            ),
            encoding="utf-8",
        )
        python_stub.chmod(0o755)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, [], env_overrides)
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert f"python {repo_root / 'scripts' / 'export_splatfactow.py'}" in log
        assert "ns-export gaussian-splat" not in log
        assert "sdf-extract-mesh" not in log

    def test_splatfacto_w_light_forwards_appearance_bake_selection(self, tmp_path: Path) -> None:
        """The W-light exporter should let users choose which appearance to bake."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "splatfacto-w-light" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)
        python_stub = bin_dir / "python"
        python_stub.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    'echo "$0 $@" >> "$MINI_MESH_STUB_LOG"',
                ]
            ),
            encoding="utf-8",
        )
        python_stub.chmod(0o755)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(
            repo_root,
            exp_path,
            ["--appearance-mode", "index", "--appearance-idx", "2"],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "--appearance-mode index --appearance-idx 2" in log

    def test_nerf_export_rejects_splatfactow_appearance_selection(self, tmp_path: Path) -> None:
        """Appearance bake selection is only defined for the W-light exporter."""
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
            repo_root, exp_path, ["--appearance-mode", "mean"], env_overrides
        )

        assert result.returncode != 0
        assert "only supported for splatfacto-w-light exports" in result.stdout

    def test_poisson_export_does_not_forward_bounding_box_args(self, tmp_path: Path) -> None:
        """Poisson export does not accept bounding-box min/max arguments."""
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
            [
                "--bounding-box-min",
                "-0.5",
                "-0.5",
                "-0.5",
                "--bounding-box-max",
                "0.5",
                "0.5",
                "0.5",
                "--obb-center",
                "0",
                "0",
                "0",
                "--obb-scale",
                "0",
                "0",
                "0",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export poisson" in log
        assert "--obb-center 0 0 0" in log
        assert "--obb-scale 0 0 0" in log
        assert "--bounding-box-min" not in log
        assert "--bounding-box-max" not in log

    def test_pointcloud_export_does_not_forward_bounding_box_args(self, tmp_path: Path) -> None:
        """Pointcloud export uses OBB cropping, not TSDF bounding-box flags."""
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
            [
                "--method",
                "pointcloud",
                "--bounding-box-min",
                "-0.5",
                "-0.5",
                "-0.5",
                "--bounding-box-max",
                "0.5",
                "0.5",
                "0.5",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export pointcloud" in log
        assert "--bounding-box-min" not in log
        assert "--bounding-box-max" not in log

    def test_gaussian_splat_export_does_not_forward_bounding_box_args(self, tmp_path: Path) -> None:
        """Gaussian splat export uses OBB cropping, not TSDF bounding-box flags."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "splatfacto" / "run"
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
            [
                "--bounding-box-min",
                "-0.5",
                "-0.5",
                "-0.5",
                "--bounding-box-max",
                "0.5",
                "0.5",
                "0.5",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export gaussian-splat" in log
        assert "--bounding-box-min" not in log
        assert "--bounding-box-max" not in log

    def test_tsdf_export_forwards_bounding_box_args(self, tmp_path: Path) -> None:
        """TSDF export accepts bounding-box min/max arguments."""
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
            [
                "--method",
                "tsdf",
                "--bounding-box-min",
                "-0.5",
                "-0.5",
                "-0.5",
                "--bounding-box-max",
                "0.5",
                "0.5",
                "0.5",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export tsdf" in log
        assert "--bounding-box-min -0.5 -0.5 -0.5" in log
        assert "--bounding-box-max 0.5 0.5 0.5" in log

    def test_tsdf_export_forwards_downscale_factor(self, tmp_path: Path) -> None:
        """The documented TSDF downscale flag should reach ns-export."""
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
            ["--method", "tsdf", "--downscale-factor", "2"],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export tsdf" in log
        assert "--downscale-factor 2" in log

    def test_tsdf_export_does_not_forward_single_resolution(self, tmp_path: Path) -> None:
        """SDF --resolution is a single int and must not collide with TSDF's 3-D resolution."""
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
            ["--method", "tsdf", "--resolution", "512"],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export tsdf" in log
        assert "--resolution 256 256 256" in log
        assert "--resolution 512" not in log

    def test_nerf_export_forwards_single_obb_triplet(self, tmp_path: Path) -> None:
        """User OBB values should replace defaults instead of relying on last-wins parsing."""
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
            [
                "--obb-center",
                "1",
                "2",
                "3",
                "--obb-rotation",
                "4",
                "5",
                "6",
                "--obb-scale",
                "7",
                "8",
                "9",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert log.count("--obb-center") == 1
        assert log.count("--obb-rotation") == 1
        assert log.count("--obb-scale") == 1
        assert "--obb-center 1 2 3" in log
        assert "--obb-rotation 4 5 6" in log
        assert "--obb-scale 7 8 9" in log
