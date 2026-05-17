#!/usr/bin/env bash

mini_mesh_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mini_mesh_repo_root="$(dirname "$mini_mesh_script_dir")"
mini_mesh_local_prefix_was_set=OFF
if [[ -n "${MINI_MESH_LOCAL_PREFIX+x}" ]]; then
  mini_mesh_local_prefix_was_set=ON
fi
mini_mesh_local_prefix="${MINI_MESH_LOCAL_PREFIX:-$mini_mesh_repo_root/.local/mini-mesh}"
mini_mesh_venv_bin="${MINI_MESH_VENV_BIN:-$mini_mesh_repo_root/.venv/bin}"

if [[ -d "$mini_mesh_venv_bin" ]]; then
  export PATH="$mini_mesh_venv_bin${PATH:+:$PATH}"
fi

if [[ -d "$mini_mesh_local_prefix" ]]; then
  export PATH="$mini_mesh_local_prefix/bin${PATH:+:$PATH}"
  export LD_LIBRARY_PATH="$mini_mesh_local_prefix/lib:$mini_mesh_local_prefix/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export CMAKE_PREFIX_PATH="$mini_mesh_local_prefix${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
elif [[ "$mini_mesh_local_prefix_was_set" = ON ]]; then
  echo "WARNING: MINI_MESH_LOCAL_PREFIX is set but missing: $mini_mesh_local_prefix" >&2
  echo "         Run 'make build' or unset MINI_MESH_LOCAL_PREFIX." >&2
fi

unset mini_mesh_script_dir mini_mesh_repo_root mini_mesh_local_prefix_was_set mini_mesh_local_prefix mini_mesh_venv_bin
