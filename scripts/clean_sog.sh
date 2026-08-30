#!/usr/bin/env bash
# Crop and clean splat captures for the blog.
#
# The blog ships .sog files, clean_splat.py speaks PLY, and splat-transform
# converts between the two. This driver runs the cleanup cascade per scene and
# writes a .sog per scene. Inputs may be .sog assets (converted to PLY first)
# or training-checkpoint PLYs (used directly, no quantization in the ancestry).
# With --ply-out-dir the cleaned PLY is also copied there for manual editing,
# which should always happen on the PLY: every extra sog->ply->sog round trip
# re-quantizes. Pass --skip-sog while a manual cleanup pass is pending so no
# .sog is written before the PLYs are final.
#
# Per-scene overrides come from a tab-separated manifest (scene<TAB>extra
# clean_splat.py arguments, with optional # comment lines); a scene's extra
# arguments are appended last and so override the default cascade. The
# manifest lives next to this script in git because the assets directory is
# not tracked.
#
# Usage:
#   clean_sog.sh --in-dir DIR --out-dir DIR [--manifest FILE] [--ply-out-dir DIR]
#     [--skip-sog] [--dry-run] [-- extra clean_splat.py arguments]
#
# The arguments after -- replace the built-in default cascade:
#   --crop-quantile 0.95 --opacity 0
#
# The default cascade is deliberately crop-only: it removes the background
# shell and nothing else. SOR and the scale quantile delete load-bearing
# surface splats (their removals have no surviving in-footprint coverage,
# which renders as holes), and manual cleanup can remove more but never
# recover.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
python="${MINI_MESH_PYTHON:-$repo_root/.venv/bin/python}"

usage() {
  echo "usage: $0 --in-dir DIR --out-dir DIR [--manifest FILE] [--ply-out-dir DIR] [--skip-sog] [--dry-run] [-- clean_splat.py args...]" >&2
}

in_dir=""
out_dir=""
ply_out_dir=""
manifest="$script_dir/sog-crops.tsv"
manifest_is_default=true
dry_run=false
skip_sog=false
cascade=(--crop-quantile 0.95 --opacity 0)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --in-dir)
      [[ $# -ge 2 ]] || { echo "[ERROR]: --in-dir needs a value" >&2; usage; exit 2; }
      in_dir="$2"; shift 2
      ;;
    --out-dir)
      [[ $# -ge 2 ]] || { echo "[ERROR]: --out-dir needs a value" >&2; usage; exit 2; }
      out_dir="$2"; shift 2
      ;;
    --ply-out-dir)
      [[ $# -ge 2 ]] || { echo "[ERROR]: --ply-out-dir needs a value" >&2; usage; exit 2; }
      ply_out_dir="$2"; shift 2
      ;;
    --manifest)
      [[ $# -ge 2 ]] || { echo "[ERROR]: --manifest needs a value" >&2; usage; exit 2; }
      manifest="$2"; manifest_is_default=false; shift 2
      ;;
    --skip-sog)
      skip_sog=true; shift
      ;;
    --dry-run)
      dry_run=true; shift
      ;;
    --)
      shift
      cascade=("$@")
      shift $#
      ;;
    *)
      echo "[ERROR]: unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ -n "$in_dir" && -n "$out_dir" ]] || { echo "[ERROR]: --in-dir and --out-dir are required" >&2; usage; exit 2; }
[[ -d "$in_dir" ]] || { echo "[ERROR]: --in-dir is not a directory: $in_dir" >&2; exit 2; }
[[ -x "$python" ]] || { echo "[ERROR]: python not found: $python (set MINI_MESH_PYTHON)" >&2; exit 2; }
if [[ "$manifest_is_default" == true && ! -f "$manifest" ]]; then
  manifest=""
fi

# Fill ROW with the manifest's extra arguments for a scene, empty if absent.
manifest_row() {
  local scene="$1" line rest
  ROW=()
  [[ -n "$manifest" ]] || return 0
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == "#"* ]] && continue
    [[ "${line%%$'\t'*}" == "$scene" ]] || continue
    rest="${line#*$'\t'}"
    if [[ "$rest" != "$line" && -n "${rest//[$'\t' ]/}" ]]; then
      read -ra ROW <<<"$rest"
    fi
    return 0
  done <"$manifest"
}

shopt -s nullglob
inputs=()
for pattern in "$in_dir"/*.sog "$in_dir"/*.ply; do
  inputs+=("$pattern")
done
shopt -u nullglob
if [[ ${#inputs[@]} -eq 0 ]]; then
  echo "[ERROR]: no .sog or .ply files in $in_dir" >&2
  exit 1
fi

mkdir -p "$out_dir"
if [[ -n "$ply_out_dir" && "$dry_run" == false ]]; then
  mkdir -p "$ply_out_dir"
fi
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT

mb() { awk -v b="$1" 'BEGIN { printf "%.1f MB", b / 1e6 }'; }

for input in "${inputs[@]}"; do
  name="$(basename "$input")"
  case "$name" in
    *.sog) scene="${name%.sog}" ;;
    *.ply) scene="${name%.ply}" ;;
  esac
  manifest_row "$scene"
  step_args=("${cascade[@]}" "${ROW[@]}")
  if [[ "$dry_run" == true ]]; then
    step_args+=(--dry-run)
  fi

  src_ply="$input"
  if [[ "$name" == *.sog ]]; then
    npx -y @playcanvas/splat-transform -w "$input" "$scratch/$scene.ply" >/dev/null
    src_ply="$scratch/$scene.ply"
  fi
  if ! clean_out="$("$python" "$script_dir/clean_splat.py" "$src_ply" \
      -o "$scratch/$scene.clean.ply" "${step_args[@]}" 2>&1)"; then
    echo "[ERROR]: clean_splat.py failed for $scene:" >&2
    echo "$clean_out" >&2
    exit 1
  fi

  kept="$(sed -n '/^\[clean\]: kept/s/.*(\([0-9.]*\)% of.*/\1/p' <<<"$clean_out")"
  in_size="$(stat -c%s "$input")"
  if [[ "$dry_run" == true ]]; then
    out_size="n/a"
  else
    if [[ -n "$ply_out_dir" ]]; then
      cp "$scratch/$scene.clean.ply" "$ply_out_dir/$scene.ply"
    fi
    if [[ "$skip_sog" == true ]]; then
      out_size="ply only"
    else
      npx -y @playcanvas/splat-transform -w "$scratch/$scene.clean.ply" "$out_dir/$scene.sog" >/dev/null
      out_size="$(mb "$(stat -c%s "$out_dir/$scene.sog")")"
    fi
  fi
  printf '%-24s kept %6s%%  %s -> %s\n' "$scene" "${kept:-?}" "$(mb "$in_size")" "$out_size"

  if [[ -n "$kept" ]]; then
    awk -v p="$kept" 'BEGIN { exit !(p < 50) }' \
      && echo "[warn]: $scene kept ${kept}%, tune it by hand" >&2 || true
  fi

  rm -f "$scratch/$scene.ply" "$scratch/$scene.clean.ply"
done
