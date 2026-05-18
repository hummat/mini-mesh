"""Regression tests for Docker image dependency wiring."""

from __future__ import annotations

from pathlib import Path


def _dockerfile_text() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / "docker" / "Dockerfile").read_text(encoding="utf-8")


class TestDockerfileCudaWheels:
    """Checks for CUDA extension wheel build/install ordering."""

    def test_buildkit_cache_mounts_are_enabled(self) -> None:
        """Heavy rebuilds should reuse compiler and pip caches across invalidated layers."""
        dockerfile = _dockerfile_text()

        assert dockerfile.startswith("# syntax=docker/dockerfile:1.7\n")
        assert dockerfile.count("target=/root/.cache/ccache,sharing=locked") >= 3
        assert dockerfile.count("target=/root/.cache/pip,sharing=locked") >= 6
        assert "ENV CCACHE_DIR=/root/.cache/ccache" in dockerfile
        assert dockerfile.count("-DCMAKE_C_COMPILER_LAUNCHER=ccache") == 3
        assert dockerfile.count("-DCMAKE_CXX_COMPILER_LAUNCHER=ccache") == 3

    def test_nvdiffrast_and_gsplat_are_built_as_pinned_wheels(self) -> None:
        """CUDA extensions should be built once in the builder stage."""
        dockerfile = _dockerfile_text()

        assert "ARG NVDIFFRAST_REF=253ac4fcea7de5f396371124af597e6cc957bfae" in dockerfile
        assert "ARG GSPLAT_VERSION=1.4.0" in dockerfile
        assert "git clone https://github.com/NVlabs/nvdiffrast.git" in dockerfile
        assert 'git checkout "${NVDIFFRAST_REF}"' in dockerfile
        assert "git clone https://github.com/nerfstudio-project/gsplat.git" in dockerfile
        assert 'git checkout "v${GSPLAT_VERSION}"' in dockerfile
        gsplat_checkout = dockerfile.index('git checkout "v${GSPLAT_VERSION}"')
        gsplat_submodules = dockerfile.index(
            "git submodule update --init --recursive",
            gsplat_checkout,
        )
        gsplat_wheel = dockerfile.index(
            "pip wheel . --no-build-isolation --no-deps -w /workspace/gsplat-wheels",
            gsplat_submodules,
        )
        assert (
            'TCNN_CUDA_ARCHITECTURES="${CMAKE_CUDA_ARCHITECTURES}" MAX_JOBS=${MAX_JOBS} pip wheel'
            in dockerfile
        )
        assert (
            'TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST}" MAX_JOBS=${MAX_JOBS} pip wheel '
            ". --no-build-isolation --no-deps -w /workspace &&" in dockerfile
        )
        assert (
            "pip wheel . --no-build-isolation --no-deps -w /workspace/gsplat-wheels" in dockerfile
        )
        assert gsplat_submodules < gsplat_wheel

    def test_runtime_installs_cuda_wheels_before_dependents(self) -> None:
        """nvdiffrast must precede sdfstudio and gsplat must precede nerfstudio."""
        dockerfile = _dockerfile_text()

        nvdiffrast_install = dockerfile.index(
            "pip install --no-cache-dir --no-deps -c /tmp/constraints.txt /tmp/tinycudann*.whl"
        )
        sdfstudio_install = dockerfile.index(
            '"sdfstudio[cuda,export] @ git+https://github.com/hummat/sdfstudio.git@v0.8.0"'
        )
        gsplat_install = dockerfile.index(
            "pip install --no-cache-dir --no-deps -c /tmp/constraints.txt "
            "/tmp/gsplat-wheels/gsplat*.whl"
        )
        nerfstudio_install = dockerfile.index(
            "git+https://github.com/hummat/nerfstudio.git@55a1f83025bb28cbf792760c9b79f9eb22c3a2e4"
        )

        assert nvdiffrast_install < sdfstudio_install
        assert gsplat_install < nerfstudio_install

    def test_constraints_generation_fails_closed(self) -> None:
        """The torch constraints file must not become silently empty."""
        dockerfile = _dockerfile_text()

        assert 'SHELL ["/bin/bash", "-eo", "pipefail", "-c"]' in dockerfile
        constraints = dockerfile.index("> /tmp/constraints.txt")
        assert "test -s /tmp/constraints.txt" in dockerfile[constraints:]

    def test_runtime_replaces_base_image_ninja_metadata(self) -> None:
        """The PyTorch base image ninja wheel fails pip check on Linux."""
        dockerfile = _dockerfile_text()

        core_deps = dockerfile.index("# Core Python deps that must not disturb the torch stack")
        assert "ninja==1.13.0" in dockerfile[core_deps:]

    def test_runtime_pins_pillow_below_nerfstudio_setimage_break(self) -> None:
        """Pillow 12.2 changed a low-level encoder API used by this Nerfstudio pin."""
        dockerfile = _dockerfile_text()

        constraints = dockerfile.index("> /tmp/constraints.txt")
        core_deps = dockerfile.index("# Core Python deps that must not disturb the torch stack")

        assert "ARG PILLOW_VERSION=12.1.0" in dockerfile
        assert (
            "printf 'pillow==%s\\n' \"${PILLOW_VERSION}\" >> /tmp/constraints.txt"
            in dockerfile[constraints:]
        )
        assert '"pillow==${PILLOW_VERSION}"' in dockerfile[core_deps:]

    def test_runtime_asserts_cuda_wheel_presence(self) -> None:
        """Missing copied wheels should fail before pip sees an unresolved glob."""
        dockerfile = _dockerfile_text()

        assert "ls /tmp/tinycudann*.whl >/dev/null" in dockerfile
        assert "ls /tmp/nvdiffrast*.whl >/dev/null" in dockerfile
        gsplat_gate = dockerfile.index('if [ "$INSTALL_OPTIONAL_DEPS" = "ON" ]; then')
        gsplat_assert = dockerfile.index("ls /tmp/gsplat-wheels/gsplat*.whl >/dev/null")
        gsplat_install = dockerfile.index("/tmp/gsplat-wheels/gsplat*.whl", gsplat_assert)

        assert gsplat_gate < gsplat_assert < gsplat_install

    def test_optional_gsplat_build_is_gated(self) -> None:
        """INSTALL_OPTIONAL_DEPS=OFF should skip the slow gsplat builder-stage compile."""
        dockerfile = _dockerfile_text()

        gsplat_clone = dockerfile.index(
            "git clone https://github.com/nerfstudio-project/gsplat.git"
        )
        gsplat_gate = dockerfile.rindex(
            'if [ "$INSTALL_OPTIONAL_DEPS" = "ON" ]; then', 0, gsplat_clone
        )
        gsplat_copy = dockerfile.index(
            "COPY --from=builder /workspace/gsplat-wheels /tmp/gsplat-wheels"
        )
        gsplat_install = dockerfile.index("/tmp/gsplat-wheels/gsplat*.whl")

        assert "ARG INSTALL_OPTIONAL_DEPS=ON" in dockerfile[:gsplat_clone]
        assert gsplat_gate < gsplat_clone
        assert gsplat_copy < gsplat_install

    def test_core_runtime_layers_precede_optional_runtime_layers(self) -> None:
        """Slim/full builds should share the core Python dependency layer."""
        dockerfile = _dockerfile_text()

        sdfstudio_install = dockerfile.index(
            '"sdfstudio[cuda,export] @ git+https://github.com/hummat/sdfstudio.git@v0.8.0"'
        )
        optional_build_tools = dockerfile.index(
            "# Build tools only if optional deps enabled",
            sdfstudio_install,
        )
        gsplat_copy = dockerfile.index(
            "COPY --from=builder /workspace/gsplat-wheels /tmp/gsplat-wheels"
        )
        rembg_install = dockerfile.index('"rembg[gpu,cli]==2.0.69"')

        assert sdfstudio_install < optional_build_tools < gsplat_copy < rembg_install

    def test_rembg_is_pinned_below_numpy_two_cutover(self) -> None:
        """Newer rembg releases require numpy>=2.3, which conflicts with nerfstudio."""
        dockerfile = _dockerfile_text()

        assert '"rembg[gpu,cli]==2.0.69"' in dockerfile

    def test_optional_deps_arg_does_not_invalidate_core_layers(self) -> None:
        """Switching slim/full should not rebuild mandatory CUDA wheels or core runtime deps."""
        dockerfile = _dockerfile_text()

        builder_optional_arg = dockerfile.index(
            "ARG INSTALL_OPTIONAL_DEPS=ON",
            dockerfile.index("# gsplat wheel"),
        )
        tinycudann_build = dockerfile.index("# tiny-cuda-nn wheel")
        nvdiffrast_build = dockerfile.index("# nvdiffrast wheel")
        gsplat_build = dockerfile.index("# gsplat wheel")
        runtime_optional_arg = dockerfile.index(
            "ARG INSTALL_OPTIONAL_DEPS=ON",
            dockerfile.index("# Build tools only if optional deps enabled"),
        )
        runtime_apt = dockerfile.index("# Core COLMAP/GLOMAP runtime deps")
        sdfstudio_install = dockerfile.index(
            '"sdfstudio[cuda,export] @ git+https://github.com/hummat/sdfstudio.git@v0.8.0"'
        )
        optional_build_tools = dockerfile.index("# Build tools only if optional deps enabled")

        assert tinycudann_build < nvdiffrast_build < gsplat_build < builder_optional_arg
        assert runtime_apt < sdfstudio_install < optional_build_tools < runtime_optional_arg

    def test_cuda_arch_lists_are_quoted_in_shell_commands(self) -> None:
        """CMake/tiny-cuda-nn and PyTorch extensions use different arch formats."""
        dockerfile = _dockerfile_text()

        assert "ARG CMAKE_CUDA_ARCHITECTURES=75;80;86;89" in dockerfile
        assert "ARG TORCH_CUDA_ARCH_LIST=7.5;8.0;8.6;8.9+PTX" in dockerfile
        assert '-DCMAKE_CUDA_ARCHITECTURES="${CMAKE_CUDA_ARCHITECTURES}"' in dockerfile
        assert 'TCNN_CUDA_ARCHITECTURES="${CMAKE_CUDA_ARCHITECTURES}"' in dockerfile
        assert (
            'TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST}" MAX_JOBS=${MAX_JOBS} pip wheel'
            in dockerfile
        )

    def test_runtime_image_contains_late_copy_of_app_scripts(self) -> None:
        """Image mode should have app files without invalidating heavy dependency layers."""
        dockerfile = _dockerfile_text()

        vggsfm_install = dockerfile.index("git+https://github.com/hummat/vggsfm.git")
        scripts_copy = dockerfile.index("COPY scripts /opt/mini-mesh/scripts")
        config_copy = dockerfile.index("COPY config /opt/mini-mesh/config")
        cmd = dockerfile.index('CMD ["bash"]')

        assert vggsfm_install < scripts_copy < config_copy < cmd
