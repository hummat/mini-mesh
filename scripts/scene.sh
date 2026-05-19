#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(dirname "$script_dir")"

usage() {
  cat <<EOF
Usage: scripts/scene.sh [options] VIDEO1 [VIDEO2 ...] -- PIPELINE_ARGS...

Assembles multiple videos of the same scene into one mini-mesh image dataset,
then runs scripts/run.sh or docker/run.sh once on the shared images directory.

Options:
  --runner <docker|local>  Runner to use (default: docker)
  --work-dir <dir>         Scene work directory; images are written to <dir>/images
  --overwrite              Rebuild assembled images and pass --overwrite to the pipeline
  -h, --help               Show this help

PIPELINE_ARGS may include an initial video context. Those video args are used
for every input video and are not forwarded to run.sh:

  scripts/scene.sh --work-dir /data/scene a.mp4 b.mp4 -- \\
    video --fps 4 \\
    sfm --method glomap process train --model splatfacto-mcmc export
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

shell_join() {
  local quoted_args=()
  local quoted_arg
  local arg
  for arg in "$@"; do
    printf -v quoted_arg "%q" "$arg"
    quoted_args+=("$quoted_arg")
  done
  local IFS=" "
  printf "%s" "${quoted_args[*]}"
}

runner="docker"
work_dir=""
overwrite=false
input_videos=()
pipeline_args=()
video_extensions=(mp4 mov m4v mkv avi webm)

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --runner)
      [[ $# -ge 2 ]] || die "--runner requires an argument"
      runner="$2"
      shift 2
      ;;
    --work-dir)
      [[ $# -ge 2 ]] || die "--work-dir requires an argument"
      work_dir="$2"
      shift 2
      ;;
    --overwrite)
      overwrite=true
      shift
      ;;
    --)
      shift
      pipeline_args=("$@")
      break
      ;;
    -*)
      die "Unknown option: $1"
      ;;
    *)
      input_videos+=("$1")
      shift
      ;;
  esac
done

[[ ${#input_videos[@]} -gt 0 ]] || die "Missing VIDEO paths"
[[ -n "$work_dir" ]] || die "--work-dir is required"
[[ ${#pipeline_args[@]} -gt 0 ]] || die "Missing PIPELINE_ARGS after --"

case "$runner" in
  docker)
    runner_cmd=("$repo_root/docker/run.sh")
    ;;
  local)
    runner_cmd=("$repo_root/scripts/run.sh")
    ;;
  *)
    die "--runner must be one of: docker, local"
    ;;
esac

is_video_path() {
  local lower_path="${1,,}"
  local extension
  for extension in "${video_extensions[@]}"; do
    if [[ "$lower_path" == *."$extension" ]]; then
      return 0
    fi
  done
  return 1
}

sanitize_stem() {
  local stem="$1"
  stem="${stem//[^A-Za-z0-9._-]/_}"
  stem="${stem##_}"
  stem="${stem%%_}"
  if [[ -z "$stem" ]]; then
    stem="video"
  fi
  printf "%s" "$stem"
}

parse_pipeline_args() {
  video_args=()
  forward_args=()
  local current_context="global"
  local seen_pipeline_context=false
  local arg

  for arg in "${pipeline_args[@]}"; do
    case "$arg" in
      video)
        if [[ "$seen_pipeline_context" = true ]]; then
          die "video context must appear before sfm/process/train/export"
        fi
        current_context="video"
        ;;
      sfm|process|train|export)
        seen_pipeline_context=true
        current_context="$arg"
        forward_args+=("$arg")
        ;;
      *)
        if [[ "$current_context" = video ]]; then
          video_args+=("$arg")
        else
          forward_args+=("$arg")
        fi
        ;;
    esac
  done
}

validate_video_args() {
  local arg
  for arg in "${video_args[@]}"; do
    case "$arg" in
      --images|--image_path)
        die "scene.sh controls the frame output directory; do not pass $arg in the video context"
        ;;
    esac
  done
}

clean_scene_outputs() {
  rm -rf \
    "$work_dir/images" \
    "$work_dir/images_orig" \
    "$work_dir/images_2" \
    "$work_dir/images_4" \
    "$work_dir/images_8" \
    "$work_dir/masks" \
    "$work_dir/sparse" \
    "$work_dir/colmap" \
    "$work_dir/hloc" \
    "$work_dir/.mini-mesh/video_frames"
  rm -f \
    "$work_dir/database.db" \
    "$work_dir/transforms.json" \
    "$work_dir/sparse_pc.ply" \
    "$work_dir/.mini-mesh/frame_sources.tsv"
}

assemble_images() {
  local images_dir="$work_dir/images"
  local state_dir="$work_dir/.mini-mesh"
  local frames_root="$state_dir/video_frames"
  local manifest="$state_dir/frame_sources.tsv"
  local video_path
  local video_name
  local video_stem
  local safe_stem
  local video_index=0
  local frame_index
  local temp_dir
  local frame_path
  local output_name
  local output_path
  local frames=()

  mkdir -p "$images_dir" "$frames_root"
  printf "image\tsource_video\tsource_frame\n" > "$manifest"

  for video_path in "${input_videos[@]}"; do
    video_index=$((video_index + 1))
    video_name="$(basename "$video_path")"
    video_stem="${video_name%.*}"
    safe_stem="$(sanitize_stem "$video_stem")"
    printf -v temp_dir "%s/%04d_%s" "$frames_root" "$video_index" "$safe_stem"
    rm -rf "$temp_dir"
    mkdir -p "$temp_dir"

    "$script_dir/ffmpeg.sh" "$video_path" --images "$temp_dir" --overwrite "${video_args[@]}"

    frames=()
    mapfile -d '' frames < <(find "$temp_dir" -maxdepth 1 -type f -name '*.jpg' -print0 | sort -z)
    [[ ${#frames[@]} -gt 0 ]] || die "No frames extracted from $video_path"

    frame_index=0
    for frame_path in "${frames[@]}"; do
      frame_index=$((frame_index + 1))
      printf -v output_name "%04d_%s_%04d.jpg" "$video_index" "$safe_stem" "$frame_index"
      output_path="$images_dir/$output_name"
      cp -p "$frame_path" "$output_path"
      printf "%s\t%s\t%s\n" "$output_name" "$video_path" "$(basename "$frame_path")" >> "$manifest"
    done
  done
}

for video_path in "${input_videos[@]}"; do
  [[ -f "$video_path" ]] || die "Video path does not exist or is not a file: $video_path"
  is_video_path "$video_path" || die "Unsupported video extension: $video_path"
done

parse_pipeline_args
validate_video_args

if [[ "$overwrite" = true ]]; then
  clean_scene_outputs
fi

if [[ ! -d "$work_dir/images" ]]; then
  assemble_images
else
  echo "[INFO]: Scene images $work_dir/images already exist; skipping assembly (use --overwrite to rebuild)"
fi

runner_args=("$work_dir/images")
if [[ "$overwrite" = true ]]; then
  runner_args+=("--overwrite")
fi
runner_args+=("${forward_args[@]}")

echo "============================="
echo "Scene:    $work_dir"
echo "Videos:   ${#input_videos[@]}"
echo "Runner:   $runner"
echo "Command:  $(shell_join "${runner_cmd[@]}" "${runner_args[@]}")"
echo "============================="
"${runner_cmd[@]}" "${runner_args[@]}"
