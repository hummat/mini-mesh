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
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace


def _make_stub_binaries(bin_dir: Path, log_path: Path) -> None:
    """Create stub binaries that log their invocations."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script_body = "\n".join(
        [
            "#!/usr/bin/env bash",
            'echo "$0 $@" >> "$MINI_MESH_STUB_LOG"',
        ]
    )
    # "python" is stubbed too: the splat cleanup step runs the real clean_splat.py
    # otherwise, and these tests write placeholder PLY files it rightly rejects.
    names = (
        "sdf-extract-mesh",
        "sdf-texture-mesh",
        "sdf-render",
        "ns-export",
        "ns-render",
        "python",
    )
    for name in names:
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


def test_render_nerfstudio_orbit_rewrites_data_and_checkpoint_roots(tmp_path: Path) -> None:
    """The Nerfstudio render wrapper should make Docker-written paths portable."""
    repo_root = Path(__file__).resolve().parents[1]
    spec = spec_from_file_location(
        "render_nerfstudio_orbit", repo_root / "scripts" / "render_nerfstudio_orbit.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    scene_dir = tmp_path / "scene"
    load_config = scene_dir / "train" / "sfmcmc" / "splatfacto" / "run" / "config.yml"
    load_config.parent.mkdir(parents=True)
    config = SimpleNamespace(
        data=Path("/data"),
        output_dir=Path("/data/train"),
        pipeline=SimpleNamespace(
            datamanager=SimpleNamespace(
                data=None,
                dataparser=SimpleNamespace(data=Path("/data")),
            )
        ),
    )

    patched = module._override_portable_paths(config, load_config, scene_dir)

    assert patched.data == scene_dir
    assert patched.output_dir == scene_dir / "train"
    assert patched.pipeline.datamanager.data == scene_dir
    assert patched.pipeline.datamanager.dataparser.data == scene_dir


def test_render_nerfstudio_orbit_uses_full_image_datamanager_camera(tmp_path: Path) -> None:
    """The Nerfstudio render wrapper should support splatfacto's FullImageDatamanager."""
    repo_root = Path(__file__).resolve().parents[1]
    spec = spec_from_file_location(
        "render_nerfstudio_orbit", repo_root / "scripts" / "render_nerfstudio_orbit.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    class FakeCameras:
        def __init__(self) -> None:
            self.selected = False
            self.device = None

        def __getitem__(self, key: slice) -> "FakeCameras":
            assert key == slice(0, 1)
            self.selected = True
            return self

        def to(self, device: str) -> "FakeCameras":
            self.device = device
            return self

    cameras = FakeCameras()
    pipeline = SimpleNamespace(
        device="cuda",
        datamanager=SimpleNamespace(eval_dataset=SimpleNamespace(cameras=cameras)),
    )

    camera = module._get_spiral_seed_camera(pipeline)

    assert camera is cameras
    assert cameras.selected
    assert cameras.device == "cuda"


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

    def test_nerf_export_runs_repeated_methods_in_order(self, tmp_path: Path) -> None:
        """Repeated --method flags should run each requested NeRF exporter."""
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
            ["--method", "pointcloud", "--method", "poisson"],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export pointcloud" in log
        assert "ns-export poisson" in log
        assert log.index("ns-export pointcloud") < log.index("ns-export poisson")
        assert "ns-export tsdf" not in log

    def test_nerf_export_runs_comma_separated_methods(self, tmp_path: Path) -> None:
        """A single --method value may request multiple NeRF exporters."""
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
            ["--method", "poisson,pointcloud"],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export poisson" in log
        assert "ns-export pointcloud" in log

    def test_nerf_multi_export_skips_existing_outputs_independently(self, tmp_path: Path) -> None:
        """Existing output for one requested method should not skip the other methods."""
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

        result = _run_export_script(
            repo_root,
            exp_path,
            ["--method", "poisson,pointcloud"],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr
        assert "poisson_mesh.ply already exists" in result.stdout

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export pointcloud" in log
        assert "ns-export poisson" not in log

    def test_nerf_export_renders_orbit_frames_without_default_poisson(self, tmp_path: Path) -> None:
        """`orbit-frames` should render frames without also running the default Poisson export."""
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
            repo_root, exp_path, ["--method", "orbit-frames"], env_overrides
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-render spiral" in log
        assert f"--output-path {exp_path / 'orbit_frames'}" in log
        assert "--output-format images" in log
        assert "--seconds 30" in log
        assert "--frame-rate 1" in log
        assert "ns-export poisson" not in log

    def test_orbit_frames_default_to_jpeg(self, tmp_path: Path) -> None:
        """Delivery frames stay JPEG unless the caller asks otherwise."""
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
            repo_root, exp_path, ["--method", "orbit-frames"], env_overrides
        )
        assert result.returncode == 0, result.stderr
        assert "--image-format jpeg" in log_path.read_text(encoding="utf-8")

    def test_orbit_frames_accept_png_for_measurement(self, tmp_path: Path) -> None:
        """Frames scored against other renders need the lossless format to reach ns-render."""
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
            ["--method", "orbit-frames", "--orbit-image-format", "png"],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr
        assert "--image-format png" in log_path.read_text(encoding="utf-8")

    def test_orbit_format_change_does_not_render_into_a_stale_directory(
        self, tmp_path: Path
    ) -> None:
        """Frames left from another format are not the output that was asked for."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "nerfacto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        frames = exp_path / "orbit_frames"
        frames.mkdir()
        (frames / "00000.jpg").write_text("old", encoding="utf-8")

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
            ["--method", "orbit-frames", "--orbit-image-format", "png"],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr
        assert "those frames are not png" in result.stdout
        assert not log_path.exists() or "ns-render spiral" not in log_path.read_text(
            encoding="utf-8"
        )
        assert (frames / "00000.jpg").exists()

    def test_orbit_overwrite_clears_frames_of_the_previous_format(
        self, tmp_path: Path
    ) -> None:
        """--overwrite re-renders, so the old frames go rather than mixing with the new."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "nerfacto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        frames = exp_path / "orbit_frames"
        frames.mkdir()
        (frames / "00000.jpg").write_text("old", encoding="utf-8")

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
            ["--method", "orbit-frames", "--orbit-image-format", "png", "--overwrite"],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr
        assert "--image-format png" in log_path.read_text(encoding="utf-8")
        assert not (frames / "00000.jpg").exists()

    def test_orbit_image_format_rejects_unknown_value(self, tmp_path: Path) -> None:
        """An unsupported format fails loudly rather than reaching the renderer."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "nerfacto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        result = _run_export_script(
            repo_root,
            exp_path,
            ["--method", "orbit-frames", "--orbit-image-format", "webp"],
        )
        assert result.returncode != 0
        assert "--orbit-image-format must be one of" in result.stdout + result.stderr

    def test_nerf_export_combines_mesh_and_orbit_frames(self, tmp_path: Path) -> None:
        """`orbit-frames` should compose with other requested NeRF export methods."""
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
            repo_root, exp_path, ["--method", "poisson,orbit-frames"], env_overrides
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export poisson" in log
        assert "ns-render spiral" in log

    def test_orbit_frames_skip_existing_frame_dir_without_overwrite(self, tmp_path: Path) -> None:
        """Existing orbit frame output should be idempotent like mesh and splat outputs."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "nerfacto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        orbit_frames = exp_path / "orbit_frames"
        orbit_frames.mkdir()
        (orbit_frames / "00000.png").write_text("png\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(
            repo_root, exp_path, ["--method", "orbit-frames"], env_overrides
        )
        assert result.returncode == 0, result.stderr
        assert "orbit_frames already exists" in result.stdout
        assert not log_path.exists()

    def test_orbit_frames_infers_data_path_for_run_directory(self, tmp_path: Path) -> None:
        """Orbit rendering should recover from Docker-style /data paths in saved configs."""
        repo_root = Path(__file__).resolve().parents[1]
        scene_dir = tmp_path / "scene"
        exp_path = scene_dir / "train" / "sfmcmc" / "splatfacto" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (scene_dir / "transforms.json").write_text("{}", encoding="utf-8")
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

        result = _run_export_script(
            repo_root, exp_path, ["--method", "orbit-frames"], env_overrides
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert f"python {repo_root / 'scripts' / 'render_nerfstudio_orbit.py'}" in log
        assert f"--data {scene_dir}" in log
        assert "ns-render spiral" not in log

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

    def test_splat_export_can_add_orbit_frames(self, tmp_path: Path) -> None:
        """Splat exports should be able to add the same orbit frame sequence."""
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
            repo_root, exp_path, ["--method", "orbit-frames"], env_overrides
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-export gaussian-splat" in log
        assert "ns-render spiral" in log

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

    def _run_splat_export_with_cleanup(
        self, tmp_path: Path, extra_args: list[str]
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        """Export a splat with an output file already in place so cleanup has a target."""
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

        result = _run_export_script(
            repo_root, exp_path, ["--overwrite", *extra_args], env_overrides
        )
        log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        return result, log

    def test_splat_export_cleans_the_exported_splat_by_default(self, tmp_path: Path) -> None:
        """A splat export should hand its output to clean_splat.py without being asked."""
        result, log = self._run_splat_export_with_cleanup(tmp_path, [])
        assert result.returncode == 0, result.stderr
        assert "clean_splat.py" in log
        assert "splat.ply" in log

    def test_no_clean_skips_the_cleanup_step(self, tmp_path: Path) -> None:
        """--no-clean should leave the exported splat exactly as nerfstudio wrote it."""
        result, log = self._run_splat_export_with_cleanup(tmp_path, ["--no-clean"])
        assert result.returncode == 0, result.stderr
        assert "ns-export gaussian-splat" in log
        assert "clean_splat.py" not in log

    def test_clean_flags_are_forwarded_without_their_prefix(self, tmp_path: Path) -> None:
        """--clean-opacity is the export-level spelling of clean_splat.py's --opacity."""
        result, log = self._run_splat_export_with_cleanup(
            tmp_path, ["--clean-opacity", "0.1", "--clean-sor"]
        )
        assert result.returncode == 0, result.stderr
        cleanup = [line for line in log.splitlines() if "clean_splat.py" in line]
        assert len(cleanup) == 1
        assert "--opacity 0.1" in cleanup[0]
        assert "--sor" in cleanup[0]
        assert "--clean-" not in cleanup[0]

    def test_mesh_export_does_not_run_the_splat_cleanup(self, tmp_path: Path) -> None:
        """Cleanup is splat-specific; a Poisson mesh must not be routed through it."""
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

        result = _run_export_script(repo_root, exp_path, [], env_overrides)
        assert result.returncode == 0, result.stderr
        assert "clean_splat.py" not in log_path.read_text(encoding="utf-8")

    def _run_and_log(
        self, tmp_path: Path, model: str, extra_args: list[str]
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        """Export one experiment of the given model and return the stub log."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / model
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(repo_root, exp_path, extra_args, env_overrides)
        log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        return result, log

    def test_splat_export_crops_nothing_by_default(self, tmp_path: Path) -> None:
        """nerfstudio's default is no crop box; export.sh must not invent one."""
        result, log = self._run_and_log(tmp_path, "splatfacto", [])
        assert result.returncode == 0, result.stderr
        assert "ns-export gaussian-splat" in log
        assert "--obb-" not in log

    def test_poisson_export_crops_nothing_by_default(self, tmp_path: Path) -> None:
        """The same default applies to the mesh exporters, which share the flags."""
        result, log = self._run_and_log(tmp_path, "nerfacto", [])
        assert result.returncode == 0, result.stderr
        assert "ns-export poisson" in log
        assert "--obb-" not in log

    def test_one_obb_flag_turns_cropping_on_with_defaults_for_the_rest(
        self, tmp_path: Path
    ) -> None:
        """nerfstudio ignores a partial triplet, so one flag has to supply all three."""
        result, log = self._run_and_log(tmp_path, "splatfacto", ["--obb-scale", "2", "2", "2"])
        assert result.returncode == 0, result.stderr
        assert "--obb-scale 2 2 2" in log
        assert "--obb-center 0 0 0" in log
        assert "--obb-rotation 0 0 0" in log


class TestExportScriptOrbitFramesSdfWorkflow:
    """Tests for image-sequence render export on SDF-style methods."""

    def test_sdf_export_can_add_orbit_frames(self, tmp_path: Path) -> None:
        """SDF exports should add an orbit frame sequence after the normal mesh workflow."""
        repo_root = Path(__file__).resolve().parents[1]
        exp_path = tmp_path / "train" / "scene" / "neus-facto"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")
        (exp_path / "mesh.ply").write_text("ply\n", encoding="utf-8")
        (exp_path / "mesh.obj").write_text("obj\n", encoding="utf-8")

        log_path = tmp_path / "stub.log"
        bin_dir = tmp_path / "bin"
        _make_stub_binaries(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "MINI_MESH_STUB_LOG": str(log_path),
        }

        result = _run_export_script(
            repo_root, exp_path, ["--method", "orbit-frames"], env_overrides
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "sdf-render" in log
        assert "--traj spiral" in log
        assert f"--output-path {exp_path / 'orbit_frames'}" in log
        assert "--output-format images" in log
        assert "sdf-extract-mesh" not in log
        assert "sdf-texture-mesh" not in log
