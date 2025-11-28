#!/usr/bin/env bash
set -e

function show_help {
  echo "Usage: $0 <path-to-images> [options]"
  echo
  echo "Options:"
  echo "  --method <str>                    Deep Learning SfM method: hloc, vggsfm (default: hloc)"
  echo "  --matcher <str>                   Matching method: exhaustive, sequential (default: sequential)"
  echo "  --hloc_feature <str>              HLoc feature extractor config. See hloc --help for available options (default: superpoint_aachen)"
  echo "  --hloc_matcher <str>              HLoc matcher config. See hloc --help for available options (default: superglue)"
  echo "  --hloc_weights <str>              HLoc matcher weights type: indoor, outdoor (default: outdoor)"
  echo "  --hloc_camera <str>               HLoc camera model: SIMPLE_PINHOLE, PINHOLE, SIMPLE_RADIAL, RADIAL, OPENCV, FISHEYE (default: OPENCV)"
  echo "  --vggsfm_max_points <int>         Maximum number of points for VGGSfM (default: 32768)"
  echo "  --vggsfm_max_tri_points <int>     Maximum number of triangulation points for VGGSfM (default: 16384)"
  echo "  --overwrite                       Overwrite existing sparse directory without confirmation"
  echo "  --help                            Show this help message and exit"
  echo
  echo "This script performs Structure-from-Motion (SfM) using Deep Learning methods."
  exit 0
}

if [ $# -eq 0 ]; then
  show_help
fi

for arg in "$@"; do
  if [ "$arg" == "--help" ]; then
    show_help
  fi
done

IMAGES="$1"
if [ ! -d "$IMAGES" ]; then
  echo "[ERROR]: Image directory does not exist: $IMAGES"
  exit 1
fi
DIR=$(dirname "$IMAGES")
METHOD="hloc"
MATCHER="sequential"
HLOC_FEATURE="superpoint_aachen"
HLOC_MATCHER="superglue"
HLOC_WEIGHTS="outdoor"
HLOC_CAMERA="OPENCV"
VGGSFM_MAX_POINTS=32768
VGGSFM_MAX_TRI_POINTS=16384
OVERWRITE=false
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --method)
      METHOD="$2"
      shift 2
    ;;
    --matcher)
      MATCHER="$2"
      shift 2
    ;;
    --hloc_feature)
      HLOC_FEATURE="$2"
      shift 2
    ;;
    --hloc_matcher)
      HLOC_MATCHER="$2"
      shift 2
    ;;
    --hloc_weights)
      HLOC_WEIGHTS="$2"
      shift 2
    ;;
    --hloc_camera)
      HLOC_CAMERA="$2"
      shift 2
    ;;
    --vggsfm_max_points)
      VGGSFM_MAX_POINTS="$2"
      shift 2
    ;;
    --vggsfm_max_tri_points)
      VGGSFM_MAX_TRI_POINTS="$2"
      shift 2
    ;;
    --overwrite)
      OVERWRITE=true
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

if [ -d "$DIR/sparse" ]; then
  if [ "$OVERWRITE" = true ] || { read -r -p "[WARNING]: Directory '$DIR/sparse' already exists. Continue? (y/N): " confirm && [[ "$confirm" =~ ^[Yy]$ ]]; }; then
    rm -rf "$DIR/sparse" "$DIR/database.db" "$DIR/hloc"
  else
    exit 0
  fi
fi

if [ "$METHOD" = hloc ]; then
  if ! command -v hloc >/dev/null 2>&1; then
    echo "[ERROR]: hloc not found in PATH"
    echo "         Please install hloc following the instructions in README.md:"
    echo "         pip install git+https://github.com/cvg/Hierarchical-Localization.git@abb252080282e31147db6291206ca102c43353f7"
    echo "         pip install git+https://github.com/hummat/hloc-cli.git@1d8fd95120a339b823e86006fd99cfd03be093e0"
    exit 1
  fi

  if [ "$MATCHER" != exhaustive ]; then
    MATCHER=retrieval
  fi
  NUM_THREADS=$(nproc --all)

  hloc --images "$IMAGES" \
       --feature "$HLOC_FEATURE" \
       --pairs "$MATCHER" \
       --matcher "$HLOC_MATCHER" \
       --matcher-weights "$HLOC_WEIGHTS" \
       --camera-model "$HLOC_CAMERA" \
       --num-threads "$NUM_THREADS"
elif [ "$METHOD" = vggsfm ]; then
  if ! command -v vggsfm-video >/dev/null 2>&1 || ! command -v vggsfm-image >/dev/null 2>&1; then
    echo "[ERROR]: vggsfm-video or vggsfm-image not found in PATH"
    echo "         Please install vggsfm following the instructions in README.md:"
    echo "         pip install git+https://github.com/hummat/vggsfm.git@3e0ec00464c5ec4640aa471b226703432bb1bfe7"
    exit 1
  fi

  if [ "$MATCHER" = sequential ]; then
    vggsfm-video SCENE_DIR="$DIR" \
      shared_camera=True \
      camera_type="SIMPLE_RADIAL" \
      max_tri_points_num="$VGGSFM_MAX_TRI_POINTS" \
      max_points_num="$VGGSFM_MAX_POINTS"
  elif [ "$MATCHER" = exhaustive ]; then
    vggsfm-image SCENE_DIR="$DIR" \
      shared_camera=True \
      camera_type="SIMPLE_RADIAL" \
      max_tri_points_num="$VGGSFM_MAX_TRI_POINTS" \
      max_points_num="$VGGSFM_MAX_POINTS"
  else
    echo "[ERROR]: Unknown matcher: $MATCHER. Supported matchers are: exhaustive, sequential"
    exit 1
  fi
  rm -rf video_demo.log demo.log .hydra
else
  echo "[ERROR]: Unknown method: $METHOD. Supported methods are: hloc, vggsfm"
  exit 1
fi
