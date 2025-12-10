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

    def test_train_neus2_uses_neus2_backend_and_writes_mesh(self, tmp_path: Path) -> None:
        """NeuS2 models should call NeuS2 run.py and produce a mesh in the exp dir."""
        repo_root = Path(__file__).resolve().parents[1]
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Minimal transforms.json for converter.
        transforms = {
            "w": 512,
            "h": 512,
            "fl_x": 1000.0,
            "fl_y": 1000.0,
            "cx": 256.0,
            "cy": 256.0,
            "frames": [
                {
                    "file_path": "images/0000.png",
                    "transform_matrix": [
                        [1.0, 0.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                }
            ],
        }
        (data_dir / "transforms.json").write_text(
            __import__("json").dumps(transforms), encoding="utf-8"
        )

        log_path = tmp_path / "stub_train_neus2.log"
        bin_dir = tmp_path / "bin"
        self._make_train_stubs(bin_dir, log_path)

        # Stub NeuS2 run.py
        neus2_root = tmp_path / "neus2"
        scripts_dir = neus2_root / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        run_py = scripts_dir / "run.py"
        run_py.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "import argparse, os, pathlib, sys",
                    "p = argparse.ArgumentParser()",
                    "p.add_argument('--name', required=True)",
                    "p.add_argument('--scene')",
                    "p.add_argument('--network')",
                    "p.add_argument('--n_steps', type=int, default=100000)",
                    "args, _ = p.parse_known_args()",
                    "log_path = os.environ.get('NEUS2_TRAIN_LOG')",
                    "if log_path:",
                    "  with open(log_path, 'a', encoding='utf-8') as f:",
                    "    f.write(f\"run.py --name {args.name} --scene {args.scene}\\n\")",
                    "out_dir = pathlib.Path('output') / args.name / 'mesh'",
                    "out_dir.mkdir(parents=True, exist_ok=True)",
                    "mesh_path = out_dir / f\"{args.n_steps}.obj\"",
                    "mesh_path.write_text('obj', encoding='utf-8')",
                ]
            ),
            encoding="utf-8",
        )

        env_overrides = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "NEUS2_ROOT": str(neus2_root),
            "NEUS2_TRAIN_LOG": str(log_path),
        }

        result = _run_script(
            repo_root,
            "scripts/train.sh",
            [
                "neus2",
                "my_exp",
                str(data_dir),
            ],
            env_overrides,
        )
        assert result.returncode == 0, result.stderr

        # NeuS2 stub should have been invoked with a scene pointing to transform_neus2.json.
        log = log_path.read_text(encoding="utf-8")
        assert "run.py --name my_exp" in log
        assert "transform_neus2.json" in log

        exp_mesh = data_dir / "train" / "my_exp" / "neus2" / "mesh.obj"
        assert exp_mesh.is_file()


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
                        '  if [ \"$1\" = \"--output_dir\" ] || [ \"$1\" = \"--output-dir\" ]; then',
                        "    out_dir=\"$2\"",
                        "    shift 2",
                        "  else",
                        "    shift",
                        "  fi",
                        "done",
                        "if [ -n \"$out_dir\" ]; then",
                        "  mkdir -p \"$out_dir\"",
                        '  echo "{}" > \"$out_dir/transforms.json\"',
                        "fi",
                    ]
                )
            elif name == "sdf-train":
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
                        '  exp_path="$out_dir/$exp_name/$model"',
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
                "neus-facto-dev",
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
