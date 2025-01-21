#!/usr/bin/env bash
set -e

if ! command -v colmap &> /dev/null; then
  echo "[ERROR] COLMAP binary could not be found."
  exit 1
fi

CAMERA_MODEL="OPENCV"
MATCHER="sequential"
EXTRA=false
OVERWRITE=false
USE_GLOMAP=false

function show_help {
  echo "Usage: $0 <path-to-images> [options]"
  echo
  echo "Options:"
  echo "  --database_path <path>     Path to the COLMAP database file (default: <path-to-images>/../database.db)"
  echo "  --camera_model <model>     Camera model for feature extraction: SIMPLE_PINHOLE, PINHOLE, SIMPLE_RADIAL, RADIAL, OPENCV (default: OPENCV)"
  echo "  --matcher <type>           Matcher type: exhaustive, sequential, vocab_tree (default: sequential)"
  echo "  --extra                    Set additional arguments for improved feature extraction and matching. No GPU support (slow)."
  echo "  --overwrite                Overwrite existing sparse directory without confirmation"
  echo "  --use_glomap               Use GLOMAP mapper instead of COLMAP mapper if available"
  echo "  --help                     Show this help message and exit"
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
  echo "[ERROR] Image directory does not exist: $IMAGES"
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
    --overwrite)
      OVERWRITE=true
      shift
    ;;
    --use_glomap)
      USE_GLOMAP=true
      shift
    ;;
    --help)
      show_help
    ;;
    *)
      echo "Unknown option: $1"
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
    echo "[INFO] GPU detected. Using GPU for feature extraction and matching."
    fi
  fi
fi

MAPPER_CMD="colmap mapper"
if [ "$USE_GLOMAP" = true ]; then
  if command -v glomap &> /dev/null; then
    MAPPER_CMD="glomap mapper"
  else
    echo "[ERROR] GLOMAP binary could not be found."
    exit 1
  fi
fi

SPARSE="$(dirname "$DB")/sparse"
if [ -d "$SPARSE" ]; then
  if [ "$OVERWRITE" = false ]; then
    read -r -p "[WARNING] Directory '$SPARSE' already exists. Continue? (y/N): " confirm
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

NUM_THREADS=$(nproc --all)
if [ "$NUM_THREADS" -gt 16 ]; then
  NUM_THREADS=16
fi
echo "[INFO] Using $NUM_THREADS threads for feature extraction and matching."

colmap feature_extractor \
  --database_path "$DB" \
  --image_path "$IMAGES" \
  --ImageReader.camera_model "$CAMERA_MODEL" \
  --SiftExtraction.estimate_affine_shape="$EXTRA" \
  --SiftExtraction.domain_size_pooling="$EXTRA" \
  --SiftExtraction.use_gpu="$USE_GPU" \
  --ImageReader.single_camera=true \
  --SiftExtraction.num_threads="$NUM_THREADS"

colmap "${MATCHER}_matcher" \
  --database_path "$DB" \
  --SiftMatching.guided_matching="$EXTRA" \
  --SiftMatching.use_gpu="$USE_GPU" \
  --SiftMatching.num_threads="$NUM_THREADS"

$MAPPER_CMD \
  --database_path "$DB" \
  --image_path "$IMAGES" \
  --output_path "$SPARSE"

if [ -d "$SPARSE/1" ]; then
  colmap model_merger \
    --input_path1 "$SPARSE/0" \
    --input_path2 "$SPARSE/1" \
    --output_path "$SPARSE"
else
  mv "$SPARSE/0/"* "$SPARSE"
  rm -d "$SPARSE/0"
fi

colmap bundle_adjuster \
  --input_path "$SPARSE" \
  --output_path "$SPARSE"

colmap bundle_adjuster \
  --input_path "$SPARSE" \
  --output_path "$SPARSE" \
  --BundleAdjustment.refine_principal_point=true

colmap model_converter \
  --input_path "$SPARSE" \
  --output_path "$SPARSE" \
  --output_type TXT

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
