"""Lightweight behavioural tests for Bash scripts.

These tests stub external binaries so we can exercise the CLI plumbing
without requiring COLMAP, ffmpeg, nerfstudio, GPUs, etc.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _run_script(
    repo_root: Path,
    script_rel_path: str,
    args: list[str],
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a Bash script from the repository with a minimal environment."""
    cmd = ["bash", str(repo_root / script_rel_path), *args]
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


def _make_simple_stub(bin_dir: Path, name: str, log_path: Path) -> None:
    """Create a simple stub that logs its invocation and exits successfully."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script_path = bin_dir / name
    script_body = "\n".join(
        [
            "#!/usr/bin/env bash",
            f'echo "$0 $*" >> "{log_path}"',
        ]
    )
    script_path.write_text(script_body, encoding="utf-8")
    script_path.chmod(0o755)


class TestFfmpegScript:
    """Tests for scripts/ffmpeg.sh."""

    def test_ffmpeg_invocation_and_args(self, tmp_path: Path) -> None:
        """ffmpeg.sh should call ffmpeg with expected filters and create images dir."""
        repo_root = Path(__file__).resolve().parents[1]
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"dummy")

        log_path = tmp_path / "stub_ffmpeg.log"
        bin_dir = tmp_path / "bin"
        _make_simple_stub(bin_dir, "ffmpeg", log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/ffmpeg.sh",
            [
                str(video_path),
                "--fps",
                "3",
                "--time_slice",
                "1,2",
                "--hdr",
                "--overwrite",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        images_dir = tmp_path / "images"
        assert images_dir.is_dir()

        log = log_path.read_text(encoding="utf-8")
        assert "ffmpeg" in log
        assert "-i" in log
        assert str(video_path) in log
        assert "fps=3" in log
        assert "between(t,1,2)" in log


class TestEnvBootstrap:
    """Tests for scripts/env.sh local dependency bootstrap."""

    def test_env_bootstrap_prefers_local_prefix(self, tmp_path: Path) -> None:
        """env.sh should put local build outputs before stale user binaries."""
        repo_root = Path(__file__).resolve().parents[1]
        prefix = tmp_path / "mini-mesh"
        venv_bin = tmp_path / "venv" / "bin"
        (prefix / "bin").mkdir(parents=True)
        (prefix / "lib").mkdir()
        (prefix / "lib64").mkdir()
        venv_bin.mkdir(parents=True)
        command = (
            "source scripts/env.sh; "
            'printf \'%s\n%s\n%s\n\' "$PATH" "$LD_LIBRARY_PATH" "$CMAKE_PREFIX_PATH"'
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                command,
            ],
            cwd=repo_root,
            env={
                **os.environ,
                "MINI_MESH_LOCAL_PREFIX": str(prefix),
                "MINI_MESH_VENV_BIN": str(venv_bin),
                "PATH": "/stale/bin:/usr/bin",
                "LD_LIBRARY_PATH": "/cuda/lib64",
                "CMAKE_PREFIX_PATH": "/other/prefix",
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        path, ld_library_path, cmake_prefix_path = result.stdout.splitlines()
        assert path.startswith(f"{prefix / 'bin'}:{venv_bin}:")
        assert ld_library_path.startswith(f"{prefix / 'lib'}:{prefix / 'lib64'}:")
        assert cmake_prefix_path.startswith(f"{prefix}:")

    def test_env_bootstrap_warns_for_explicit_missing_local_prefix(self, tmp_path: Path) -> None:
        """An explicitly configured but missing prefix should fail loudly enough to diagnose."""
        repo_root = Path(__file__).resolve().parents[1]
        missing_prefix = tmp_path / "missing-prefix"

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source scripts/env.sh; printf '%s' \"$PATH\"",
            ],
            cwd=repo_root,
            env={
                **os.environ,
                "MINI_MESH_LOCAL_PREFIX": str(missing_prefix),
                "MINI_MESH_VENV_BIN": str(tmp_path / "missing-venv" / "bin"),
                "PATH": "/usr/bin",
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert result.stdout == "/usr/bin"
        assert f"MINI_MESH_LOCAL_PREFIX is set but missing: {missing_prefix}" in result.stderr
        assert "Run 'make build' or unset MINI_MESH_LOCAL_PREFIX." in result.stderr


class TestSfmScript:
    """Tests for scripts/sfm.sh with stubbed COLMAP."""

    def test_sfm_calls_colmap_pipeline(self, tmp_path: Path) -> None:
        """sfm.sh should drive the expected COLMAP subcommands."""
        repo_root = Path(__file__).resolve().parents[1]
        images_dir = tmp_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_colmap.log"
        bin_dir = tmp_path / "bin"
        _make_simple_stub(bin_dir, "colmap", log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/sfm.sh",
            [
                str(images_dir),
                "--matcher",
                "exhaustive",
                "--extra",
                "--overwrite",
                "--num_threads",
                "4",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "colmap feature_extractor" in log
        assert "colmap exhaustive_matcher" in log
        assert "colmap mapper" in log
        assert "colmap bundle_adjuster" in log


class TestDlSfmScript:
    """Tests for scripts/dl_sfm.sh with stubbed hloc / vggsfm."""

    def test_hloc_invocation_and_matcher_rewrite(self, tmp_path: Path) -> None:
        """dl_sfm.sh hloc mode should rewrite non-exhaustive matcher to retrieval."""
        repo_root = Path(__file__).resolve().parents[1]
        images_dir = tmp_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_hloc.log"
        bin_dir = tmp_path / "bin"
        _make_simple_stub(bin_dir, "hloc", log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/dl_sfm.sh",
            [
                str(images_dir),
                "--method",
                "hloc",
                "--matcher",
                "sequential",
                "--overwrite",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "hloc" in log
        # Non-exhaustive matcher should be rewritten to retrieval.
        assert "--pairs retrieval" in log

    def test_vggsfm_uses_correct_binary_per_matcher(self, tmp_path: Path) -> None:
        """dl_sfm.sh vggsfm mode should pick vggsfm-video vs vggsfm-image."""
        repo_root = Path(__file__).resolve().parents[1]
        images_dir = tmp_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_vggsfm.log"
        bin_dir = tmp_path / "bin"
        _make_simple_stub(bin_dir, "vggsfm-video", log_path)
        _make_simple_stub(bin_dir, "vggsfm-image", log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        # Sequential matcher -> vggsfm-video
        result = _run_script(
            repo_root,
            "scripts/dl_sfm.sh",
            [
                str(images_dir),
                "--method",
                "vggsfm",
                "--matcher",
                "sequential",
                "--overwrite",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "vggsfm-video" in log

        # Exhaustive matcher -> vggsfm-image
        log_path.write_text("", encoding="utf-8")
        result = _run_script(
            repo_root,
            "scripts/dl_sfm.sh",
            [
                str(images_dir),
                "--method",
                "vggsfm",
                "--matcher",
                "exhaustive",
                "--overwrite",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "vggsfm-image" in log


class TestTrainScript:
    """Tests for scripts/train.sh with stubbed training binaries."""

    def _make_train_stubs(self, bin_dir: Path, log_path: Path) -> None:
        """Create stubs for nvidia-smi, sdf-train, and ns-train."""
        bin_dir.mkdir(parents=True, exist_ok=True)

        # nvidia-smi: just log and exit, to satisfy the GPU check.
        nvidia_smi = bin_dir / "nvidia-smi"
        nvidia_smi.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    f'echo "$0 $*" >> "{log_path}"',
                    'echo "GPU 0"',
                ]
            ),
            encoding="utf-8",
        )
        nvidia_smi.chmod(0o755)

        _make_simple_stub(bin_dir, "sdf-train", log_path)
        _make_simple_stub(bin_dir, "ns-train", log_path)

    def test_train_sdf_uses_sdf_train_and_defaults(self, tmp_path: Path) -> None:
        """SDF models should use sdf-train with nerfstudio-data."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_train.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "neus-facto",
                "my_exp",
                str(data_dir),
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "sdf-train neus-facto" in log
        assert "--output-dir" in log
        assert str(data_dir / "train") in log
        assert "nerfstudio-data" in log
        assert f"--data {data_dir}" in log

    def test_train_nerf_uses_ns_train(self, tmp_path: Path) -> None:
        """NeRF models should use ns-train with NS_DATA_DEFAULTS."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_train_nerf.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "nerfacto",
                "my_exp",
                str(data_dir),
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-train nerfacto" in log
        assert "--output-dir" in log
        assert str(data_dir / "train") in log
        assert "nerfstudio-data" in log
        assert f"--data {data_dir}" in log

    def test_train_consumes_missing_implicit_model_config(self, tmp_path: Path) -> None:
        """If the default model-name config is absent, it should not become a CLI arg."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_train_missing_implicit.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "future-splat-model",
                "my_exp",
                str(data_dir),
                "future-splat-model",
                "--vis",
                "viewer",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-train future-splat-model" in log
        assert log.count("future-splat-model") == 1
        assert "--vis viewer" in log

    def test_train_errors_on_missing_explicit_config(self, tmp_path: Path) -> None:
        """Unknown config names should fail before reaching the trainer CLI."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_train_bad_config.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "splatfacto",
                "my_exp",
                str(data_dir),
                "does-not-exist",
                "--vis",
                "viewer",
            ],
            env_overrides,
        )
        assert result.returncode != 0
        assert "Config 'does-not-exist' not found" in result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-train" not in log

    def test_train_rejects_full_splatfacto_w(self, tmp_path: Path) -> None:
        """Full splatfacto-w needs a data layout mini-mesh does not produce."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_train_full_splatfactow.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "splatfacto-w",
                "my_exp",
                str(data_dir),
                "splatfacto-w",
            ],
            env_overrides,
        )
        assert result.returncode != 0
        assert "splatfacto-w requires the plugin's splatfactow_dataparser" in result.stderr
        assert "use --model splatfacto-w-light instead" in result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-train" not in log

    def test_train_splatfacto_w_light_uses_config(self, tmp_path: Path) -> None:
        """The supported W variant should use its checked-in mini-mesh config."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_train_splatfactow_light.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "splatfacto-w-light",
                "my_exp",
                str(data_dir),
                "splatfacto-w-light",
                "--vis",
                "viewer",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-train splatfacto-w-light" in log
        assert "--max-num-iterations 30001" in log
        assert "--steps-per-save 2000" in log
        assert "--vis viewer" in log
        assert "--viewer.quit-on-train-completion True" in log

    def test_train_viewer_disables_torch_compile_for_nerfstudio(self, tmp_path: Path) -> None:
        """Viewer mode should avoid TorchDynamo render-thread failures in Nerfstudio."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_train_viewer_compile.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)
        ns_train = bin_dir / "ns-train"
        ns_train.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    f'echo "$0 $*" >> "{log_path}"',
                    f'echo "TORCH_COMPILE_DISABLE=${{TORCH_COMPILE_DISABLE-}}" >> "{log_path}"',
                ]
            ),
            encoding="utf-8",
        )
        ns_train.chmod(0o755)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "splatfacto-mcmc",
                "my_exp",
                str(data_dir),
                "splatfacto-mcmc-short",
                "--vis",
                "viewer",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-train splatfacto-mcmc" in log
        assert "--vis viewer" in log
        assert "--viewer.quit-on-train-completion True" in log
        assert "TORCH_COMPILE_DISABLE=1" in log

    def test_train_viewer_respects_explicit_quit_on_completion(self, tmp_path: Path) -> None:
        """Explicit viewer lifetime settings should not be overwritten."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_train_viewer_quit_override.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "splatfacto-mcmc",
                "my_exp",
                str(data_dir),
                "splatfacto-mcmc-short",
                "--vis",
                "viewer",
                "--viewer.quit-on-train-completion",
                "False",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "--viewer.quit-on-train-completion False" in log
        assert "--viewer.quit-on-train-completion True" not in log

    def test_train_tensorboard_keeps_torch_compile_default(self, tmp_path: Path) -> None:
        """Non-viewer training should leave torch.compile behavior to upstream defaults."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_train_tensorboard_compile.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)
        ns_train = bin_dir / "ns-train"
        ns_train.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    f'echo "$0 $*" >> "{log_path}"',
                    f'echo "TORCH_COMPILE_DISABLE=${{TORCH_COMPILE_DISABLE-}}" >> "{log_path}"',
                ]
            ),
            encoding="utf-8",
        )
        ns_train.chmod(0o755)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "splatfacto-mcmc",
                "my_exp",
                str(data_dir),
                "splatfacto-mcmc-short",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-train splatfacto-mcmc" in log
        assert "TORCH_COMPILE_DISABLE=" in log
        assert "TORCH_COMPILE_DISABLE=1" not in log


class TestRunScript:
    """Tests for scripts/run.sh with stubbed pipeline tools."""

    def _make_pipeline_stubs(self, bin_dir: Path, log_path: Path) -> None:
        """Create stubs for external tools used by run.sh sub-scripts."""
        bin_dir.mkdir(parents=True, exist_ok=True)
        # Shared logging stub for all external tools.
        for name in [
            "nvidia-smi",
            "colmap",
            "sdf-train",
            "ns-train",
            "sdf-extract-mesh",
            "sdf-texture-mesh",
            "ns-export",
            "sdf-process-data",
        ]:
            script_path = bin_dir / name
            if name == "nvidia-smi":
                body = "\n".join(
                    [
                        "#!/usr/bin/env bash",
                        f'echo "$0 $*" >> "{log_path}"',
                        'echo "GPU 0"',
                    ]
                )
            elif name == "sdf-process-data":
                body = "\n".join(
                    [
                        "#!/usr/bin/env bash",
                        f'echo "$0 $*" >> "{log_path}"',
                        "out_dir=''",
                        "while [ $# -gt 0 ]; do",
                        '  if [ "$1" = "--output_dir" ] || [ "$1" = "--output-dir" ]; then',
                        '    out_dir="$2"',
                        "    shift 2",
                        "  else",
                        "    shift",
                        "  fi",
                        "done",
                        'if [ -n "$out_dir" ]; then',
                        '  mkdir -p "$out_dir"',
                        '  echo "{}" > "$out_dir/transforms.json"',
                        "fi",
                    ]
                )
            elif name in ("sdf-train", "ns-train"):
                body = "\n".join(
                    [
                        "#!/usr/bin/env bash",
                        f'echo "$0 $*" >> "{log_path}"',
                        'model="$1"',
                        "shift",
                        "out_dir=''",
                        "exp_name=''",
                        "while [ $# -gt 0 ]; do",
                        '  case "$1" in',
                        "    --output-dir|--output_dir)",
                        '      out_dir="$2"; shift 2 ;;',
                        "    --experiment-name)",
                        '      exp_name="$2"; shift 2 ;;',
                        "    *)",
                        "      shift ;;",
                        "  esac",
                        "done",
                        'if [ -n "$out_dir" ] && [ -n "$exp_name" ] && [ -n "$model" ]; then',
                        '  if [ "$model" = "splatfacto-mcmc" ]; then model="splatfacto"; fi',
                        '  exp_path="$out_dir/$exp_name/$model/run"',
                        '  mkdir -p "$exp_path"',
                        '  echo "dummy: true" > "$exp_path/config.yml"',
                        "fi",
                    ]
                )
            else:
                body = "\n".join(
                    [
                        "#!/usr/bin/env bash",
                        f'echo "$0 $*" >> "{log_path}"',
                    ]
                )
            script_path.write_text(body, encoding="utf-8")
            script_path.chmod(0o755)

    def test_run_script_sdf_pipeline_from_images(self, tmp_path: Path) -> None:
        """run.sh should orchestrate process/train/export for SDF models."""
        repo_root = Path(__file__).resolve().parents[1]
        scene_dir = tmp_path / "scene"
        images_dir = scene_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "0001.jpg").write_text("dummy", encoding="utf-8")

        log_path = tmp_path / "stub_run.log"
        bin_dir = tmp_path / "bin"
        self._make_pipeline_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        # Input path is the images dir; run.sh will treat its parent as input_dir.
        result = _run_script(
            repo_root,
            "scripts/run.sh",
            [
                str(images_dir),
                "process",
                "train",
                "--model",
                "neus-facto",
                "--config",
                "neus-facto-short",
                "export",
                "--mesh-only",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        # Process stage should call sdf-process-data and create transforms.json.
        assert "sdf-process-data images" in log
        assert (scene_dir / "transforms.json").is_file()

        # Train stage should call sdf-train with the model name.
        assert "sdf-train neus-facto" in log
        assert f"--data {scene_dir}" in log

        # Export stage with --mesh-only should call sdf-extract-mesh but not sdf-texture-mesh.
        assert "sdf-extract-mesh" in log
        assert "sdf-texture-mesh" not in log

    def test_run_script_retrains_existing_experiment_dir_without_config(
        self, tmp_path: Path
    ) -> None:
        """A partial experiment directory without config.yml should not skip train."""
        repo_root = Path(__file__).resolve().parents[1]
        scene_dir = tmp_path / "scene"
        images_dir = scene_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "0001.jpg").write_text("dummy", encoding="utf-8")
        exp_path = scene_dir / "train" / "be_prepared" / "neus-facto" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)

        log_path = tmp_path / "stub_run.log"
        bin_dir = tmp_path / "bin"
        self._make_pipeline_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/run.sh",
            [
                str(images_dir),
                "sfm",
                "--skip",
                "process",
                "--skip",
                "train",
                "--model",
                "neus-facto",
                "--name",
                "be_prepared",
                "--config",
                "neus-facto-short",
                "export",
                "--mesh-only",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "sdf-train neus-facto" in log
        assert (exp_path / "config.yml").is_file()

    def test_run_script_skips_train_when_config_exists(self, tmp_path: Path) -> None:
        """A completed experiment directory should not retrain unless overwritten."""
        repo_root = Path(__file__).resolve().parents[1]
        scene_dir = tmp_path / "scene"
        images_dir = scene_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "0001.jpg").write_text("dummy", encoding="utf-8")
        exp_path = scene_dir / "train" / "be_prepared" / "neus-facto" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub_run_skip_train.log"
        bin_dir = tmp_path / "bin"
        self._make_pipeline_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/run.sh",
            [
                str(images_dir),
                "sfm",
                "--skip",
                "process",
                "--skip",
                "train",
                "--model",
                "neus-facto",
                "--name",
                "be_prepared",
                "--config",
                "neus-facto-short",
                "export",
                "--mesh-only",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "sdf-train neus-facto" not in log
        assert "sdf-extract-mesh" in log

    def test_run_script_exports_splatfacto_mcmc_from_nerfstudio_method_dir(
        self, tmp_path: Path
    ) -> None:
        """splatfacto-mcmc trains with that CLI name but writes under splatfacto/run."""
        repo_root = Path(__file__).resolve().parents[1]
        scene_dir = tmp_path / "scene"
        images_dir = scene_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "0001.jpg").write_text("dummy", encoding="utf-8")

        log_path = tmp_path / "stub_run_splatfacto_mcmc.log"
        bin_dir = tmp_path / "bin"
        self._make_pipeline_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/run.sh",
            [
                str(images_dir),
                "sfm",
                "--skip",
                "process",
                "--skip",
                "train",
                "--model",
                "splatfacto-mcmc",
                "--name",
                "firebrigade",
                "--config",
                "splatfacto-mcmc-short",
                "export",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        exp_path = scene_dir / "train" / "firebrigade" / "splatfacto" / "run"
        assert (exp_path / "config.yml").is_file()

        log = log_path.read_text(encoding="utf-8")
        assert "ns-train splatfacto-mcmc" in log
        assert f"--load-config {exp_path / 'config.yml'}" in log
        assert "ns-export gaussian-splat" in log

    def test_run_script_skips_splatfacto_mcmc_when_method_dir_config_exists(
        self, tmp_path: Path
    ) -> None:
        """Existing splatfacto/run config should satisfy a splatfacto-mcmc run."""
        repo_root = Path(__file__).resolve().parents[1]
        scene_dir = tmp_path / "scene"
        images_dir = scene_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "0001.jpg").write_text("dummy", encoding="utf-8")
        exp_path = scene_dir / "train" / "firebrigade" / "splatfacto" / "run"
        exp_path.mkdir(parents=True, exist_ok=True)
        (exp_path / "config.yml").write_text("dummy: true\n", encoding="utf-8")

        log_path = tmp_path / "stub_run_splatfacto_mcmc_skip.log"
        bin_dir = tmp_path / "bin"
        self._make_pipeline_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/run.sh",
            [
                str(images_dir),
                "sfm",
                "--skip",
                "process",
                "--skip",
                "train",
                "--model",
                "splatfacto-mcmc",
                "--name",
                "firebrigade",
                "--config",
                "splatfacto-mcmc-short",
                "export",
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        log = log_path.read_text(encoding="utf-8")
        assert "ns-train splatfacto-mcmc" not in log
        assert f"--load-config {exp_path / 'config.yml'}" in log

    def test_run_script_rejects_full_splatfacto_w_before_pipeline_stages(
        self, tmp_path: Path
    ) -> None:
        """The unsupported W variant should fail before video/SfM/process work starts."""
        repo_root = Path(__file__).resolve().parents[1]
        scene_dir = tmp_path / "scene"
        images_dir = scene_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "0001.jpg").write_text("dummy", encoding="utf-8")

        log_path = tmp_path / "stub_run_full_splatfactow.log"
        bin_dir = tmp_path / "bin"
        self._make_pipeline_stubs(bin_dir, log_path)

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        }

        result = _run_script(
            repo_root,
            "scripts/run.sh",
            [
                str(images_dir),
                "process",
                "train",
                "--model",
                "splatfacto-w",
                "export",
            ],
            env_overrides,
        )
        assert result.returncode != 0
        assert "splatfacto-w requires the plugin's splatfactow_dataparser" in result.stderr

        log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        assert "sdf-process-data" not in log
        assert "ns-train" not in log
