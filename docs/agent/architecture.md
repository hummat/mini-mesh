# Architecture

## Layout
```
.
├── AGENTS.md                 # agent instructions
├── CLAUDE.md                 # this repo's specific guidelines
├── scripts/                  # CLI entrypoints and orchestration
│   ├── run.sh                # single source of truth for pipeline
│   ├── train.sh              # config resolution and training dispatch
│   ├── export.sh             # mesh extraction and texturing
│   ├── ffmpeg.sh             # video frame extraction
│   ├── sfm.sh                # structure-from-motion (COLMAP/GLOMAP)
│   ├── dl_sfm.sh             # advanced SfM methods (hloc/vggsfm)
│   └── lint.sh               # runs all checks (shellcheck/ruff/pyright/pytest)
├── config/                   # training configurations
│   ├── defaults.sh           # base defaults for all model types
│   └── *.sh                  # model-specific configs (CONFIG=(...) arrays)
├── docker/                   # container runtime
│   ├── Dockerfile            # canonical image build
│   ├── run.sh                # docker wrapper around scripts/run.sh
│   └── Dockerfile_bak        # legacy backup (do not edit)
├── webui.py                  # Gradio UI (wraps scripts/run.sh)
├── web.py                    # alias to webui.py
├── pyproject.toml           # Python config (hatchling build, dev deps, tooling)
├── tests/                    # unit tests for webui.py
│   ├── conftest.py           # shared fixtures
│   └── test_webui.py         # command construction/validation tests
└── README.md                 # project documentation
```

## Package Manager
```bash
uv sync --group dev           # install deps from lock
uv run <cmd>                # run command in venv
```

## Pipeline Stages
The `run.sh` script orchestrates a 5-stage pipeline:
1. **video**: Extract frames from video (via `ffmpeg.sh`)
2. **sfm**: Structure-from-motion reconstruction (via `sfm.sh` or `dl_sfm.sh`)
3. **process**: Data preprocessing (masking, transforms.json generation)
4. **train**: Train 3D model (via `train.sh` dispatching to sdf-train or ns-train)
5. **export**: Extract and texture mesh (via `export.sh`)

## Single Source of Truth
- `scripts/run.sh` defines the complete pipeline contract: contexts, flags, skip/overwrite semantics
- All other entrypoints (`docker/run.sh`, `webui.py`) are thin wrappers around it
- Do not duplicate pipeline logic; extend `run.sh` patterns instead

## Configuration System
- Training configs are Bash arrays in `config/*.sh`: `CONFIG=(--flag1 value1 --flag2 value2 ...)`
- `scripts/train.sh` resolves config names and dispatches:
  - SDF models → `sdf-train` (SDFStudio)
  - NeRF/splat models → `ns-train` (Nerfstudio)
- `config/defaults.sh` provides base defaults for all model types

## Data Flow
```
video/images → ffmpeg.sh → images/ → sfm.sh → sparse/ → process → transforms.json
                                                              → images_masked/
                                                              → train/ → export → mesh.ply + textures
```
