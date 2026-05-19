#!/usr/bin/env bash
set -e

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/env.sh
source "$script_dir/env.sh"

if ! command -v colmap &> /dev/null; then
  echo "[ERROR]: COLMAP binary could not be found."
  exit 1
fi

CAMERA_MODEL="OPENCV"
MATCHER="exhaustive"
EXTRA=false
REFINE_PRINCIPAL_POINT=true
CONVERT_TXT=false
UNDISTORT=false
OVERWRITE=false
USE_GLOMAP=false

NUM_THREADS=$(nproc --all)
OPENBLAS_NUM_THREADS="$NUM_THREADS"
MKL_NUM_THREADS="$NUM_THREADS"
OMP_NUM_THREADS="$NUM_THREADS"
TBB_NUM_THREADS="$NUM_THREADS"

valid_colmap_model() {
  local model_path="$1"
  [[ -f "$model_path/cameras.bin" && -f "$model_path/images.bin" && -f "$model_path/points3D.bin" ]]
}

registered_image_count() {
  local model_path="$1"
  colmap model_analyzer --path "$model_path" 2>&1 \
    | awk '/Registered images:/ { print $NF; found=1 } END { if (!found) exit 1 }'
}

promote_colmap_model() {
  local source_path="$1"
  local target_path="$2"
  local tmp_path
  tmp_path="$(dirname "$target_path")/.$(basename "$target_path").canonical.$$"
  rm -rf "$tmp_path"
  mkdir -p "$tmp_path"
  cp -a "$source_path"/. "$tmp_path"/
  rm -rf "$target_path"
  mv "$tmp_path" "$target_path"
}

canonicalize_sparse_model() {
  local sparse_path="$1"
  local components=()
  local component
  local component_count
  local largest_component=""
  local largest_count=-1
  local merge_candidate
  local merge_output
  local candidate_count
  local merged_count
  local failed_merges=0

  if valid_colmap_model "$sparse_path"; then
    return
  fi

  for component in "$sparse_path"/*; do
    if [[ -d "$component" ]] && valid_colmap_model "$component"; then
      components+=("$component")
    fi
  done

  if [[ ${#components[@]} -eq 0 ]]; then
    echo "[ERROR]: COLMAP did not produce a valid sparse model in $sparse_path" >&2
    exit 1
  fi

  for component in "${components[@]}"; do
    if ! component_count="$(registered_image_count "$component")"; then
      echo "[ERROR]: Failed to inspect COLMAP submodel $component" >&2
      exit 1
    fi
    echo "[INFO]: COLMAP submodel $(basename "$component") registered $component_count images"
    if (( component_count > largest_count )); then
      largest_count="$component_count"
      largest_component="$component"
    fi
  done

  if [[ ${#components[@]} -eq 1 ]]; then
    echo "[INFO]: Promoting COLMAP submodel $(basename "$largest_component") as canonical sparse model"
    promote_colmap_model "$largest_component" "$sparse_path"
    return
  fi

  echo "[WARN]: COLMAP produced ${#components[@]} disconnected sparse submodels; trying to merge them"
  merge_candidate="$(dirname "$sparse_path")/.sparse-merge-candidate.$$"
  rm -rf "$merge_candidate"
  mkdir -p "$merge_candidate"
  cp -a "$largest_component"/. "$merge_candidate"/
  candidate_count="$largest_count"

  for component in "${components[@]}"; do
    if [[ "$component" = "$largest_component" ]]; then
      continue
    fi
    merge_output="$(dirname "$sparse_path")/.sparse-merge-output.$$"
    rm -rf "$merge_output"
    mkdir -p "$merge_output"
    if colmap model_merger \
      --input_path1 "$merge_candidate" \
      --input_path2 "$component" \
      --output_path "$merge_output" \
      && valid_colmap_model "$merge_output"; then
      if merged_count="$(registered_image_count "$merge_output")" && (( merged_count > candidate_count )); then
        rm -rf "$merge_candidate"
        mv "$merge_output" "$merge_candidate"
        candidate_count="$merged_count"
        echo "[INFO]: Merged COLMAP submodel $(basename "$component"); canonical model has $candidate_count images"
      else
        failed_merges=$((failed_merges + 1))
        rm -rf "$merge_output"
        echo "[WARN]: Model merge for submodel $(basename "$component") did not increase registered image count; keeping current canonical candidate"
      fi
    else
      failed_merges=$((failed_merges + 1))
      rm -rf "$merge_output"
      echo "[WARN]: Model merge did not produce a valid model for submodel $(basename "$component"); keeping current canonical candidate"
    fi
  done

  if (( failed_merges > 0 )); then
    echo "[WARN]: Using largest mergeable COLMAP component with $candidate_count images; $failed_merges submodel(s) were left out"
  fi
  promote_colmap_model "$merge_candidate" "$sparse_path"
  rm -rf "$merge_candidate"
}

function show_help {
  echo "Usage: $0 <path-to-images> [options]"
  echo
  echo "Options:"
  echo "  --database_path <str>             Path to the COLMAP database file (default: <path-to-images>/../database.db)"
  echo "  --camera_model <str>              Camera model: SIMPLE_PINHOLE, PINHOLE, SIMPLE_RADIAL, RADIAL, OPENCV, FISHEYE (default: OPENCV)"
  echo "  --matcher <str>                   Matching method: exhaustive, sequential, vocab_tree (default: exhaustive)"
  echo "  --extra                           Set additional arguments for improved feature extraction and matching. No GPU support (slow)."
  echo "  --refine_principal_point <bool>   Run bundle adjustment with principal point refinement (default: true)"
  echo "  --convert_txt                     Convert the model to TXT format after reconstruction"
  echo "  --undistort                       Undistort images after reconstruction"
  echo "  --overwrite                       Overwrite existing sparse directory without confirmation"
  echo "  --use_glomap                      Use GLOMAP mapper instead of COLMAP mapper if available"
  echo "  --num_threads <int>               Number of threads to use for feature extraction and matching (default: all available)"
  echo "  --help                            Show this help message and exit"
  echo
  echo "This script automates the Structure-from-Motion (SfM) pipeline using COLMAP:"
  echo "1. Feature extraction from images"
  echo "2. Feature matching"
  echo "3. Sparse mapping (3D reconstruction)"
  echo "4. Bundle adjustment"
  echo
  echo "If GPU support is detected (via nvidia-smi), feature extraction and matching will use the GPU."
  exit 0
}

# Check if no arguments are provided
if [[ $# -eq 0 ]]; then
  show_help
fi

# Check if user wants help early
for arg in "$@"; do
  if [[ "$arg" == "--help" ]]; then
    show_help
  fi
done

IMAGES="$1"
if [ ! -d "$IMAGES" ]; then
  echo "[ERROR]: Image directory does not exist: $IMAGES"
  exit 1
fi
DB=$(dirname "$IMAGES")/database.db
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --database_path)
      DB="$2"
      shift 2
    ;;
    --camera_model)
      CAMERA_MODEL="$2"
      shift 2
    ;;
    --matcher)
      MATCHER="$2"
      shift 2
    ;;
    --extra)
      EXTRA=true
      shift
    ;;
    --refine_principal_point)
      REFINE_PRINCIPAL_POINT="$2"
      shift 2
    ;;
    --convert_txt)
      CONVERT_TXT=true
      shift
    ;;
    --undistort)
      UNDISTORT=true
      shift
    ;;
    --overwrite)
      OVERWRITE=true
      shift
    ;;
    --num_threads)
      NUM_THREADS="$2"
      shift 2
    ;;
    --use_glomap)
      USE_GLOMAP=true
      shift
    ;;
    --help)
      show_help
    ;;
    *)
      echo "[ERROR]: Unknown option: $1"
      show_help
    ;;
  esac
done

USE_GPU=false
if ! [ "$EXTRA" = true ]; then
  # Attempt to detect GPU support
  # A simple heuristic: if `nvidia-smi` is available and returns a GPU count > 0, assume GPU support.
  if command -v nvidia-smi &> /dev/null; then
    GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
    if [ "$GPU_COUNT" -gt 0 ]; then
      USE_GPU=true
    echo "[INFO]: GPU detected. Using GPU for feature extraction and matching."
    fi
  fi
fi

MAPPER_CMD="colmap mapper"
if [ "$USE_GLOMAP" = true ]; then
  if command -v glomap &> /dev/null; then
    MAPPER_CMD="glomap mapper"
  else
    echo "[ERROR]: GLOMAP binary could not be found."
    exit 1
  fi
fi

SPARSE="$(dirname "$DB")/sparse"
if [ -d "$SPARSE" ]; then
  if [ "$OVERWRITE" != true ]; then
    read -r -p "[WARNING]: Directory '$SPARSE' already exists. Continue? (y/N): " confirm
    if ! [[ "$confirm" =~ ^[Yy]$ ]]; then
      exit 0
    fi
  else
    [ -f "$DB" ] && rm "$DB"
    rm -rf "$SPARSE"
    mkdir -p "$SPARSE"
  fi
else
  mkdir -p "$SPARSE"
fi

echo "[INFO]: Using $NUM_THREADS threads for feature extraction and matching."

colmap feature_extractor \
  --database_path "$DB" \
  --image_path "$IMAGES" \
  --ImageReader.camera_model "$CAMERA_MODEL" \
  --ImageReader.single_camera=true \
  --SiftExtraction.estimate_affine_shape="$EXTRA" \
  --SiftExtraction.domain_size_pooling="$EXTRA" \
  --FeatureExtraction.use_gpu="$USE_GPU" \
  --FeatureExtraction.num_threads="$NUM_THREADS"

colmap "${MATCHER}_matcher" \
  --database_path "$DB" \
  --FeatureMatching.guided_matching="$EXTRA" \
  --FeatureMatching.use_gpu="$USE_GPU" \
  --FeatureMatching.num_threads="$NUM_THREADS"

$MAPPER_CMD \
  --database_path "$DB" \
  --image_path "$IMAGES" \
  --output_path "$SPARSE"

canonicalize_sparse_model "$SPARSE"

colmap bundle_adjuster \
  --input_path "$SPARSE" \
  --output_path "$SPARSE"

if [ "$REFINE_PRINCIPAL_POINT" = true ]; then
  colmap bundle_adjuster \
    --input_path "$SPARSE" \
    --output_path "$SPARSE" \
    --BundleAdjustment.refine_principal_point=true
fi

if [ "$CONVERT_TXT" = true ]; then
  colmap model_converter \
    --input_path "$SPARSE" \
    --output_path "$SPARSE" \
    --output_type TXT
fi

if [ "$UNDISTORT" = true ]; then
  UNDISTORT_PATH="$(dirname "$DB")/undistorted"
  colmap image_undistorter \
    --image_path "$IMAGES" \
    --input_path "$SPARSE" \
    --output_path "$UNDISTORT_PATH"

  colmap model_converter \
  --input_path "$UNDISTORT_PATH/sparse" \
  --output_path "$UNDISTORT_PATH/sparse" \
  --output_type TXT
fi
