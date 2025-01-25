#!/usr/bin/env bash
set -e
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

function show_help {
  echo "Usage: $0 <input_path> [options] [contexts] [args...]"
  echo
  echo "This script automates a multi-step 3D reconstruction workflow:"
  echo "1. Optional video extraction using ffmpeg (video context)"
  echo "2. Structure-from-Motion (SfM) using sfm.sh (sfm context)"
  echo "3. Data processing using ns-process-data (global context)"
  echo "4. Training using train.sh (train context)"
  echo "5. Mesh export using ns-extract-mesh (export context)"
  echo
  echo "Options:"
  echo "  --show      Show COLMAP GUI after SfM completes"
  echo "  --verbose   Enable verbose output"
  echo "  --help      Show this help message and exit"
  echo
  echo "Contexts:"
  echo "  video [...args]    Additional arguments for ffmpeg.sh. Call ffmpeg.sh for more information."
  echo "  sfm [...args]      Additional arguments for sfm.sh. Call sfm.sh for more information."
  echo "  train [...args]    Additional arguments for train.sh:"
  echo "                       --model <model>     Model name (default: neus)"
  echo "                       --name <name>       Experiment name (default: input directory name)"
  echo "                       --config <config>   Configuration file or name (default: neus-grid-dev)"
  echo "  export [...args]   Additional arguments for the mesh export:"
  echo "                       --resolution <value>                Resolution of the exported mesh (default: 1024)"
  echo "                       --bounding-box-min/max <x y z>      Bounding box for the exported mesh (default: +-1)"
  echo "                       --marching-cube-threshold <value>   Isosurface value (default: 0.0)"
  echo "                       --px-per-uv-triangle <value>        Pixels per UV triangle (default: 4)"
  echo "                       --num-pixels-per-side <value>       Pixels per side (default: 2048)"
  echo "                       --target-num-faces <value>          Target number of faces (default: 50_000)"
  echo
  echo "Examples:"
  echo "  $0 /path/to/images --show sfm --camera_model SIMPLE_RADIAL"
  echo "  $0 /path/to/video.mp4 video --fps 1 sfm --use_glomap train --config neus-facto-fast --vis wandb"
  exit 0
}

# Check if no arguments are provided
if [ $# -eq 0 ]; then
  show_help
fi

# Check if user wants help early
for arg in "$@"; do
  if [ "$arg" == "--help" ]; then
    show_help
  fi
done

input_path="$1"
if [ -f "$input_path" ] || [ -d "$input_path" ]; then
  input_dir=$(dirname "$input_path")
else
  echo "Input path does not exist: $input_path"
  exit 1
fi
shift

global_args=()
video_args=()
sfm_args=()
train_args=()
export_args=()

show=false
verbose=false
overwrite=false
current_context=global
sfm_method=colmap
model=neus
name=$(basename "$input_dir")
config=neus-grid-dev

while [ $# -gt 0 ]; do
  case "$1" in
    --show)
      show=true
      shift
      ;;
    --verbose)
      verbose=true
      shift
      ;;
    --overwrite)
      overwrite=true
      shift
      ;;
    --help)
      show_help
      ;;
    video)
      current_context="video"
      shift
      ;;
    sfm)
      current_context="sfm"
      shift
      ;;
    train)
      current_context="train"
      shift
      ;;
    export)
      current_context="export"
      shift
      ;;
    --method)
      if [ "$current_context" = "sfm" ]; then
        sfm_method="$2"
        shift 2
      else
        echo "Error: --method can only be used with the sfm context"
        exit 1
      fi
      ;;
    --model)
      if [ "$current_context" = "train" ]; then
        model="$2"
        config="$2"
        shift 2
      else
        echo "Error: --model can only be used with the train context"
        exit 1
      fi
      ;;
    --name)
      if [ "$current_context" = "train" ]; then
        name="$2"
        shift 2
      else
        echo "Error: --name can only be used with the train context"
        exit 1
      fi
      ;;
    --config)
      if [ "$current_context" = "train" ]; then
        config="$2"
        shift 2
      else
        echo "Error: --config can only be used with the train context"
        exit 1
      fi
      ;;
    *)
      case "$current_context" in
        global) global_args+=("$1");;
        video) video_args+=("$1");;
        sfm) sfm_args+=("$1");;
        train) train_args+=("$1");;
        export) export_args+=("$1");;
      esac
      shift
      ;;
  esac
done

echo "Global args: ${global_args[*]}"
echo "============================="
echo "          1. VIDEO           "
echo "============================="

if ([ -f "$input_path" ] && ! [ -d "$input_dir/images" ]) || [ "$overwrite" = true ]; then
  echo "Video args: ${video_args[*]}"
  "$script_dir"/ffmpeg.sh "$input_path" "${video_args[@]}"
fi

echo "============================="
echo "          2. SfM             "
echo "============================="

if ! [ -d "$input_dir/sparse" ] || [ "$overwrite" = true ]; then
  echo "SFM args: ${sfm_args[*]}"
  case "$sfm_method" in
    colmap|glomap)
      if [ "$sfm_method" = glomap ]; then
        sfm_args+=("--use_glomap")
      fi
      "$script_dir"/sfm.sh "$input_dir/images" "${sfm_args[@]}"
      ;;
    hloc|vggsfm)
      "$script_dir"/dl_sfm.sh "$input_dir/images" --method "$sfm_method" "${sfm_args[@]}"
      ;;
    *)
      echo "Unsupported SfM method: $sfm_method. Supported methods: colmap, glomap, hloc, vggsfm"
      exit 1
      ;;
  esac
fi

if [ "$show" = true ]; then
  colmap gui --import_path "$input_dir/sparse" \
             --database_path "$input_dir/database.db" \
             --image_path "$input_dir/images"
fi

echo "============================="
echo "     3. DATA PROCESSING      "
echo "============================="

if ! [ -f "$input_dir/transforms.json" ] || [ "$overwrite" = true ]; then
  if [ -d "$input_dir/images" ] && ! [ -d "$input_dir/images_orig" ]; then
    mv "$input_dir/images" "$input_dir/images_orig"
  fi
  ns-process-data images \
    --data "$input_dir/images_orig" \
    --output_dir "$input_dir" \
    --skip-colmap \
    --colmap-model-path "$input_dir/sparse"
fi

echo "============================="
echo "          4. TRAIN           "
echo "============================="

exp_path="$input_dir/train/$name/$model"
if ! [ -d "$exp_path" ] || [ "$overwrite" = true ]; then
  echo "Train args: ${train_args[*]}"
  "$script_dir"/train.sh "$model" "$name" "$input_dir" "$config" "${train_args[@]}" --timestamp ""
fi

echo "============================="
echo "         5. EXPORT           "
echo "============================="

echo "Export args: ${export_args[*]}"
extract_args=()
texture_args=()
for arg in "${export_args[@]}"; do
  case "$arg" in
    --resolution|--bounding-box-min|--bounding-box-max|--marching-cube-threshold)
      extract_args+=("$arg")
      ;;
    --px-per-uv-triangle|--num-pixels-per-side|--target-num-faces)
      texture_args+=("$arg")
      ;;
  esac
done

if [ -f "$exp_path/config.yml" ]; then
  if ! [ -f "$exp_path/mesh.ply" ] || [ "$overwrite" = true ]; then
    echo "Extracting mesh with: ${extract_args[*]}"
    ns-extract-mesh \
      --load-config "$exp_path/config.yml" \
      --output-path "$exp_path/mesh.ply" \
      "${extract_args[@]}"
  fi
  if [ -f "$exp_path/mesh.ply" ]; then
    echo "Texturing mesh with: ${texture_args[*]}"
    ns-texture-mesh \
      --load-config "$exp_path/config.yml" \
      --output-dir "$exp_path" \
      --input-mesh-filename "$exp_path/mesh.ply" \
      "${texture_args[@]}"
  else
    echo "[ERROR] Mesh file $exp_path/mesh.ply not found"
    exit 1
  fi
else
  echo "[ERROR] Config file $exp_path/config.yml not found"
  exit 1
fi