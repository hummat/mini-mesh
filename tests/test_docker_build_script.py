"""Checks for the Docker image build wrapper."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_docker_build_shell_syntax() -> None:
    """The Docker build wrapper should stay shell-parseable."""
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["bash", "-n", str(repo_root / "docker" / "build.sh")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_local_build_passes_cmake_and_torch_cuda_arch_formats(tmp_path: Path) -> None:
    """Local builds need CMake/tiny-cuda-nn archs as 89 and PyTorch archs as 8.9."""
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_args = tmp_path / "docker-args.txt"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        f"#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > {docker_args}\n",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)

    result = subprocess.run(
        [
            "bash",
            str(repo_root / "docker" / "build.sh"),
            "local",
            "--cuda-arch",
            "89",
            "--max-jobs",
            "1",
        ],
        cwd=repo_root,
        env={**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    args = docker_args.read_text(encoding="utf-8").splitlines()
    assert "--build-arg" in args
    assert "CMAKE_CUDA_ARCHITECTURES=89" in args
    assert "TORCH_CUDA_ARCH_LIST=8.9" in args
    assert "TORCH_CUDA_ARCH_LIST=89" not in args


def test_local_build_accepts_torch_style_cuda_arch(tmp_path: Path) -> None:
    """Users may pass the PyTorch-style dotted arch manually or via env."""
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_args = tmp_path / "docker-args.txt"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        f"#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > {docker_args}\n",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)

    result = subprocess.run(
        [
            "bash",
            str(repo_root / "docker" / "build.sh"),
            "local",
            "--cuda-arch",
            "8.9",
            "--max-jobs",
            "1",
        ],
        cwd=repo_root,
        env={**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    args = docker_args.read_text(encoding="utf-8").splitlines()
    assert "CMAKE_CUDA_ARCHITECTURES=89" in args
    assert "TORCH_CUDA_ARCH_LIST=8.9" in args
