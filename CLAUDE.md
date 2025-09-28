# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mini-mesh** is a sophisticated 3D reconstruction pipeline that creates detailed, textured 3D meshes of objects (like tabletop miniatures) from short smartphone videos or image sequences. The project leverages advanced computer vision and machine learning techniques to provide an accessible, GPU-accelerated solution for 3D content creation.

**Author:** Matthias Humt
**License:** MIT License
**Primary Language:** Bash & Python
**Main Framework:** Docker-based deployment with PyTorch neural networks

## Build/Development Commands

### Installation Methods

**1. Docker (Recommended):**
```bash
# Quick start with Docker
docker/run.sh /path/to/video/or/images

# Build custom Docker image (if needed)
docker build -t hummat/mini-mesh -f docker/Dockerfile \
    --build-arg CUDA_ARCHITECTURES=<YOUR-CC> \
    --build-arg MARCH_NATIVE=ON .
```

**2. Manual Installation:**
```bash
# Install Python 3.10, PyTorch 2.4.0, CUDA 12.4.1, COLMAP, GLOMAP, and SDFStudio
pip install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu124
pip install git+https://github.com/NVlabs/tiny-cuda-nn/#subdirectory=bindings/torch
pip install git+https://github.com/hummat/sdfstudio
```

### Usage Commands

**Basic Workflow:**
```bash
# Default usage (Docker)
docker/run.sh /path/to/video/or/images

# With custom settings
docker/run.sh /path/to/video/video.mp4 video --fps 1 sfm --use_glomap train --model neus-facto --config neus-facto-fast --vis wandb

# Manual execution
scripts/run.sh /path/to/video/video.mp4 video --fps 1 sfm --use_glomap train --model neus-facto

# Web interface
python web.py
```

**Individual Steps:**
```bash
# Video processing
scripts/ffmpeg.sh /path/to/video/video.mp4 --fps 2

# Structure-from-Motion
scripts/sfm.sh /path/to/images/ --camera_model SIMPLE_RADIAL --matcher exhaustive

# Training
scripts/train.sh neus my-experiment /path/to/data neus-grid-dev --vis tensorboard

# Web interface only
python web.py
```

**Configuration Options:**
- `--show`: Show COLMAP GUI after SfM completes
- `--verbose`: Enable verbose output
- `--overwrite`: Overwrite all existing results
- `--skip`: Skip individual pipeline steps
- `--fps`: Set video frame extraction rate
- `--model`: Choose neural model (neus, neus-facto, neuralangelo)
- `--config`: Select training configuration

## High-Level Architecture

### Core Functionality
The mini-mesh pipeline performs a 5-step automated 3D reconstruction workflow:

1. **Video Processing (video)**: Extracts frames from input videos using ffmpeg
2. **Structure-from-Motion (SfM)**: Estimates camera poses using COLMAP, GLOMAP, HLoc, or VGG-SFM
3. **Data Processing**: Prepares data for training using ns-process-data
4. **Neural Training (train)**: Reconstructs 3D mesh using deep learning models
5. **Mesh Export (export)**: Extracts and textures the final 3D mesh

### Key Architectural Components

**Pipeline Orchestration:**
- `scripts/run.sh` - Main workflow orchestrator (319 lines) with context-aware argument parsing
- Modular pipeline design where each step can be individually controlled
- State management for skipping completed steps

**Configuration System:**
- Bash array-based configuration in `config/` directory
- 18 different configuration files for various model variants
- Hierarchical configuration with defaults and model-specific overrides
- Models supported: NeuS, NeuS-Facto, Neuralangelo

**Web Interface:**
- Gradio-based web interface in `web.py`
- Real-time command execution with streaming output
- Comprehensive GUI controls for all pipeline parameters

### Docker Architecture
- Multi-stage Docker build with optimized layers
- CUDA architecture-specific builds (61;70;75;80;86;89)
- GPU acceleration via NVIDIA Container Toolkit
- Port 7007 for web interface access

## Key Technologies and Frameworks Used

### Core Technologies
- **Python 3.10**: Primary programming language for web interface
- **Bash**: Main shell scripts for pipeline orchestration
- **Docker**: Containerization for easy deployment and reproducibility
- **NVIDIA CUDA**: GPU acceleration for neural networks

### Machine Learning/AI Stack
- **PyTorch 2.4.0**: Deep learning framework
- **tiny-cuda-nn**: CUDA-accelerated neural network bindings
- **SDFStudio (hummat fork)**: Neural 3D reconstruction framework
- **NERF-based models**: NeuS, NeuS-Facto, Neuralangelo
- **Hash-encoded neural representations**: For efficient 3D scene representation

### Computer Vision/3D Processing
- **COLMAP**: Structure-from-Motion and multi-view stereo
- **GLOMAP**: Global optimization for SfM
- **HLoc/VGG-SFM**: Deep learning-based SfM methods
- **PoseLib**: Camera pose optimization
- **FFmpeg**: Video processing and frame extraction

## Development Guidelines

### Architecture Patterns
- **Modular Pipeline Design**: Each step is a separate, configurable component
- **Context-based Argument Parsing**: Different argument contexts for each pipeline step
- **Error Handling**: Comprehensive validation with early termination
- **SLURM Support**: Built-in support for HPC cluster execution
- **Docker-First Design**: Container deployment recommended for consistency

### Configuration Management
- **Bash Array Configuration**: All training parameters organized in Bash arrays
- **Hierarchical Configuration**: Defaults can be overridden by model-specific configs
- **Environment Variables**: Support for custom environment settings
- **SLURM Integration**: Automatic SLURM environment detection

### Script Design Principles
- **Robust Argument Parsing**: Context-sensitive argument validation
- **Progressive Step Execution**: Each pipeline step can be individually controlled
- **Comprehensive Logging**: Detailed output and progress reporting
- **Flexible Input Handling**: Supports both videos and image sequences
- **State Management**: Skips completed steps unless overridden

### Performance Considerations
- **GPU Memory**: Configurable ray chunking (1024-8192 rays per chunk)
- **Training Time**: Varies from 20k-100k iterations based on model
- **Image Resolution**: Automatic downscaling support for efficiency
- **Model Size**: Different model variants for different accuracy/speed trade-offs

### Hardware Requirements
- Minimum 24GB VRAM recommended for default settings
- Can be configured for lower VRAM (12GB) with adjusted ray batching
- Objects should fill bounding box of +/-1 for optimal results

## Troubleshooting and Performance

### Common Issues
- **CUDA Out of Memory**: Adjust ray chunking parameters (2048 or lower for 12GB VRAM)
- **SfM Failures**: Multiple fallback methods (exhaustive matcher, GLOMAP, HLoc)
- **Training Convergence**: Model-specific configuration suggestions
- **Texture Quality**: Model configuration for reflective/transparent surfaces

### Configuration Examples
For low VRAM systems:
```bash
--pipeline.model.eval-num-rays-per-chunk 2048
--pipeline.datamanager.train-num-rays-per-batch 2048
--pipeline.datamanager.eval-num-rays-per-batch 2048
```

For challenging surfaces:
```bash
--pipeline.datamanager.camera-optimizer.mode SO3xR3
--pipeline.model.sdf-field.use-diffuse-color True
--pipeline.model.sdf-field.use-specular-tint True
```

The modular design and comprehensive configuration system make this a robust platform for 3D reconstruction research and production usage.