#!/usr/bin/env bash
set -e

if ! command -v ffmpeg &> /dev/null; then
  echo "[ERROR] ffmpeg could not be found"
  exit 1
fi

FPS=2
FPS_SET=false
FRAMES_TARGET=""
MAX_FRAMES=""
TIME_SLICE=""
HDR=false
OVERWRITE=false

function show_help {
  echo "Usage: $0 <video_path> [options]"
  echo
  echo "Options:"
  echo "  --image_path <path>        Set the path to the output directory for the images (default: <video_dir>/images)"
  echo "  --fps <value>              Set the frame rate for the extracted images (default: $FPS)"
  echo "  --frames <int>             Extract approximately this many frames across the video or time slice"
  echo "  --max-frames <int>         Cap extracted frames by lowering FPS only when needed"
  echo "  --time_slice <start,end>   Extract images between <start> and <end> seconds (e.g. --time_slice 10,20)"
  echo "  --hdr                      Convert HDR video to SDR"
  echo "  --overwrite                Overwrite existing images directory without confirmation"
  echo "  --help                     Show this help message and exit"
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

VIDEO_IN="$1"
if [[ ! -f "$VIDEO_IN" ]]; then
  echo "[ERROR] Video file '$VIDEO_IN' does not exist or is not readable"
  exit 1
fi
VIDEO_DIR="$(dirname "$VIDEO_IN")"
IMAGES="$VIDEO_DIR/images"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --images)
      IMAGES="$2"
      shift 2
    ;;
    --fps)
      FPS="$2"
      if ! [[ "$FPS" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo "[ERROR] FPS must be a numeric value"
        exit 1
      fi
      FPS_SET=true
      shift 2
    ;;
    --frames)
      FRAMES_TARGET="$2"
      if ! [[ "$FRAMES_TARGET" =~ ^[1-9][0-9]*$ ]]; then
        echo "[ERROR] frames must be a positive integer"
        exit 1
      fi
      shift 2
    ;;
    --max-frames)
      MAX_FRAMES="$2"
      if ! [[ "$MAX_FRAMES" =~ ^[1-9][0-9]*$ ]]; then
        echo "[ERROR] max-frames must be a positive integer"
        exit 1
      fi
      shift 2
    ;;
    --time_slice)
      TIME_SLICE="$2"
      IFS=',' read -r start end <<< "$TIME_SLICE"
      if ! [[ "$start" =~ ^[0-9]+(\.[0-9]+)?$ && "$end" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        echo "[ERROR] time_slice values must be numeric (e.g. --time_slice 10,20)"
        exit 1
      fi
      if ! awk -v start="$start" -v end="$end" 'BEGIN { exit !(end > start) }'; then
        echo "[ERROR] time_slice end must be greater than start"
        exit 1
      fi
      shift 2
    ;;
    --hdr)
      HDR=true
      shift
    ;;
    --overwrite)
      OVERWRITE=true
      shift
    ;;
    *)
      echo "Unknown option: $1"
      show_help
    ;;
  esac
done

if [[ -n "$FRAMES_TARGET" && "$FPS_SET" = true ]]; then
  echo "[ERROR] --fps and --frames cannot be used together" >&2
  exit 1
fi
if [[ -n "$FRAMES_TARGET" && -n "$MAX_FRAMES" ]]; then
  echo "[ERROR] --frames and --max-frames cannot be used together" >&2
  exit 1
fi

if [ -d "$IMAGES" ]; then
  if [ "$OVERWRITE" = false ]; then
    read -r -p "[WARNING] Directory '$IMAGES' already exists. Continue? (y/N): " confirm
    if ! [[ "$confirm" =~ ^[Yy]$ ]]; then
      exit 0
    fi
  else
    rm -rf "$IMAGES"
    mkdir -p "$IMAGES"
  fi
else
  mkdir -p "$IMAGES"
fi

if [[ -n "$FRAMES_TARGET" || -n "$MAX_FRAMES" ]]; then
  duration=""
  if [[ -n "$TIME_SLICE" ]]; then
    duration="$(awk -v start="$start" -v end="$end" 'BEGIN { printf "%.6f", end - start }')"
  else
    if ! command -v ffprobe &> /dev/null; then
      echo "[ERROR] ffprobe could not be found; frame budgeting requires ffprobe to read video duration"
      exit 1
    fi
    duration="$(ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 "$VIDEO_IN")"
  fi
fi
if [[ -n "$FRAMES_TARGET" ]]; then
  if ! FPS="$(awk -v frames="$FRAMES_TARGET" -v duration="$duration" 'BEGIN { if (duration <= 0) exit 1; printf "%.6f", frames / duration }')"; then
    echo "[ERROR] Could not calculate FPS for --frames $FRAMES_TARGET from duration '$duration'"
    exit 1
  fi
fi
if [[ -n "$MAX_FRAMES" ]]; then
  if ! FPS="$(awk -v fps="$FPS" -v frames="$MAX_FRAMES" -v duration="$duration" 'BEGIN { if (duration <= 0) exit 1; capped = frames / duration; if (fps * duration > frames) printf "%.6f", capped; else print fps }')"; then
    echo "[ERROR] Could not calculate FPS for --max-frames $MAX_FRAMES from duration '$duration'"
    exit 1
  fi
fi

time_slice_value=""
if [[ -n "$TIME_SLICE" ]]; then
  time_slice_value=",select='between(t,$start,$end)'"
fi

hdr_to_sdr=""
if [[ "$HDR" = true ]]; then
  hdr_to_sdr=",zscale=t=linear:npl=100,tonemap=hable:desat=0,zscale=transfer=bt709:matrix=bt709:primaries=bt709,format=yuv420p"
fi

echo "-----------------------------"
echo "Video input:    $VIDEO_IN"
echo "FPS:            $FPS"
[[ -n "$FRAMES_TARGET" ]] && echo "Frames target:  $FRAMES_TARGET"
[[ -n "$MAX_FRAMES" ]] && echo "Max frames:     $MAX_FRAMES"
[[ -n "$TIME_SLICE" ]] && echo "Time slice:     $TIME_SLICE"
$HDR && echo "HDR to SDR:     Enabled"
echo "Images dir:     $IMAGES"
echo "Overwrite dir:  $OVERWRITE"
echo "-----------------------------"

# Avoiding -fps_mode vfr for backward compatibility with older versions of ffmpeg
ffmpeg -i "$VIDEO_IN" -q:v 1 -qmin 1 -vsync vfr -vf "fps=$FPS$time_slice_value$hdr_to_sdr" "$IMAGES/%04d.jpg"
