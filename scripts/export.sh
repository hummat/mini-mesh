#!/usr/bin/env bash
set -e

verbose=false

# Run a command, logging it first if verbose mode is enabled
run_cmd() {
  if [ "$verbose" = true ] || [ "${VERBOSE:-}" = true ]; then
    echo "[CMD]: $*"
  fi
  "$@"
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
  echo "                           --resolution <int>                       Marching cubes resolution (default: 1024)"
  echo "                           --bounding-box-min <float float float>   Minimum bounding box (default: -1 -1 -1)"
  echo "                           --bounding-box-max <float float float>   Maximum bounding box (default: 1 1 1)"
  echo "                           --marching-cube-threshold <float>        Isosurface threshold (default: 0.0)"
  echo "                           --px-per-uv-triangle <int>               Pixels per UV triangle (default: 4)"
  echo "                           --num-pixels-per-side <int>              Pixels per side (default: 2048)"
  echo "                           --target-num-faces <int>                 Target number of faces (default: 50000)"
  echo "                           --method <string>                        NeRF export method: poisson, tsdf, pointcloud (default: poisson)"
  echo "                           --obb-center <float float float>         Center of oriented bounding-box (default: 0 0 0)"
  echo "                           --obb-scale <float float float>          Scale of oriented bounding-box (default: 1 1 1)"
  echo "                           --downscale-factor <int>                 Image downscale factor for TSDF extraction (default: 2)"
  echo "                           --mesh-only                              SDF only: extract mesh but skip texturing"
  echo "                           --texture-only                           SDF only: texture an existing mesh, skip extraction"
  echo "                           --input-mesh-filename <path>             SDF only: custom mesh file for texturing (requires --texture-only)"
  echo "                           --overwrite                              Overwrite existing files"
  echo "                           --verbose                                Enable verbose output"
  echo "                           --help                                   Show this help message"
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
texture_mesh_args=()
nerf_args=()
method=poisson
mesh_only=false
texture_only=false
input_mesh_filename=""

i=0
while [ $i -lt ${#export_args[@]} ]; do
  case "${export_args[$i]}" in
    --resolution|--marching-cube-threshold)
      extract_mesh_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      nerf_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      i=$((i+2))
      ;;
    --bounding-box-min|--bounding-box-max)
      extract_mesh_args+=("${export_args[$i]}" "${export_args[$((i+1))]}" "${export_args[$((i+2))]}" "${export_args[$((i+3))]}")
      nerf_args+=("${export_args[$i]}" "${export_args[$((i+1))]}" "${export_args[$((i+2))]}" "${export_args[$((i+3))]}")
      i=$((i+4))
      ;;
    --px-per-uv-triangle|--num-pixels-per-side|--target-num-faces)
      texture_mesh_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      nerf_args+=("${export_args[$i]}" "${export_args[$((i+1))]}")
      i=$((i+2))
      ;;
    --method)
      method="${export_args[$((i+1))]}"
      i=$((i+2))
      ;;
    --obb-center|--obb-scale)
      nerf_args+=("${export_args[$i]}" "${export_args[$((i+1))]}" "${export_args[$((i+2))]}" "${export_args[$((i+3))]}")
      i=$((i+4))
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
  model_name=$(basename "$exp_path")
  if [[ "$model_name" == *nerf* ]] || [[ "$model_name" == *splat* ]] || [[ "$model_name" == *ngp* ]]; then
    if [ "$mesh_only" = true ] || [ "$texture_only" = true ] || [ -n "$input_mesh_filename" ]; then
      echo "[ERROR]: --mesh-only/--texture-only/--input-mesh-filename are only supported for SDF experiments."
      exit 1
    fi
    if [[ "$model_name" == *splat* ]]; then
      run_cmd ns-export gaussian-splat \
        --load-config "$exp_path/config.yml" \
        --output-dir "$exp_path" \
        --obb-center 0 0 0 \
        --obb-rotation 0 0 0 \
        --obb-scale 1 1 1 \
        "${nerf_args[@]}"
    elif [ "$method" = pointcloud ]; then
      run_cmd ns-export pointcloud \
        --load-config "$exp_path/config.yml" \
        --output-dir "$exp_path" \
        --obb-center 0 0 0 \
        --obb-rotation 0 0 0 \
        --obb-scale 1 1 1 \
        --std-ratio 1 \
        "${nerf_args[@]}"
    elif [ "$method" = tsdf ]; then
      run_cmd ns-export tsdf \
        --load-config "$exp_path/config.yml" \
        --output-dir "$exp_path" \
        --batch-size 1 \
        --resolution 256 256 256 \
        "${nerf_args[@]}"
    else
      run_cmd ns-export poisson \
        --load-config "$exp_path/config.yml" \
        --output-dir "$exp_path" \
        --save-point-cloud True \
        --obb-center 0 0 0 \
        --obb-rotation 0 0 0 \
        --obb-scale 1 1 1 \
        --std-ratio 1 \
        --density-quantile 0.01 \
        "${nerf_args[@]}"
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
  fi
else
  echo "[ERROR]: Config file $exp_path/config.yml not found"
  exit 1
fi
