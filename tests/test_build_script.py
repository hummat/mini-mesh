"""Static checks for local dependency setup helper."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _write_direct_url_dist(
    path: Path, name: str, source_path: Path, direct_url: str | None = None
) -> None:
    """Create minimal importlib.metadata files for a path dependency."""
    dist_info = path / f"{name}-1.0.dist-info"
    dist_info.mkdir(parents=True)
    dist_info.joinpath("METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n",
        encoding="utf-8",
    )
    dist_info.joinpath("direct_url.json").write_text(
        direct_url if direct_url is not None else f'{{"url": "file://{source_path}"}}\n',
        encoding="utf-8",
    )


def _build_script_env(tmp_path: Path) -> dict[str, str]:
    """Environment that lets build.sh be sourced without touching real deps."""
    cuda_home = tmp_path / "cuda"
    cuda_home.joinpath("include").mkdir(parents=True)
    cuda_home.joinpath("include", "cuda_runtime.h").write_text("", encoding="utf-8")
    cuda_home.joinpath("lib64").mkdir()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_bin.joinpath("nvcc").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    fake_bin.joinpath("nvcc").chmod(0o755)

    return {
        **os.environ,
        "BUILD_SFM": "OFF",
        "INSTALL_PYTHON_DEPS": "OFF",
        "INSTALL_HLOC": "OFF",
        "CUDA_HOME": str(cuda_home),
        "CC": "cc",
        "CXX": "c++",
        "CUDAHOSTCXX": "c++",
        "TORCH_CUDA_ARCH_LIST": "8.9",
        "MAX_JOBS": "1",
        "MINI_MESH_LOCAL_PREFIX": str(tmp_path / "prefix"),
        "MINI_MESH_BUILD_ROOT": str(tmp_path / "build"),
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
    }


def test_build_shell_syntax() -> None:
    """The local setup helper should stay shell-parseable."""
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["bash", "-n", str(repo_root / "scripts" / "build.sh")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_env_shell_syntax() -> None:
    """The env bootstrap helper should stay shell-parseable."""
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["bash", "-n", str(repo_root / "scripts" / "env.sh")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_build_script_has_no_dead_shell_function_wrapper() -> None:
    """direnv exec only exports env vars, so build.sh must not depend on shell functions."""
    repo_root = Path(__file__).resolve().parents[1]
    text = repo_root.joinpath("scripts", "build.sh").read_text(encoding="utf-8")

    assert "cuda-build" not in text
    assert "declare -F" not in text


def test_python_package_matches_source_reports_corrupt_metadata(tmp_path: Path) -> None:
    """Bad direct_url.json should be an unexpected error, not a reinstall trigger."""
    repo_root = Path(__file__).resolve().parents[1]
    pythonpath = tmp_path / "pythonpath"
    _write_direct_url_dist(pythonpath, "brokenpkg", tmp_path, "{not-json")

    result = subprocess.run(
        [
            "bash",
            "-c",
            (
                "source scripts/build.sh >/dev/null; "
                "status=0; "
                'python_package_matches_source brokenpkg "$PWD" || status=$?; '
                "printf '%s' \"$status\""
            ),
        ],
        cwd=repo_root,
        env={**_build_script_env(tmp_path), "PYTHONPATH": str(pythonpath)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "2"
    assert "invalid direct_url.json for brokenpkg" in result.stderr


def test_install_cuda_package_stamp_skips_matching_clean_checkout(tmp_path: Path) -> None:
    """A matching stamp, package source, and clean git checkout should skip reinstall."""
    repo_root = Path(__file__).resolve().parents[1]
    build_root = tmp_path / "build"
    prefix = tmp_path / "prefix"
    source_path = build_root / "demo" / "bindings"
    source_path.mkdir(parents=True)
    source_path.joinpath("pyproject.toml").write_text(
        "[project]\nname = 'demopkg'\nversion = '1.0'\n", encoding="utf-8"
    )
    subprocess.run(["git", "init"], cwd=build_root / "demo", check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "add", "."], cwd=build_root / "demo", check=True, stdout=subprocess.PIPE)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=mini-mesh-test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "init",
        ],
        cwd=build_root / "demo",
        check=True,
        stdout=subprocess.PIPE,
    )
    ref = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=build_root / "demo", text=True
    ).strip()
    prefix.mkdir()
    prefix.joinpath(f".stamp-python-demo-{ref}").write_text("", encoding="utf-8")
    pythonpath = tmp_path / "pythonpath"
    _write_direct_url_dist(pythonpath, "demopkg", source_path)

    result = subprocess.run(
        [
            "bash",
            "-c",
            (
                "source scripts/build.sh >/dev/null; "
                "checkout_repo() { echo checkout-called; return 99; }; "
                'install_cuda_package demo demopkg unused-url demo "$DEMO_REF" bindings'
            ),
        ],
        cwd=repo_root,
        env={
            **_build_script_env(tmp_path),
            "MINI_MESH_BUILD_ROOT": str(build_root),
            "MINI_MESH_LOCAL_PREFIX": str(prefix),
            "PYTHONPATH": str(pythonpath),
            "DEMO_REF": ref,
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "checkout-called" not in result.stdout


def test_install_cuda_package_stamp_rebuilds_dirty_checkout(tmp_path: Path) -> None:
    """A stamp should not hide local edits in the CUDA package checkout."""
    repo_root = Path(__file__).resolve().parents[1]
    build_root = tmp_path / "build"
    prefix = tmp_path / "prefix"
    source_path = build_root / "demo" / "bindings"
    source_path.mkdir(parents=True)
    tracked_file = source_path / "pyproject.toml"
    tracked_file.write_text("[project]\nname = 'demopkg'\nversion = '1.0'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=build_root / "demo", check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "add", "."], cwd=build_root / "demo", check=True, stdout=subprocess.PIPE)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=mini-mesh-test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "init",
        ],
        cwd=build_root / "demo",
        check=True,
        stdout=subprocess.PIPE,
    )
    ref = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=build_root / "demo", text=True
    ).strip()
    tracked_file.write_text("[project]\nname = 'changed'\nversion = '1.0'\n", encoding="utf-8")
    prefix.mkdir()
    prefix.joinpath(f".stamp-python-demo-{ref}").write_text("", encoding="utf-8")
    pythonpath = tmp_path / "pythonpath"
    _write_direct_url_dist(pythonpath, "demopkg", source_path)

    result = subprocess.run(
        [
            "bash",
            "-c",
            (
                "source scripts/build.sh >/dev/null; "
                "checkout_repo() { echo checkout-called; return 99; }; "
                'install_cuda_package demo demopkg unused-url demo "$DEMO_REF" bindings'
            ),
        ],
        cwd=repo_root,
        env={
            **_build_script_env(tmp_path),
            "MINI_MESH_BUILD_ROOT": str(build_root),
            "MINI_MESH_LOCAL_PREFIX": str(prefix),
            "PYTHONPATH": str(pythonpath),
            "DEMO_REF": ref,
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    assert result.returncode == 99
    assert "checkout-called" in result.stdout
