#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(dirname "$script_dir")"

usage() {
  cat <<EOF
Usage: scripts/batch.sh [options] VIDEO_DIR -- PIPELINE_ARGS...
       scripts/batch.sh [options] VIDEO1 [VIDEO2 ...] -- PIPELINE_ARGS...

Runs mini-mesh once for each input video. A single directory input expands to
all top-level video files in that directory. Each video gets its own work
directory named after the video stem, then PIPELINE_ARGS are passed unchanged to
scripts/run.sh or docker/run.sh. Runs are sequential and stop on the first
failure.

Options:
  --runner <docker|local>  Runner to use (default: docker)
  --work-root <dir>        Parent directory for per-video work dirs (default: VIDEO_DIR)
  --copy                   Copy videos into work dirs instead of hardlinking
  -h, --help               Show this help

Example:
  scripts/batch.sh /data/videos -- \\
    video --fps 4 \\
    train --model splatfacto-mcmc --config splatfacto-mcmc-short --name sfmcmc --vis viewer \\
    export --obb-scale 1.5 1.5 1.0
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

runner="docker"
stage_mode="link"
work_root=""
input_paths=()
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
    --work-root)
      [[ $# -ge 2 ]] || die "--work-root requires an argument"
      work_root="$2"
      shift 2
      ;;
    --copy)
      stage_mode="copy"
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
      input_paths+=("$1")
      shift
      ;;
  esac
done

[[ ${#input_paths[@]} -gt 0 ]] || die "Missing VIDEO_DIR or VIDEO paths"
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

videos=()
if [[ ${#input_paths[@]} -eq 1 && -d "${input_paths[0]}" ]]; then
  video_dir="${input_paths[0]}"
  if [[ -z "$work_root" ]]; then
    work_root="$video_dir"
  fi

  candidates=()
  mapfile -d '' candidates < <(find "$video_dir" -maxdepth 1 -type f -print0 | sort -z)
  for candidate in "${candidates[@]}"; do
    if is_video_path "$candidate"; then
      videos+=("$candidate")
    fi
  done
else
  common_parent=""
  for input_path in "${input_paths[@]}"; do
    [[ -f "$input_path" ]] || die "Video path does not exist or is not a file: $input_path"
    is_video_path "$input_path" || die "Unsupported video extension: $input_path"
    videos+=("$input_path")
    input_parent="$(dirname "$input_path")"
    if [[ -z "$common_parent" ]]; then
      common_parent="$input_parent"
    elif [[ "$common_parent" != "$input_parent" ]]; then
      common_parent=""
      break
    fi
  done

  if [[ -z "$work_root" ]]; then
    [[ -n "$common_parent" ]] || die "--work-root is required when explicit video paths are from different directories"
    work_root="$common_parent"
  fi
fi

[[ ${#videos[@]} -gt 0 ]] || die "No videos found"
mkdir -p "$work_root"

declare -A seen_stems=()
for video_path in "${videos[@]}"; do
  video_name="$(basename "$video_path")"
  video_stem="${video_name%.*}"
  if [[ -n "${seen_stems[$video_stem]:-}" ]]; then
    die "Multiple videos share the stem '$video_stem': ${seen_stems[$video_stem]} and $video_path"
  fi
  seen_stems[$video_stem]="$video_path"
done

stage_video() {
  local video_path="$1"
  local work_video="$2"
  local tmp_video
  local work_dir
  work_dir="$(dirname "$work_video")"

  case "$stage_mode" in
    link)
      # The work video is a hardlink to the source; keep downstream stages read-only with respect to the input file.
      if [[ ! -e "$work_video" ]]; then
        ln "$video_path" "$work_video" \
          || die "Failed to hardlink $video_path into $work_dir. Use --copy for cross-filesystem batches."
      elif [[ ! "$work_video" -ef "$video_path" ]]; then
        die "Work video exists but is not the same file: $work_video"
      fi
      ;;
    copy)
      if [[ ! -e "$work_video" ]]; then
        tmp_video="$work_video.tmp.$$"
        cp -p "$video_path" "$tmp_video"
        mv "$tmp_video" "$work_video"
      elif [[ -f "$work_video" ]] && cmp -s "$video_path" "$work_video"; then
        :
      else
        die "Work video exists with different contents: $work_video"
      fi
      ;;
    *)
      die "Unsupported stage mode: $stage_mode"
      ;;
  esac
}

for video_path in "${videos[@]}"; do
  video_name="$(basename "$video_path")"
  video_stem="${video_name%.*}"
  work_dir="$work_root/$video_stem"
  work_video="$work_dir/$video_name"

  mkdir -p "$work_dir"
  stage_video "$video_path" "$work_video"

  echo "============================="
  echo "Running: $video_name"
  echo "Work dir: $work_dir"
  echo "Runner:   $runner"
  echo "============================="
  "${runner_cmd[@]}" "$work_video" "${pipeline_args[@]}"
done
