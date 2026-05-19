#!/usr/bin/env bash
set -e

NUM_THREADS=$(nproc --all)
export NUM_THREADS OPENBLAS_NUM_THREADS="$NUM_THREADS" MKL_NUM_THREADS="$NUM_THREADS" \
       OMP_NUM_THREADS="$NUM_THREADS" TBB_NUM_THREADS="$NUM_THREADS"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/env.sh
source "$script_dir/env.sh"
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

stage_run() {
  echo "[INFO]: Running $1 stage"
}

stage_skip() {
  if [[ "$2" == by\ * ]]; then
    echo "[INFO]: $1 stage skipped $2"
  else
    echo "[INFO]: $1 stage skipped: $2"
  fi
}

output_skip() {
  echo "[INFO]: $1 output $2 already exists; skipping (use --overwrite to rerun)"
}

# Run a command, logging it first if verbose mode is enabled
run_cmd() {
  if [ "$verbose" = true ]; then
    echo "[CMD]: $*"
  fi
  "$@"
}

experiment_model_dir_name() {
  case "$1" in
    splatfacto-mcmc)
      echo "splatfacto"
      ;;
    *)
      echo "$1"
      ;;
  esac
}

uses_nerfstudio_trainer() {
  [[ "$1" == *nerf* ]] || [[ "$1" == *splat* ]] || [[ "$1" == *ngp* ]]
}

training_checkpoint_dir() {
  local model_name="$1"
  local experiment_path="$2"
  if uses_nerfstudio_trainer "$model_name"; then
    echo "$experiment_path/nerfstudio_models"
  else
    echo "$experiment_path/sdfstudio_models"
  fi
}

require_resume_checkpoints() {
  local checkpoint_dir="$1"
  local checkpoint_step="$2"
  if [ ! -d "$checkpoint_dir" ]; then
    echo "[ERROR]: Checkpoint directory $checkpoint_dir not found for --resume" >&2
    exit 1
  fi
  if [ -n "$checkpoint_step" ]; then
    local checkpoint_path
    checkpoint_path="$checkpoint_dir/step-$(printf '%09d' "$checkpoint_step").ckpt"
    if [ ! -f "$checkpoint_path" ]; then
      echo "[ERROR]: Checkpoint $checkpoint_path not found for --resume-step $checkpoint_step" >&2
      exit 1
    fi
    return
  fi
  if ! compgen -G "$checkpoint_dir/step-*.ckpt" >/dev/null; then
    echo "[ERROR]: No checkpoint files found for --resume in $checkpoint_dir" >&2
    exit 1
  fi
}

append_resume_args() {
  local -n target_args="$1"
  local model_name="$2"
  local checkpoint_dir="$3"
  local checkpoint_step="$4"

  if uses_nerfstudio_trainer "$model_name"; then
    target_args+=("--load-dir" "$checkpoint_dir")
    if [ -n "$checkpoint_step" ]; then
      target_args+=("--load-step" "$checkpoint_step")
    fi
  else
    target_args+=("--trainer.load-dir" "$checkpoint_dir")
    if [ -n "$checkpoint_step" ]; then
      target_args+=("--trainer.load-step" "$checkpoint_step")
    fi
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
  echo "  video [...args]    Additional arguments for ffmpeg.sh. Call ffmpeg.sh --help for details."
  echo "  sfm [...args]      Additional arguments for sfm.sh. Call sfm.sh --help for details."
  echo "                       --method <str>                         SfM method: colmap, glomap, hloc, vggsfm (default: colmap)"
  echo "  process [...args]  Additional arguments for sdf-process-data:"
  echo "                       --mask <str>                           Mask background: rembg, sam2, true, none (default: none)"
  echo "                       --min-match-ratio <float>              Acceptable percentage of estimated camera poses"
  echo "                       --crop-factor <top bot left rgt>       Crop ratio for images"
  echo "  train [...args]    Additional arguments for train.sh:"
  echo "                       --model <str>                          Model name (default: neus)"
  echo "                       --name <str>                           Experiment name (default: input directory name)"
  echo "                       --config <str>                         Configuration file or name (default: neus-grid-short)"
  echo "                       --resume                               Resume from existing checkpoint directory"
  echo "                       --resume-step <int>                    Resume from a specific checkpoint step"
  echo "                     Data processing flags (passed to nerfstudio-data):"
  echo "                       --downscale-factor <int>               Downscale factor for images"
  echo "                       --scale-factor <float>                 Scale factor for scene"
  echo "                       --center-method <str>                  Method to center poses"
  echo "                       --orientation-method <str>             Method to orient poses"
  echo "                       --auto-scale-poses <bool>              Auto-scale poses"
  echo "                       --train-split-fraction <float>         Train/val split fraction"
  echo "  export [...args]   Additional arguments for export.sh. Call export.sh --help for details."
  echo "                       --resolution <int>                         Marching cubes resolution (default: 1024)"
  echo "                       --bounding-box-min <float float float>     Minimum bounding box (default: -1 -1 -1)"
  echo "                       --bounding-box-max <float float float>     Maximum bounding box (default: 1 1 1)"
  echo "                       --marching-cube-threshold <float>          Isosurface threshold (default: 0.0)"
  echo "                       --px-per-uv-triangle <int>                 Pixels per UV triangle (default: 4)"
  echo "                       --num-pixels-per-side <int>                Pixels per side (default: 2048)"
  echo "                       --target-num-faces <int>                   Target number of faces (default: 50000)"
  echo "                       --use-average-appearance-embedding <bool>  Use average appearance embedding (default: True)"
  echo "                       --num-directions <int>                     Viewing directions for texturing (default: 1)"
  echo "                       --texture-method <str>                     Texturing method: legacy, cpu, gpu, open3d (default: gpu)"
  echo "                       --pad-px <int>                             Chart edge dilation pixels (default: 32)"
  echo "                       --normal-map-convention <str>              Normal map convention: opengl, directx (default: opengl)"
  echo "                       --appearance-idx <int>                     Camera index for appearance embedding"
  echo "                       --method <str>                             NeRF export: poisson, tsdf, pointcloud (default: poisson)"
  echo "                       --obb-rotation <float float float>          Rotation of oriented bounding-box (default: 0 0 0)"
  echo "                       --mesh-only                                Extract mesh but skip texturing (SDF only)"
  echo "                       --texture-only                             Texture existing mesh, skip extraction (SDF only)"
  echo "                       --input-mesh-filename <path>               Custom mesh file for texturing (requires --texture-only)"
  echo "                       --data <path>                              Override data path (for Docker/local portability)"
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
train_resume=false
train_resume_step=""

while [ $# -gt 0 ]; do
  case "$1" in
    --show)
      show=true
      shift
      ;;
    --verbose)
      verbose=true
      export VERBOSE=true
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
    --resume)
      if [ "$current_context" = "train" ]; then
        train_resume=true
        shift
      else
        echo "Error: --resume can only be used with the train context"
        exit 1
      fi
      ;;
    --resume-step)
      if [ "$current_context" = "train" ]; then
        if [[ $# -lt 2 || ! "$2" =~ ^[0-9]+$ ]]; then
          echo "Error: --resume-step requires a non-negative integer"
          exit 1
        fi
        train_resume=true
        train_resume_step="$2"
        shift 2
      else
        echo "Error: --resume-step can only be used with the train context"
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

if [ "$train_resume" = true ]; then
  if [ "$train_skip" = true ]; then
    echo "[ERROR]: train --resume cannot be combined with train --skip" >&2
    exit 1
  fi
  if [ "$overwrite" = true ] || [ "$train_overwrite" = true ]; then
    echo "[ERROR]: train --resume cannot be combined with --overwrite" >&2
    exit 1
  fi
fi

# Set up logging if --mail is specified
if [ -n "$mail_addr" ]; then
  logfile="$input_dir/run.log"
  exec > >(tee -a "$logfile") 2>&1
  verbose_echo "Logging to $logfile, will email $mail_addr on completion"
fi

if [ "$model" = splatfacto-w ]; then
  echo "[ERROR] splatfacto-w requires the plugin's splatfactow_dataparser and Phototourism/Nerf-W data layout." >&2
  echo "        mini-mesh produces Nerfstudio data; use --model splatfacto-w-light instead." >&2
  exit 1
fi

echo "Global args: ${global_args[*]}"
echo "============================="
echo "          1. VIDEO           "
echo "============================="

# Warn if video-related flags are set but input is not a video file
if ! [ -f "$input_path" ]; then
  stage_skip "Video" "input is not a video file"
  if [ "$video_overwrite" = true ]; then
    echo "[WARN]: --overwrite in video context ignored: input is not a video file"
  fi
  if [ ${#video_args[@]} -gt 0 ]; then
    echo "[WARN]: video arguments ignored: input is not a video file"
  fi
fi

if [ "$video_skip" = true ]; then
  stage_skip "Video" "by --skip"
elif [ -f "$input_path" ]; then
  if ! [ -d "$input_dir/images" ] || [ "$overwrite" = true ] || [ "$video_overwrite" = true ]; then
    stage_run "video"
    echo "Video args: ${video_args[*]}"
    if [ -d "$input_dir/images" ]; then
      verbose_echo "Removing: $input_dir/images $input_dir/images_orig"
      rm -rf "$input_dir/images" "$input_dir/images_orig"
    fi
    run_cmd "$script_dir"/ffmpeg.sh "$input_path" "${video_args[@]}"
  else
    output_skip "Video" "$input_dir/images"
  fi
fi

echo "============================="
echo "          2. SfM             "
echo "============================="

if [ "$sfm_skip" = true ]; then
  stage_skip "SfM" "by --skip"
else
  if ! [ -d "$input_dir/sparse" ] || [ "$overwrite" = true ] || [ "$sfm_overwrite" = true ]; then
    stage_run "SfM"
    echo "SFM args: ${sfm_args[*]}"
    if [ -d "$input_dir/sparse" ] && { [ "$overwrite" = true ] || [ "$sfm_overwrite" = true ]; }; then
      verbose_echo "Removing: $input_dir/sparse $input_dir/database.db $input_dir/colmap $input_dir/hloc"
      rm -rf "$input_dir/sparse" "$input_dir/database.db" "$input_dir/colmap" "$input_dir/hloc"
    fi
    case "$sfm_method" in
      colmap|glomap)
        if [ "$sfm_method" = glomap ]; then
          sfm_args+=("--use_glomap")
        fi
        run_cmd "$script_dir"/sfm.sh "$input_dir/images" "${sfm_args[@]}"
        ;;
      hloc|vggsfm)
        run_cmd "$script_dir"/dl_sfm.sh "$input_dir/images" --method "$sfm_method" "${sfm_args[@]}"
        ;;
      *)
        echo "Unsupported SfM method: $sfm_method. Supported methods: colmap, glomap, hloc, vggsfm"
        exit 1
        ;;
    esac
  else
    output_skip "SfM" "$input_dir/sparse"
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

if [ "$process_skip" = true ]; then
  stage_skip "Data processing" "by --skip"
else
  if ! [ -f "$input_dir/transforms.json" ] || [ "$overwrite" = true ] || [ "$process_overwrite" = true ]; then
    stage_run "data processing"
    if [[ ${#process_args[@]} -gt 0 ]]; then
      echo "Process args: ${process_args[*]}"
    fi
    if [ "$process_overwrite" = true ]; then
      verbose_echo "Removing: $input_dir/images_2 $input_dir/images_4 $input_dir/images_8 $input_dir/masks"
      rm -rf "$input_dir/images_2" "$input_dir/images_4" "$input_dir/images_8" "$input_dir/masks"
      verbose_echo "Removing: $input_dir/transforms.json $input_dir/sparse_pc.ply"
      rm -f "$input_dir/transforms.json" "$input_dir/sparse_pc.ply"
      if [ -d "$input_dir/images_orig" ]; then
        verbose_echo "Removing: $input_dir/images (will be restored from images_orig)"
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
        run_cmd rembg p "$input_dir/images_orig" "$input_dir/masks"
      elif [ "$mask" = sam2 ]; then
        run_cmd sam2 --data "$input_dir/images_orig" --output_dir "$input_dir/masks" --model.huggingface
      elif [ "$mask" != true ]; then
        echo "[ERROR]: Unsupported mask method '$mask'"
        exit 1
      fi
      process_data="$input_dir/masks"
    fi

    run_cmd sdf-process-data images \
      --data "$process_data" \
      --output_dir "$input_dir" \
      --skip-colmap \
      --colmap-model-path "$input_dir/sparse" \
      "${process_args[@]}"

    if ! [ -f "$input_dir/transforms.json" ]; then
      echo "[ERROR]: transforms.json not generated"
      exit 1
    fi
  else
    output_skip "Data processing" "$input_dir/transforms.json"
  fi
fi

echo "============================="
echo "          4. TRAIN           "
echo "============================="

exp_model=$(experiment_model_dir_name "$model")
exp_path="$input_dir/train/$name/$exp_model/run"
if [ "$train_skip" = true ]; then
  stage_skip "Train" "by --skip"
else
  if ! [ -f "$exp_path/config.yml" ] || [ "$overwrite" = true ] || [ "$train_overwrite" = true ] || [ "$train_resume" = true ]; then
    stage_run "train"
    if [ "$train_resume" = true ]; then
      resume_checkpoint_dir="$(training_checkpoint_dir "$model" "$exp_path")"
      require_resume_checkpoints "$resume_checkpoint_dir" "$train_resume_step"
      echo "[INFO]: Resuming train stage from $resume_checkpoint_dir"
      append_resume_args train_args "$model" "$resume_checkpoint_dir" "$train_resume_step"
    fi
    if [[ ${#train_args[@]} -gt 0 ]]; then
      echo "Train args: ${train_args[*]}"
    fi
    if [ -d "$exp_path" ] && { [ "$overwrite" = true ] || [ "$train_overwrite" = true ]; }; then
      verbose_echo "Removing: $exp_path"
      rm -rf "$exp_path"
    fi
    if [ "$mask" != none ]; then
      if [[ "$model" != *nerf* && "$model" != *splat* && "$model" != *ngp* ]]; then
        train_args+=("--pipeline.model.background-model" "none" "--trainer.mixed-precision" "False")
      else
        train_args+=("--pipeline.model.background-color" "random")
      fi
    fi
    run_cmd "$script_dir"/train.sh "$model" "$name" "$input_dir" "$config" \
      "${train_args[@]}" --timestamp run
  else
    output_skip "Train" "$exp_path/config.yml"
  fi
fi

echo "============================="
echo "         5. EXPORT           "
echo "============================="

if [ "$export_skip" = true ]; then
  stage_skip "Export" "by --skip"
else
  stage_run "export"
  export_cmd_args=("${export_args[@]}")
  if [ "$overwrite" = true ] || [ "$export_overwrite" = true ]; then
    export_cmd_args+=("--overwrite")
  fi
  run_cmd "$script_dir"/export.sh "$exp_path" "${export_cmd_args[@]}"
fi
