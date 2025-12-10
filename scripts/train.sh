#!/usr/bin/env bash
set -e

if [ $# -lt 3 ]; then
  echo "ERROR: Missing required arguments"
  echo "Usage: $0 MODEL_NAME EXP_NAME DATA_DIR [CONFIG] [additional args...]"
  exit 1
fi

start_time="$(date +%s)"
echo "============================="
echo "         JOB INFO            "
echo "============================="
echo "Job started on:    $start_time"
echo "Current directory: $(pwd)"
echo "Current user:      $(whoami)"
echo "Python version:    $(python -c 'import sys; print(sys.version)')"
echo "pip version:       $(pip --version)"

if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi
else
  echo "[ERROR] nvidia-smi not found, unable to display GPU status."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(dirname "$SCRIPT_DIR")/config"
MODEL_NAME="$1"
EXP_NAME="$2"
DATA_DIR="$3"
# CONFIG may refer to a file path or a named config in CONFIG_DIR.
CONFIG="$4"
if [ -f "$CONFIG" ]; then
  echo "[INFO] Using config file: $CONFIG"
  # shellcheck disable=SC1090
  source "$CONFIG"
  shift 4
elif [ -f "$CONFIG_DIR/$CONFIG.sh" ]; then
  echo "[INFO] Using config file $CONFIG.sh from $CONFIG_DIR"
  # shellcheck disable=SC1090
  source "$CONFIG_DIR/$CONFIG.sh"
  shift 4
else
  if [ -f "$CONFIG_DIR/$MODEL_NAME.sh" ]; then
      echo "[INFO] Using config file $MODEL_NAME.sh"
      # shellcheck disable=SC1090
      source "$CONFIG_DIR/$MODEL_NAME.sh"
  else
      echo "[INFO] No config file found"
      CONFIG=()
  fi
  shift 3
fi
# shellcheck disable=SC1091
source "$CONFIG_DIR/defaults.sh"  # Defines DEFAULTS and DATA_DEFAULTS arrays

ARGS=()
DATA_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --downscale-factor|--scale-factor|--center-method|--auto-scale-poses|--orientation-method|--train-split-fraction)
      DATA_ARGS+=("$1")
      shift
      if [[ $# -gt 0 && ! "$1" =~ ^-- ]]; then
          DATA_ARGS+=("$1")
          shift
      fi
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ "$MODEL_NAME" == neus2* ]]; then
  NEUS2_ROOT="${NEUS2_ROOT:-/opt/git/NeuS2}"
  if [ ! -d "$NEUS2_ROOT" ]; then
    echo "[ERROR] NeuS2 root not found. Set NEUS2_ROOT to your NeuS2 checkout or build the Docker image with NeuS2 support."
    exit 1
  fi

  CONVERTER="$SCRIPT_DIR/convert_studio_to_ngp.py"
  if [ ! -f "$CONVERTER" ]; then
    echo "[ERROR] NeuS2 converter not found at $CONVERTER"
    exit 1
  fi

  NEUS2_SCENE_JSON="$DATA_DIR/transform_neus2.json"
  echo "[INFO] Converting transforms.json for NeuS2 at $NEUS2_SCENE_JSON"
  python "$CONVERTER" --data-dir "$DATA_DIR" --output "$NEUS2_SCENE_JSON"

  COMMAND=(
    python
    "$NEUS2_ROOT/scripts/run.py"
    --scene "$NEUS2_SCENE_JSON"
    --name "$EXP_NAME"
    "${CONFIG[@]}"
    "${ARGS[@]}"
  )
elif [[ "$MODEL_NAME" == *nerf* ]] || [[ "$MODEL_NAME" == *splat* ]] || [[ "$MODEL_NAME" == *ngp* ]]; then
  if [[ "$MODEL_NAME" == *splat* ]]; then
    NS_DEFAULTS=("${SPLAT_DEFAULTS[@]}")
  else
    NS_DEFAULTS=("${NERF_DEFAULTS[@]}")
  fi
  COMMAND=(
    ns-train
    "$MODEL_NAME"
    --output-dir "$DATA_DIR/train"
    --experiment-name "$EXP_NAME"
    "${NS_DEFAULTS[@]}"
    "${CONFIG[@]}"
    "${ARGS[@]}"
    nerfstudio-data
    --data "$DATA_DIR"
    "${NS_DATA_DEFAULTS[@]}"
    "${DATA_ARGS[@]}"
  )
else
  COMMAND=(
    sdf-train
    "$MODEL_NAME"
    --output-dir "$DATA_DIR/train"
    --experiment-name "$EXP_NAME"
    "${DEFAULTS[@]}"
    "${CONFIG[@]}"
    "${ARGS[@]}"
    nerfstudio-data
    --data "$DATA_DIR"
    "${DATA_DEFAULTS[@]}"
    "${DATA_ARGS[@]}"
  )
fi

if [ -z "$SLURM_JOB_NAME" ]; then
  echo "[INFO] Running LOCALLY with COMMAND:" "${COMMAND[@]}"
  "${COMMAND[@]}"
else
  echo "============================="
  echo "        SLURM INFO           "
  echo "============================="
  echo "Node List:         $SLURM_NODELIST"
  echo "Job ID:            $SLURM_JOB_ID"
  echo "Job Name:          $SLURM_JOB_NAME"
  echo "Partition:         $SLURM_JOB_PARTITION"
  echo "Submit directory:  $SLURM_SUBMIT_DIR"
  echo "Submit host:       $SLURM_SUBMIT_HOST"
  echo "Nodes:             $SLURM_JOB_NUM_NODES"
  echo "Tasks per node:    $SLURM_NTASKS_PER_NODE"
  if [ "$SLURM_JOB_NAME" = "interactive" ]; then
    echo "[INFO] Running INTERACTIVELY with COMMAND:" "${COMMAND[@]}"
    "${COMMAND[@]}"
  else
    echo "[INFO] Running on SLURM with COMMAND: srun" "${COMMAND[@]}"
    srun "${COMMAND[@]}"
  fi
fi

if [[ "$MODEL_NAME" == neus2* ]]; then
  EXP_DIR="$DATA_DIR/train/$EXP_NAME/$MODEL_NAME"
  NEUS2_MESH_DIR="$(pwd)/output/$EXP_NAME/mesh"
  mkdir -p "$EXP_DIR"
  if [ -d "$NEUS2_MESH_DIR" ]; then
    last_mesh=$(ls -1 "$NEUS2_MESH_DIR"/*.obj 2>/dev/null | sort | tail -n 1 || true)
    if [ -n "$last_mesh" ]; then
      cp "$last_mesh" "$EXP_DIR/mesh.obj"
    else
      echo "[ERROR] NeuS2 mesh .obj not found in $NEUS2_MESH_DIR"
      exit 1
    fi
  else
    echo "[ERROR] NeuS2 output directory not found: $NEUS2_MESH_DIR"
    exit 1
  fi
fi

end_time="$(date +%s)"
echo
echo "Job ended on $(date)"
echo "Job execution took $((end_time - start_time)) seconds"
