#!/usr/bin/env bash
set -e

NUM_THREADS=$(nproc --all)
export NUM_THREADS OPENBLAS_NUM_THREADS="$NUM_THREADS" MKL_NUM_THREADS="$NUM_THREADS" \
       OMP_NUM_THREADS="$NUM_THREADS" TBB_NUM_THREADS="$NUM_THREADS"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
input_dir=""
name="unknown"
mail_addr=""
logfile=""

finish_script() {
  local exit_code=$?
  echo "============================="
  echo "          FINISHED           "
  echo "============================="
  local status; status=$([ "$exit_code" -eq 0 ] && echo "SUCCESS" || echo "FAILED")
  echo "Job '$name': $status"
  if [ -n "$mail_addr" ] && [ -n "$logfile" ]; then
    if command -v mail >/dev/null; then
      mail -s "[mini-mesh] Job '$name': $status" "$mail_addr" < "$logfile"
    else
      echo "Warning: 'mail' command not found, cannot send notification"
    fi
  fi
  exit "$exit_code"
}

trap finish_script EXIT

verbose_echo() {
  if [ "$verbose" = true ]; then
    echo "[VERBOSE]:" "$@"
  fi
}

function show_help {
  echo "Usage: $0 <input_path> [options] [contexts] [args...]"
  echo
  echo "This script automates a multi-step 3D reconstruction workflow:"
  echo "1. Optional video extraction using ffmpeg (video context)"
  echo "2. Structure-from-Motion (SfM) using sfm.sh (sfm context)"
  echo "3. Data processing using sdf-process-data (process context)"
  echo "4. Training using train.sh (train context)"
  echo "5. Mesh export using export.sh (export context)"
  echo
  echo "Options:"
  echo "  --show          Show COLMAP GUI after SfM completes"
  echo "  --verbose       Enable verbose output"
  echo "  --mail <addr>   Send notification email on completion"
  echo "  --help          Show this help message and exit"
  echo
  echo "Contexts:"
  echo "  video [...args]    Additional arguments for ffmpeg.sh. Call ffmpeg.sh for more information."
  echo "  sfm [...args]      Additional arguments for sfm.sh. Call sfm.sh for more information."
  echo "                       --method <str>                    SfM method: colmap, glomap, hloc, vggsfm (default: colmap)"
  echo "  process [...args]  Additional arguments for sdf-process-data:"
  echo "                       --mask <str>                      Mask background: rembg, sam2, true, none (default: none)"
  echo "                       --min-match-ratio <float>         Acceptable percentage of estimated camera poses"
  echo "                       --crop-factor <top bot left rgt>  Crop ratio for images"
  echo "  train [...args]    Additional arguments for train.sh:"
  echo "                       --model <model>                   Model name (default: neus)"
  echo "                       --name <name>                     Experiment name (default: input directory name)"
  echo "                       --config <config>                 Configuration file or name (default: neus-grid-short)"
  echo "                     Data processing flags (passed to nerfstudio-data):"
  echo "                       --downscale-factor <int>          Downscale factor for images"
  echo "                       --scale-factor <float>            Scale factor for scene"
  echo "                       --center-method <str>             Method to center poses"
  echo "                       --orientation-method <str>        Method to orient poses"
  echo "                       --auto-scale-poses <bool>         Auto-scale poses"
  echo "                       --train-split-fraction <float>    Train/val split fraction"
  echo "  export [...args]   Additional arguments for export.sh:"
  echo "                       --resolution <value>                Resolution of the exported mesh (default: 1024)"
  echo "                       --bounding-box-min/max <x y z>      Bounding box for the exported mesh (default: +-1)"
  echo "                       --marching-cube-threshold <value>   Isosurface value (default: 0.0)"
  echo "                       --px-per-uv-triangle <value>        Pixels per UV triangle (default: 4)"
  echo "                       --num-pixels-per-side <value>       Pixels per side (default: 2048)"
  echo "                       --target-num-faces <value>          Target number of faces (default: 50_000)"
  echo "                       --method <str>                      NeRF export: poisson, tsdf, pointcloud (default: poisson)"
  echo "                       --mesh-only                         SDF only: extract mesh but skip texturing"
  echo "                       --texture-only                      SDF only: texture an existing mesh, skip extraction"
  echo "                       --input-mesh-filename <path>        SDF only: custom mesh file for texturing (requires --texture-only)"
  echo
  echo "Examples:"
  echo "  $0 /path/to/images --show sfm --camera_model SIMPLE_RADIAL --matcher exhaustive"
  echo "  $0 /path/to/video.mp4 video --fps 1 sfm --method glomap train --model neus-facto --config neus-facto-fast"
  echo "  $0 /path/to/images sfm --method hloc process --mask rembg train --config neus-grid-short export --resolution 2048"
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
process_args=()
train_args=()
export_args=()

show=false
verbose=false
overwrite=false
current_context=global
sfm_method=colmap
mask=none
model=neus
name=$(basename "$input_dir")
config=neus-grid-short

video_skip=false
sfm_skip=false
process_skip=false
train_skip=false
export_skip=false
video_overwrite=false
sfm_overwrite=false
process_overwrite=false
train_overwrite=false
export_overwrite=false

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
    --mail)
      mail_addr="$2"
      shift 2
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
    process)
      current_context="process"
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
      elif [ "$current_context" = "export" ]; then
        export_args+=("$1" "$2")
        shift 2
      else
        echo "Error: --method can only be used with the sfm or export context"
        exit 1
      fi
      ;;
    --mask)
      if [ "$current_context" = "process" ]; then
        if [ "$2" = rembg ] || [ "$2" = sam2 ] || [ "$2" = true ] || [ "$2" = none ]; then
          mask="$2"
          shift 2
        else
          echo "Error: Unsupported mask method '$2'. Supported: rembg, sam2, true, none"
          exit 1
        fi
      else
        echo "Error: --mask can only be used with the process context"
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
     --skip)
      case "$current_context" in
        video) video_skip=true ;;
        sfm) sfm_skip=true ;;
        process) process_skip=true ;;
        train) train_skip=true ;;
        export) export_skip=true ;;
      esac
      shift
      ;;
    --overwrite)
      case "$current_context" in
        video) video_overwrite=true ;;
        sfm) sfm_overwrite=true ;;
        process) process_overwrite=true ;;
        train) train_overwrite=true ;;
        export) export_overwrite=true ;;
        global) overwrite=true ;;
      esac
      shift
      ;;
    *)
      case "$current_context" in
        global) global_args+=("$1");;
        video) video_args+=("$1");;
        sfm) sfm_args+=("$1");;
        process) process_args+=("$1");;
        train) train_args+=("$1");;
        export) export_args+=("$1");;
      esac
      shift
      ;;
  esac
done

# Set up logging if --mail is specified
if [ -n "$mail_addr" ]; then
  logfile="$input_dir/run.log"
  exec > >(tee -a "$logfile") 2>&1
  verbose_echo "Logging to $logfile, will email $mail_addr on completion"
fi

echo "Global args: ${global_args[*]}"
echo "============================="
echo "          1. VIDEO           "
echo "============================="

if [ "$video_skip" != true ]; then
  if { [ -f "$input_path" ] && ! [ -d "$input_dir/images" ]; } || [ "$overwrite" = true ] || [ "$video_overwrite" = true ]; then
    echo "Video args: ${video_args[*]}"
    if [ -d "$input_dir/images" ] && { [ "$overwrite" = true ] || [ "$video_overwrite" = true ]; }; then
      rm -rf "$input_dir/images"
    fi
    "$script_dir"/ffmpeg.sh "$input_path" "${video_args[@]}"
  fi
fi

echo "============================="
echo "          2. SfM             "
echo "============================="

if [ "$sfm_skip" != true ]; then
  if ! [ -d "$input_dir/sparse" ] || [ "$overwrite" = true ] || [ "$sfm_overwrite" = true ]; then
    echo "SFM args: ${sfm_args[*]}"
    if [ -d "$input_dir/sparse" ] && { [ "$overwrite" = true ] || [ "$sfm_overwrite" = true ]; }; then
      rm -rf "$input_dir/sparse"
    fi
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
fi

if [ "$show" = true ]; then
  colmap gui --import_path "$input_dir/sparse" \
             --database_path "$input_dir/database.db" \
             --image_path "$input_dir/images"
fi

echo "============================="
echo "     3. DATA PROCESSING      "
echo "============================="

if [ "$process_skip" != true ]; then
  if ! [ -f "$input_dir/transforms.json" ] || [ "$overwrite" = true ] || [ "$process_overwrite" = true ]; then
    if [[ ${#process_args[@]} -gt 0 ]]; then
      echo "Process args: ${process_args[*]}"
    fi
    if [ "$process_overwrite" = true ]; then
      rm -rf "$input_dir/images_2" "$input_dir/images_4" "$input_dir/images_8" "$input_dir/masks"
      rm -f "$input_dir/transforms.json" "$input_dir/sparse_pc.ply"
      if [ -d "$input_dir/images_orig" ]; then
        rm -rf "$input_dir/images"
      fi
    fi
    if [ -d "$input_dir/images" ] && ! [ -d "$input_dir/images_orig" ]; then
      mv "$input_dir/images" "$input_dir/images_orig"
    fi

    process_data="$input_dir/images_orig"
    if [ "$mask" != none ]; then
      echo "Masking images using $mask"
      if [ "$mask" = rembg ]; then
        rembg p "$input_dir/images_orig" "$input_dir/masks"
      elif [ "$mask" = sam2 ]; then
        sam2 --data "$input_dir/images_orig" --output_dir "$input_dir/masks" --model.huggingface
      elif [ "$mask" != true ]; then
        echo "[ERROR]: Unsupported mask method '$mask'"
        exit 1
      fi
      process_data="$input_dir/masks"
    fi

    sdf-process-data images \
      --data "$process_data" \
      --output_dir "$input_dir" \
      --skip-colmap \
      --colmap-model-path "$input_dir/sparse" \
      "${process_args[@]}"

    if ! [ -f "$input_dir/transforms.json" ]; then
      echo "[ERROR]: transforms.json not generated"
      exit 1
    fi
  fi
fi

echo "============================="
echo "          4. TRAIN           "
echo "============================="

exp_path="$input_dir/train/$name/$model"
if [ "$train_skip" != true ]; then
  if ! [ -d "$exp_path" ] || [ "$overwrite" = true ] || [ "$train_overwrite" = true ]; then
    if [[ ${#train_args[@]} -gt 0 ]]; then
      echo "Train args: ${train_args[*]}"
    fi
    if [ -d "$exp_path" ] && { [ "$overwrite" = true ] || [ "$train_overwrite" = true ]; }; then
      rm -rf "$exp_path"
    fi
    if [ "$mask" != none ]; then
      if [[ "$model" != *nerf* && "$model" != *splat* && "$model" != *ngp* ]]; then
        train_args+=("--pipeline.model.background-model" "none" "--trainer.mixed-precision" "False")
      else
        train_args+=("--pipeline.model.background-color" "random")
      fi
    fi
    "$script_dir"/train.sh "$model" "$name" "$input_dir" "$config" \
      "${train_args[@]}" --timestamp ""
  fi
fi

echo "============================="
echo "         5. EXPORT           "
echo "============================="

if [ "$export_skip" != true ]; then
  export_cmd_args=("${export_args[@]}")
  if [ "$overwrite" = true ] || [ "$export_overwrite" = true ]; then
    export_cmd_args+=("--overwrite")
  fi
  "$script_dir"/export.sh "$exp_path" "${export_cmd_args[@]}"
fi
