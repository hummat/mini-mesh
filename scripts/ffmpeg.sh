#!/usr/bin/env bash
set -e

if ! command -v ffmpeg &> /dev/null; then
    echo "[ERROR] ffmpeg could not be found"
    exit 1
fi

FPS=2
TIME_SLICE=""
HDR=false
OVERWRITE=false

function show_help {
    echo "Usage: $0 <video_path> [options]"
    echo
    echo "Options:"
    echo "  --image_path <path>        Set the path to the output directory for the images (default: <video_dir>/images)"
    echo "  --fps <value>              Set the frame rate for the extracted images (default: $FPS)"
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
            shift 2
        ;;
        --time_slice)
            TIME_SLICE="$2"
            IFS=',' read -r start end <<< "$TIME_SLICE"
            if ! [[ "$start" =~ ^[0-9]+(\.[0-9]+)?$ && "$end" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
                echo "[ERROR] time_slice values must be numeric (e.g. --time_slice 10,20)"
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

if [ -d "$IMAGES" ]; then
    if [ "$OVERWRITE" = false ]; then
        read -r -p "[WARNING] Directory '$IMAGES' already exists. Continue? (y/N): " confirm
        if ! [[ "$confirm" =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
else
    mkdir -p "$IMAGES"
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
[[ -n "$TIME_SLICE" ]] && echo "Time slice:     $TIME_SLICE"
$HDR && echo "HDR to SDR:     Enabled"
echo "Images dir:     $IMAGES"
echo "Overwrite dir:  $OVERWRITE"
echo "-----------------------------"

# Avoiding -fps_mode vfr for backward compatibility with older versions of ffmpeg
ffmpeg -i "$VIDEO_IN" -q:v 1 -qmin 1 -vsync vfr -vf "fps=$FPS$time_slice_value$hdr_to_sdr" "$IMAGES/%04d.jpg"
