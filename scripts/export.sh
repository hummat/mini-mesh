#!/usr/bin/env bash
set -e

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/env.sh
source "$script_dir/env.sh"
# shellcheck source=config/defaults.sh
if ! source "$script_dir/../config/defaults.sh"; then
  echo "[ERROR]: Failed to source config/defaults.sh"
  exit 1
fi
if [ -z "${EXPORT_DEFAULTS+x}" ]; then
  echo "[ERROR]: EXPORT_DEFAULTS not defined in config/defaults.sh"
  exit 1
fi

verbose=false

# Helper to check if enough arguments remain for a flag
require_args() {
  local flag="$1"
  local needed="$2"
  local have="$3"
  if [ "$have" -lt "$needed" ]; then
    echo "[ERROR]: $flag requires $needed value(s)"
    exit 1
  fi
}

# Run a command, logging it first if verbose mode is enabled
run_cmd() {
  if [ "$verbose" = true ] || [ "${VERBOSE:-}" = true ]; then
    echo "[CMD]: $*"
  fi
  "$@"
}

experiment_model_name() {
  local path="$1"
  local name
  name="$(basename "$path")"
  if [ "$name" = run ]; then
    name="$(basename "$(dirname "$path")")"
  fi
  echo "$name"
}

nerfstudio_python() {
  # scripts/env.sh prepends $repo/.venv/bin to PATH whenever that directory exists,
  # so `python` may be a dev venv interpreter with no torch while the pipeline itself
  # runs under another one. Probe candidates for torch rather than trusting the name,
  # and check for the module without importing it so this stays cheap.
  local probe candidate entry shebang first
  probe='import importlib.util as u, sys; sys.exit(0 if u.find_spec("torch") else 1)'

  # A console script's shebang names the interpreter it was installed for, which is
  # the one that owns nerfstudio.
  entry="$(command -v ns-export 2>/dev/null)" || entry=""
  shebang=""
  if [ -n "$entry" ]; then
    first="$(head -n 1 "$entry" 2>/dev/null)"
    case "$first" in
      '#!'*)
        first="${first#\#!}"
        shebang="${first%% *}"
        if [ "$(basename "$shebang")" = env ]; then
          first="${first#* }"
          shebang="${first%% *}"
        fi
        ;;
    esac
  fi

  for candidate in python python3 "$shebang"; do
    [ -n "$candidate" ] || continue
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -c "$probe" >/dev/null 2>&1; then
      echo "$candidate"
      return
    fi
  done

  # Nothing claims torch: keep the historical call so the failure is the script's own.
  echo python
}

clean_splat_output() {
  local output_path="$1"
  if [ "$clean_splat" != true ] || [ ! -f "$output_path" ]; then
    return 0
  fi
  run_cmd "$(nerfstudio_python)" "$script_dir/clean_splat.py" "$output_path" "${clean_splat_args[@]}"
}

nerf_export_output_path() {
  local exp_path="$1"
  local model_name="$2"
  local method="$3"

  if [[ "$model_name" == *splat* ]]; then
    echo "$exp_path/splat.ply"
  elif [ "$method" = pointcloud ]; then
    echo "$exp_path/point_cloud.ply"
  elif [ "$method" = tsdf ]; then
    echo "$exp_path/tsdf_mesh.ply"
  else
    echo "$exp_path/poisson_mesh.ply"
  fi
}

orbit_frames_output_path() {
  local exp_path="$1"
  echo "$exp_path/orbit_frames"
}

infer_data_path() {
  local candidate="$1"

  while [ "$candidate" != "/" ] && [ -n "$candidate" ]; do
    if [ -f "$candidate/transforms.json" ]; then
      echo "$candidate"
      return 0
    fi
    candidate="$(dirname "$candidate")"
  done
}

should_run_export() {
  local output_path="$1"
  if [ -f "$output_path" ] && [ "${overwrite:-false}" != true ]; then
    echo "[INFO]: Export output $output_path already exists; skipping (use --overwrite to rerun)"
    return 1
  fi
  return 0
}

should_run_export_dir() {
  local output_path="$1"
  local existing_output

  if [ -d "$output_path" ]; then
    existing_output="$(find "$output_path" -mindepth 1 -maxdepth 1 -print -quit)"
    if [ -n "$existing_output" ] && [ "${overwrite:-false}" != true ]; then
      echo "[INFO]: Export output $output_path already exists; skipping (use --overwrite to rerun)"
      return 1
    fi
  fi
  return 0
}

run_nerfstudio_orbit_frames_export() {
  local exp_path="$1"
  local output_path
  output_path="$(orbit_frames_output_path "$exp_path")"

  if should_run_export_dir "$output_path"; then
    if [ -n "$data_path" ]; then
      run_cmd python "$script_dir/render_nerfstudio_orbit.py" \
        --load-config "$exp_path/config.yml" \
        --output-path "$output_path" \
        --data "$data_path" \
        --seconds 30 \
        --frame-rate 1
    else
      run_cmd ns-render spiral \
        --load-config "$exp_path/config.yml" \
        --output-path "$output_path" \
        --output-format images \
        --seconds 30 \
        --frame-rate 1
    fi
  fi
}

run_sdf_orbit_frames_export() {
  local exp_path="$1"
  local output_path
  local sdf_render_args=()
  output_path="$(orbit_frames_output_path "$exp_path")"

  if [ -n "$data_path" ]; then
    sdf_render_args+=("--data" "$data_path")
  fi

  if should_run_export_dir "$output_path"; then
    run_cmd sdf-render \
      --load-config "$exp_path/config.yml" \
      --traj spiral \
      --output-path "$output_path" \
      --output-format images \
      "${sdf_render_args[@]}"
  fi
}

validate_export_method() {
  local method_name="$1"
  case "$method_name" in
    poisson|tsdf|pointcloud|orbit-frames) ;;
    "") echo "[ERROR]: --method requires at least one value"; exit 1 ;;
    *) echo "[ERROR]: --method must be one of: poisson, tsdf, pointcloud, orbit-frames"; exit 1 ;;
  esac
}

add_export_methods() {
  local raw="$1"
  local method_name

  method_requested=true
  while true; do
    method_name="${raw%%,*}"
    validate_export_method "$method_name"
    if [ "$method_name" = orbit-frames ]; then
      orbit_frames_requested=true
    else
      nerf_methods+=("$method_name")
    fi
    if [[ "$raw" != *,* ]]; then
      break
    fi
    raw="${raw#*,}"
  done
}

function show_help {
  echo "Usage: export.sh <exp_path> [export_args...]"
  echo
  echo "This script automates the export process for the pipeline."
  echo "It loads the experiment configuration and executes mesh extraction and texturing."
  echo
  echo "Arguments:"
  echo "  <exp_path>                Path to the experiment directory (must contain config.yml)"
  echo "  [export_args...]          Additional options for export:"
  echo "                              --resolution <int>                        Marching cubes resolution (default: 1024)"
  echo "                              --bounding-box-min <float float float>    Minimum bounding box (default: -1 -1 -1)"
  echo "                              --bounding-box-max <float float float>    Maximum bounding box (default: 1 1 1)"
  echo "                              --marching-cube-threshold <float>         Isosurface threshold (default: 0.0)"
  echo "                              --px-per-uv-triangle <int>                Pixels per UV triangle (default: 4)"
  echo "                              --num-pixels-per-side <int>               Pixels per side (default: 2048)"
  echo "                              --target-num-faces <int>                  Target number of faces (default: 50000)"
  echo "                              --use-average-appearance-embedding <bool> Use average appearance embedding (default: True)"
  echo "                              --num-directions <int>                    Viewing directions for texturing (default: 1)"
  echo "                              --texture-method <string>                 Texturing method: legacy, cpu, gpu, open3d (default: gpu)"
  echo "                              --pad-px <int>                            Chart edge dilation pixels (default: 32)"
  echo "                              --normal-map-convention <string>          Normal map convention: opengl, directx (default: opengl)"
  echo "                              --appearance-mode <mean|index>            Appearance bake mode for splatfacto-w-light (default: mean)"
  echo "                              --appearance-idx <int>                    Camera index for appearance embedding"
  echo "                              --method <string[,string...]>             Export method(s): poisson, tsdf, pointcloud, orbit-frames (default: poisson for NeRF)"
  echo "                              --obb-center <float float float>          Center of oriented bounding-box (default: 0 0 0)"
  echo "                              --obb-rotation <float float float>        Rotation of oriented bounding-box (default: 0 0 0)"
  echo "                              --obb-scale <float float float>           Scale of oriented bounding-box (default: 1 1 1)"
  echo "                              --downscale-factor <int>                  Image downscale factor for TSDF extraction (default: 2)"
  echo "                              --no-clean                                Skip splat cleanup after export"
  echo "                              --clean-opacity <float>                   Drop Gaussians below this opacity (default: 0.05)"
  echo "                              --clean-max-scale-quantile <float>        Drop Gaussians above this size quantile (default: off)"
  echo "                              --clean-max-anisotropy <float>            Drop Gaussians above this axis ratio (default: off)"
  echo "                              --clean-sor                               Statistical outlier removal on centres (needs scipy)"
  echo "                              --clean-sor-neighbours <int>              Neighbours per outlier test (default: 16)"
  echo "                              --clean-sor-std-ratio <float>             Outlier cut in std devs (default: 2.0)"
  echo "                              --mesh-only                               Extract mesh but skip texturing (SDF only)"
  echo "                              --texture-only                            Texture existing mesh, skip extraction (SDF only)"
  echo "                              --input-mesh-filename <path>              Custom mesh file for texturing (requires --texture-only)"
  echo "                              --overwrite                               Overwrite existing files"
  echo "                              --verbose                                 Enable verbose output"
  echo "                              --data <path>                             Override data path (for Docker/local portability)"
  echo "                              --help                                    Show this help message"
  echo
  exit 0
}

if [ "$#" -lt 1 ]; then
  show_help
fi

for arg in "$@"; do
  if [ "$arg" == "--help" ]; then
    show_help
  fi
done

exp_path="$1"
shift
export_args=("$@")
extract_mesh_args=()
texture_mesh_args=("${EXPORT_DEFAULTS[@]}")
nerf_args=()
nerf_tsdf_args=()
splatfactow_args=()
clean_splat_args=()
clean_splat=true
nerf_methods=()
method_requested=false
orbit_frames_requested=false
nerf_obb_center=(0 0 0)
nerf_obb_rotation=(0 0 0)
nerf_obb_scale=(1 1 1)
mesh_only=false
texture_only=false
input_mesh_filename=""
data_path=""

i=0
while [ $i -lt ${#export_args[@]} ]; do
  remaining=$((${#export_args[@]} - i - 1))
  case "${export_args[$i]}" in
    --resolution|--marching-cube-threshold)
      require_args "${export_args[$i]}" 1 "$remaining"
      extract_mesh_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      i=$((i+2))
      ;;
    --downscale-factor)
      require_args "${export_args[$i]}" 1 "$remaining"
      nerf_tsdf_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      i=$((i+2))
      ;;
    --bounding-box-min|--bounding-box-max)
      require_args "${export_args[$i]}" 3 "$remaining"
      extract_mesh_args+=("${export_args[$i]}" "${export_args[$((i+1))]}" "${export_args[$((i+2))]}" "${export_args[$((i+3))]}")
      nerf_tsdf_args+=("${export_args[$i]}" "${export_args[$((i+1))]}" "${export_args[$((i+2))]}" "${export_args[$((i+3))]}")
      i=$((i+4))
      ;;
    --px-per-uv-triangle|--num-pixels-per-side|--target-num-faces|--num-directions|--pad-px)
      require_args "${export_args[$i]}" 1 "$remaining"
      texture_mesh_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      nerf_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      i=$((i+2))
      ;;
    --appearance-idx|--appearance-index)
      require_args "${export_args[$i]}" 1 "$remaining"
      texture_mesh_args+=("--appearance-idx" "${export_args[$((i+1))]}")
      splatfactow_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      i=$((i+2))
      ;;
    --appearance-mode)
      require_args "${export_args[$i]}" 1 "$remaining"
      val="${export_args[$((i+1))]}"
      case "$val" in
        mean|index) ;;
        *) echo "[ERROR]: --appearance-mode must be one of: mean, index"; exit 1 ;;
      esac
      splatfactow_args+=("${export_args[$i]}" "$val")
      i=$((i+2))
      ;;
    --normal-map-convention)
      require_args "${export_args[$i]}" 1 "$remaining"
      val="${export_args[$((i+1))]}"
      case "$val" in
        opengl|directx) ;;
        *) echo "[ERROR]: --normal-map-convention must be one of: opengl, directx"; exit 1 ;;
      esac
      texture_mesh_args+=("${export_args[$i]}" "$val")
      i=$((i+2))
      ;;
    --use-average-appearance-embedding)
      require_args "${export_args[$i]}" 1 "$remaining"
      val="${export_args[$((i+1))]}"
      case "$val" in
        True|False|true|false) ;;
        *) echo "[ERROR]: --use-average-appearance-embedding must be True or False"; exit 1 ;;
      esac
      # Remove default value to avoid duplicate
      local_texture_args=()
      for ((j=0; j<${#texture_mesh_args[@]}; j++)); do
        if [ "${texture_mesh_args[$j]}" = "--use-average-appearance-embedding" ]; then
          j=$((j+1))  # Skip the value too
        else
          local_texture_args+=("${texture_mesh_args[$j]}")
        fi
      done
      texture_mesh_args=("${local_texture_args[@]}" "${export_args[$i]}" "$val")
      i=$((i+2))
      ;;
    --texture-method)
      require_args "${export_args[$i]}" 1 "$remaining"
      val="${export_args[$((i+1))]}"
      case "$val" in
        legacy|cpu|gpu|open3d) ;;
        *) echo "[ERROR]: --texture-method must be one of: legacy, cpu, gpu, open3d"; exit 1 ;;
      esac
      texture_mesh_args+=("--method" "$val")
      i=$((i+2))
      ;;
    --method)
      require_args "${export_args[$i]}" 1 "$remaining"
      val="${export_args[$((i+1))]}"
      add_export_methods "$val"
      i=$((i+2))
      ;;
    --obb-center|--obb-rotation|--obb-scale)
      require_args "${export_args[$i]}" 3 "$remaining"
      case "${export_args[$i]}" in
        --obb-center)
          nerf_obb_center=("${export_args[$((i+1))]}" "${export_args[$((i+2))]}" "${export_args[$((i+3))]}")
          ;;
        --obb-rotation)
          nerf_obb_rotation=("${export_args[$((i+1))]}" "${export_args[$((i+2))]}" "${export_args[$((i+3))]}")
          ;;
        --obb-scale)
          nerf_obb_scale=("${export_args[$((i+1))]}" "${export_args[$((i+2))]}" "${export_args[$((i+3))]}")
          ;;
      esac
      i=$((i+4))
      ;;
    --no-clean)
      clean_splat=false
      i=$((i+1))
      ;;
    --clean-opacity|--clean-max-scale-quantile|--clean-max-anisotropy|--clean-sor-neighbours|--clean-sor-std-ratio)
      require_args "${export_args[$i]}" 1 "$remaining"
      clean_splat_args+=("${export_args[$i]/--clean-/--}" "${export_args[$((i+1))]}")
      i=$((i+2))
      ;;
    --clean-sor)
      clean_splat_args+=("--sor")
      i=$((i+1))
      ;;
    --mesh-only)
      mesh_only=true
      i=$((i+1))
      ;;
    --texture-only)
      texture_only=true
      i=$((i+1))
      ;;
    --input-mesh-filename)
      require_args "${export_args[$i]}" 1 "$remaining"
      input_mesh_filename="${export_args[$((i+1))]}"
      i=$((i+2))
      ;;
    --overwrite)
      overwrite=true
      i=$((i+1))
      ;;
    --verbose)
      verbose=true
      i=$((i+1))
      ;;
    --data)
      require_args "${export_args[$i]}" 1 "$remaining"
      data_path="${export_args[$((i+1))]}"
      extract_mesh_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      texture_mesh_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      i=$((i+2))
      ;;
    *)
      echo "[ERROR]: Unknown argument ${export_args[$i]}"
      show_help
      ;;
  esac
done

if [ -f "$exp_path/config.yml" ]; then
  if [[ ${#export_args[@]} -gt 0 ]]; then
    echo "[INFO]: Export args: ${export_args[*]}"
  fi
  if [ -z "$data_path" ]; then
    data_path="$(infer_data_path "$exp_path")"
  fi
  if [ "$method_requested" != true ] && [[ ${#nerf_methods[@]} -eq 0 ]]; then
    nerf_methods=(poisson)
  fi
  model_name="$(experiment_model_name "$exp_path")"
  if [[ "$model_name" == *nerf* ]] || [[ "$model_name" == *splat* ]] || [[ "$model_name" == *ngp* ]]; then
    if [ "$mesh_only" = true ] || [ "$texture_only" = true ] || [ -n "$input_mesh_filename" ]; then
      echo "[ERROR]: --mesh-only/--texture-only/--input-mesh-filename are only supported for SDF experiments."
      exit 1
    fi
    if [ "$model_name" != splatfacto-w-light ] && [[ ${#splatfactow_args[@]} -gt 0 ]]; then
      echo "[ERROR]: --appearance-mode/--appearance-index are only supported for splatfacto-w-light exports."
      exit 1
    fi
    if [[ "$model_name" == *splat* ]]; then
      nerf_output_path="$(nerf_export_output_path "$exp_path" "$model_name" poisson)"
      if should_run_export "$nerf_output_path"; then
        if [ "$model_name" = splatfacto-w-light ]; then
          run_cmd "$(nerfstudio_python)" "$script_dir/export_splatfactow.py" \
            --load-config "$exp_path/config.yml" \
            --output-dir "$exp_path" \
            --obb-center "${nerf_obb_center[@]}" \
            --obb-rotation "${nerf_obb_rotation[@]}" \
            --obb-scale "${nerf_obb_scale[@]}" \
            "${splatfactow_args[@]}" \
            "${nerf_args[@]}"
        else
          run_cmd ns-export gaussian-splat \
            --load-config "$exp_path/config.yml" \
            --output-dir "$exp_path" \
            --obb-center "${nerf_obb_center[@]}" \
            --obb-rotation "${nerf_obb_rotation[@]}" \
            --obb-scale "${nerf_obb_scale[@]}" \
            "${nerf_args[@]}"
        fi
        clean_splat_output "$nerf_output_path"
      fi
      if [ "$orbit_frames_requested" = true ]; then
        run_nerfstudio_orbit_frames_export "$exp_path"
      fi
    else
      for method in "${nerf_methods[@]}"; do
        nerf_output_path="$(nerf_export_output_path "$exp_path" "$model_name" "$method")"
        if should_run_export "$nerf_output_path"; then
          if [ "$method" = pointcloud ]; then
            run_cmd ns-export pointcloud \
              --load-config "$exp_path/config.yml" \
              --output-dir "$exp_path" \
              --obb-center "${nerf_obb_center[@]}" \
              --obb-rotation "${nerf_obb_rotation[@]}" \
              --obb-scale "${nerf_obb_scale[@]}" \
              --std-ratio 1 \
              "${nerf_args[@]}"
          elif [ "$method" = tsdf ]; then
            run_cmd ns-export tsdf \
              --load-config "$exp_path/config.yml" \
              --output-dir "$exp_path" \
              --batch-size 1 \
              --resolution 256 256 256 \
              "${nerf_tsdf_args[@]}" \
              "${nerf_args[@]}"
          else
            run_cmd ns-export poisson \
              --load-config "$exp_path/config.yml" \
              --output-dir "$exp_path" \
              --save-point-cloud True \
              --obb-center "${nerf_obb_center[@]}" \
              --obb-rotation "${nerf_obb_rotation[@]}" \
              --obb-scale "${nerf_obb_scale[@]}" \
              --std-ratio 1 \
              --density-quantile 0.01 \
              "${nerf_args[@]}"
          fi
        fi
      done
      if [ "$orbit_frames_requested" = true ]; then
        run_nerfstudio_orbit_frames_export "$exp_path"
      fi
    fi
  else
    if [ "$mesh_only" = true ] && [ "$texture_only" = true ]; then
      echo "[ERROR]: --mesh-only and --texture-only cannot be used together"
      exit 1
    fi
    if [ -n "$input_mesh_filename" ] && [ "$texture_only" != true ]; then
      echo "[ERROR]: --input-mesh-filename requires --texture-only for SDF experiments"
      exit 1
    fi

    default_mesh_path="$exp_path/mesh.ply"

    if [ "$texture_only" = true ]; then
      if [ -n "$input_mesh_filename" ]; then
        # Resolve relative paths against exp_path
        if [[ "$input_mesh_filename" = /* ]]; then
          mesh_path="$input_mesh_filename"
        else
          mesh_path="$exp_path/$input_mesh_filename"
        fi
      else
        mesh_path="$default_mesh_path"
      fi
      if [ ! -f "$mesh_path" ]; then
        echo "[ERROR]: Mesh file $mesh_path not found"
        exit 1
      fi
      if [ ! -f "$exp_path/mesh.obj" ] || [ "${overwrite:-false}" = true ]; then
        run_cmd sdf-texture-mesh \
          --load-config "$exp_path/config.yml" \
          --output-dir "$exp_path" \
          --input-mesh-filename "$mesh_path" \
          "${texture_mesh_args[@]}"
      fi
    else
      if [ ! -f "$default_mesh_path" ] || [ "${overwrite:-false}" = true ]; then
        run_cmd sdf-extract-mesh \
          --load-config "$exp_path/config.yml" \
          --output-path "$default_mesh_path" \
          "${extract_mesh_args[@]}"
      fi
      if [ "$mesh_only" != true ]; then
        if [ -f "$default_mesh_path" ]; then
          if [ ! -f "$exp_path/mesh.obj" ] || [ "${overwrite:-false}" = true ]; then
            run_cmd sdf-texture-mesh \
              --load-config "$exp_path/config.yml" \
              --output-dir "$exp_path" \
              --input-mesh-filename "$default_mesh_path" \
              "${texture_mesh_args[@]}"
          fi
        else
          echo "[ERROR]: Mesh file $default_mesh_path not found"
          exit 1
        fi
      fi
    fi
    if [ "$orbit_frames_requested" = true ]; then
      run_sdf_orbit_frames_export "$exp_path"
    fi
  fi
else
  echo "[ERROR]: Config file $exp_path/config.yml not found"
  exit 1
fi
