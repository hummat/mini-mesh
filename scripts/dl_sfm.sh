#!/usr/bin/env bash
set -e

COLMAP_BINARY="colmap"
if ! command -v "$COLMAP_BINARY" &> /dev/null; then
  echo "[ERROR] COLMAP could not be found"
  exit 1
fi

function show_help {
    echo "Usage: $0 <path-to-images> [options]"
    echo
    echo "Options:"
    echo "  --method <method>          Method for SfM: hloc, vggsfm (default: hloc)"
    echo "  --help                     Show this help message and exit"
    echo
    echo "This script performs Structure-from-Motion (SfM) using Deep Learning methods."
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

IMAGES="$1"
if [ ! -d "$IMAGES" ]; then
    echo "[ERROR] Image directory does not exist: $IMAGES"
    exit 1
fi
DIR=$(dirname "$IMAGES")
METHOD="hloc"
shift

while [[ $# -gt 0 ]]; do
    case "$1" in
        --method)
            METHOD="$2"
            shift 2
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

# Attempt to use pyenv if available; otherwise fall back to conda
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init -)"
  # Check if the current pyenv environment matches 'sdfstudio'
  if ! pyenv which python | grep -q "sdfstudio"; then
      pyenv activate sdfstudio
  fi
  echo "[INFO] Using pyenv $(pyenv version-name)"
else
  echo "[INFO] Using conda"
  if ! command -v conda >/dev/null 2>&1; then
    echo "[ERROR] Neither pyenv nor conda found. Exiting."
    exit 1
  fi
  eval "$(conda shell.bash hook)"
  conda activate sdfstudio
fi

if [ "$METHOD" == hloc ]; then
  # Install Hierarchical-Localization (hloc)
  if ! pip show hloc > /dev/null 2>&1; then
    REPO_NAME=Hierarchical-Localization
    REPO_URL=https://github.com/cvg/Hierarchical-Localization
    if [ ! -d "$GIT_ROOT/$REPO_NAME" ]; then
      echo "Cloning $REPO_NAME from $REPO_URL into $GIT_ROOT"
      git -C "$GIT_ROOT" clone --recursive "$REPO_URL"
    else
      echo "Updating $REPO_NAME"
      git -C "$GIT_ROOT/$REPO_NAME" pull
    fi
    echo "Installing $REPO_NAME"
    pip install --use-pep517 -e "$GIT_ROOT/$REPO_NAME"
  fi
  ns-process-data images --data "$IMAGES" --output_dir "$DIR" --sfm-tool hloc --skip-image-processing
  mv "$DIR"/colmap/sparse/0 "$DIR"/sparse
  mv "$DIR"/sparse/database.db "$DIR"/database.db
elif [ "$METHOD" == vggsfm ]; then
  REPO_NAME=vggsfm
  if ! pip show vggsfm > /dev/null 2>&1; then
    REPO_URL=https://github.com/hummat/vggsfm.git
    if [ ! -d "$GIT_ROOT/$REPO_NAME" ]; then
      echo "Cloning $REPO_NAME from $REPO_URL into $GIT_ROOT"
      git -C "$GIT_ROOT" clone "$REPO_URL"
    else
      echo "Updating $REPO_NAME"
      git -C "$GIT_ROOT/$REPO_NAME" pull
    fi
    echo "Installing $REPO_NAME"
    pip install hydra-core==1.3.2 pycolmap==3.10.0 pyceres==2.3 poselib==2.0.4
    pip install --use-pep517 -e "$GIT_ROOT/$REPO_NAME"
  fi
  python "$GIT_ROOT/$REPO_NAME/video_demo.py" SCENE_DIR="$DIR" camera_type=SIMPLE_RADIAL
else
  echo "Unknown method: $METHOD. Supported methods are: hloc, vggsfm"
  exit 1
fi
