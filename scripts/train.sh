#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/env.sh
source "$SCRIPT_DIR/env.sh"

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

CONFIG_DIR="$(dirname "$SCRIPT_DIR")/config"
MODEL_NAME="$1"
EXP_NAME="$2"
DATA_DIR="$3"

source_required_config() {
  local config_path="$1"
  # shellcheck disable=SC1090
  if ! source "$config_path"; then
    echo "[ERROR] Failed to source config file: $config_path" >&2
    exit 1
  fi
}

if [ "$MODEL_NAME" = splatfacto-w ]; then
  echo "[ERROR] splatfacto-w requires the plugin's splatfactow_dataparser and Phototourism/Nerf-W data layout." >&2
  echo "        mini-mesh produces Nerfstudio data; use --model splatfacto-w-light instead." >&2
  exit 1
fi

# CONFIG may refer to a file path or a named config in CONFIG_DIR.
CONFIG=()
CONFIG_NAME="${4:-}"
if [ -n "$CONFIG_NAME" ] && [ -f "$CONFIG_NAME" ]; then
  echo "[INFO] Using config file: $CONFIG_NAME"
  source_required_config "$CONFIG_NAME"
  shift 4
elif [ -n "$CONFIG_NAME" ] && [ -f "$CONFIG_DIR/$CONFIG_NAME.sh" ]; then
  echo "[INFO] Using config file $CONFIG_NAME.sh from $CONFIG_DIR"
  source_required_config "$CONFIG_DIR/$CONFIG_NAME.sh"
  shift 4
else
  if [ -n "$CONFIG_NAME" ] && [ "$CONFIG_NAME" != "$MODEL_NAME" ]; then
      echo "[ERROR] Config '$CONFIG_NAME' not found. Expected file path or $CONFIG_DIR/$CONFIG_NAME.sh" >&2
      exit 1
  elif [ -f "$CONFIG_DIR/$MODEL_NAME.sh" ]; then
      echo "[INFO] Using config file $MODEL_NAME.sh"
      source_required_config "$CONFIG_DIR/$MODEL_NAME.sh"
      if [ -n "$CONFIG_NAME" ]; then
        shift 4
      else
        shift 3
      fi
  else
      echo "[INFO] No config file found for $MODEL_NAME; using defaults only"
      if [ -n "$CONFIG_NAME" ]; then
        shift 4
      else
        shift 3
      fi
  fi
fi
source_required_config "$CONFIG_DIR/defaults.sh"  # Defines DEFAULTS and DATA_DEFAULTS arrays

# Route arguments to trainer (ARGS/CONFIG_ARGS) or dataparser (DATA_ARGS/DATA_CONFIG_ARGS)
route_args() {
  local -n _trainer_out=$1
  local -n _data_out=$2
  shift 2
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --downscale-factor|--scale-factor|--center-method|--auto-scale-poses|--orientation-method|--train-split-fraction)
        _data_out+=("$1")
        shift
        if [[ $# -gt 0 && ! "$1" =~ ^-- ]]; then
            _data_out+=("$1")
            shift
        fi
        ;;
      --*scale*|--*center*|--*orientation*|--*split*)
        echo "[WARNING] '$1' looks like a data argument but doesn't match known patterns. Routing to trainer." >&2
        _trainer_out+=("$1")
        shift
        ;;
      *)
        _trainer_out+=("$1")
        shift
        ;;
    esac
  done
}

ARGS=()
DATA_ARGS=()
route_args ARGS DATA_ARGS "$@"

# Also route CONFIG array (from config file) through the same logic
CONFIG_ARGS=()
DATA_CONFIG_ARGS=()
route_args CONFIG_ARGS DATA_CONFIG_ARGS "${CONFIG[@]}"

# Debug: show argument routing
[[ ${#DATA_ARGS[@]} -gt 0 ]] && echo "[DEBUG] Data args (CLI): ${DATA_ARGS[*]}"
[[ ${#DATA_CONFIG_ARGS[@]} -gt 0 ]] && echo "[DEBUG] Data args (config): ${DATA_CONFIG_ARGS[*]}"

if [[ "$MODEL_NAME" == *nerf* ]] || [[ "$MODEL_NAME" == *splat* ]] || [[ "$MODEL_NAME" == *ngp* ]]; then
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
    "${CONFIG_ARGS[@]}"
    "${ARGS[@]}"
    nerfstudio-data
    --data "$DATA_DIR"
    "${NS_DATA_DEFAULTS[@]}"
    "${DATA_CONFIG_ARGS[@]}"
    "${DATA_ARGS[@]}"
  )
else
  COMMAND=(
    sdf-train
    "$MODEL_NAME"
    --output-dir "$DATA_DIR/train"
    --experiment-name "$EXP_NAME"
    "${DEFAULTS[@]}"
    "${CONFIG_ARGS[@]}"
    "${ARGS[@]}"
    nerfstudio-data
    --data "$DATA_DIR"
    "${DATA_DEFAULTS[@]}"
    "${DATA_CONFIG_ARGS[@]}"
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

end_time="$(date +%s)"
echo
echo "Job ended on $(date)"
echo "Job execution took $((end_time - start_time)) seconds"
