"""Tests for Docker runtime wrappers."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _write_fake_docker(bin_dir: Path, log_path: Path, local_exists: bool = False) -> None:
    """Create a docker stub that supports image inspect and records docker run."""
    inspect_status = "0" if local_exists else "1"
    script = f"""#!/usr/bin/env bash
if [[ "$1" = "image" && "$2" = "inspect" ]]; then
  exit {inspect_status}
fi
printf '%s\\n' "$@" > "{log_path}"
"""
    docker = bin_dir / "docker"
    docker.write_text(script, encoding="utf-8")
    docker.chmod(0o755)


def _write_fake_xhost(bin_dir: Path, log_path: Path) -> None:
    """Create an xhost stub that records allow/revoke calls."""
    xhost = bin_dir / "xhost"
    xhost.write_text(
        f'#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "{log_path}"\n',
        encoding="utf-8",
    )
    xhost.chmod(0o755)


def _run_wrapper(
    repo_root: Path,
    script_name: str,
    args: list[str],
    tmp_path: Path,
    *,
    local_exists: bool = False,
    env_overrides: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], list[str], str]:
    """Run a Docker wrapper with fake docker/xhost binaries."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker-args.txt"
    xhost_log = tmp_path / "xhost.log"
    _write_fake_docker(fake_bin, docker_log, local_exists=local_exists)
    _write_fake_xhost(fake_bin, xhost_log)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "DISPLAY": ":99",
        "MINI_MESH_DOCKER_X11": "off",
        "MINI_MESH_DOCKER_TTY": "off",
    }
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        ["bash", str(repo_root / "docker" / script_name), *args],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    docker_args = docker_log.read_text(encoding="utf-8").splitlines() if docker_log.exists() else []
    xhost_calls = xhost_log.read_text(encoding="utf-8") if xhost_log.exists() else ""
    return result, docker_args, xhost_calls


def test_run_wrapper_uses_repo_scripts_and_normalizes_relative_input(tmp_path: Path) -> None:
    """docker/run.sh should keep the checkout-mounted script contract by default."""
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = tmp_path / "data with spaces"
    data_dir.mkdir()
    input_path = data_dir / "input.mp4"
    input_path.write_bytes(b"")
    relative_input = os.path.relpath(input_path, repo_root)

    result, docker_args, _ = _run_wrapper(
        repo_root,
        "run.sh",
        [relative_input, "video", "--fps", "1"],
        tmp_path,
        env_overrides={"MINI_MESH_IMAGE": "hummat/mini-mesh:test"},
    )

    assert result.returncode == 0, result.stderr
    assert docker_args[:2] == ["run", "--rm"]
    assert "hummat/mini-mesh:test" in docker_args
    assert f"{data_dir.resolve()}:/data" in docker_args
    assert f"{repo_root}:/app" in docker_args
    assert "/app/scripts/run.sh" in docker_args
    assert f"/data/{input_path.name}" in docker_args
    assert "video" in docker_args
    assert "--fps" in docker_args
    assert "1" in docker_args
    assert "-it" not in docker_args


def test_run_wrapper_can_use_baked_image_scripts(tmp_path: Path) -> None:
    """Image app mode should not bind-mount the checkout."""
    repo_root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"")

    result, docker_args, _ = _run_wrapper(
        repo_root,
        "run.sh",
        [str(input_path), "--help"],
        tmp_path,
        env_overrides={
            "MINI_MESH_IMAGE": "hummat/mini-mesh:test",
            "MINI_MESH_DOCKER_APP": "image",
        },
    )

    assert result.returncode == 0, result.stderr
    assert f"{repo_root}:/app" not in docker_args
    assert "/opt/mini-mesh/scripts/run.sh" in docker_args


def test_wrapper_auto_selects_local_image_when_present(tmp_path: Path) -> None:
    """Local builds should be preferred when no explicit image is set."""
    repo_root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"")

    result, docker_args, _ = _run_wrapper(
        repo_root,
        "run.sh",
        [str(input_path), "--help"],
        tmp_path,
        local_exists=True,
    )

    assert result.returncode == 0, result.stderr
    assert "hummat/mini-mesh:local" in docker_args
    assert "Using local Docker image: hummat/mini-mesh:local" in result.stderr


def test_explicit_image_overrides_local_auto_selection(tmp_path: Path) -> None:
    """MINI_MESH_IMAGE should take precedence over local image detection."""
    repo_root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"")

    result, docker_args, _ = _run_wrapper(
        repo_root,
        "run.sh",
        [str(input_path), "--help"],
        tmp_path,
        local_exists=True,
        env_overrides={"MINI_MESH_IMAGE": "example/image:tag"},
    )

    assert result.returncode == 0, result.stderr
    assert "example/image:tag" in docker_args
    assert "hummat/mini-mesh:local" not in docker_args


def test_x11_auto_mode_allows_and_revokes_access(tmp_path: Path) -> None:
    """X11 auto mode should clean up the xhost permission it adds."""
    repo_root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"")

    result, docker_args, xhost_calls = _run_wrapper(
        repo_root,
        "run.sh",
        [str(input_path), "--help"],
        tmp_path,
        env_overrides={
            "MINI_MESH_IMAGE": "hummat/mini-mesh:test",
            "MINI_MESH_DOCKER_X11": "auto",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "-e" in docker_args
    assert "DISPLAY=:99" in docker_args
    assert "/tmp/.X11-unix:/tmp/.X11-unix" in docker_args
    assert "+local:" in xhost_calls
    assert "-local:" in xhost_calls


def test_start_wrapper_passes_optional_command(tmp_path: Path) -> None:
    """docker/start.sh should allow a command after the input path."""
    repo_root = Path(__file__).resolve().parents[1]
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"")

    result, docker_args, _ = _run_wrapper(
        repo_root,
        "start.sh",
        [str(input_path), "python", "-c", "print('ok')"],
        tmp_path,
        env_overrides={"MINI_MESH_IMAGE": "hummat/mini-mesh:test"},
    )

    assert result.returncode == 0, result.stderr
    assert "python" in docker_args
    assert "-c" in docker_args
    assert "print('ok')" in docker_args
