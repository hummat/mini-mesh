"""Web UI for mini-mesh video to 3D mesh pipeline."""

import re
import shlex
from typing import Optional

import gradio as gr  # type: ignore[import-not-found]


def test_cmd(cmd: str, run_cmd: str) -> Optional[str]:
    """
    Validate command syntax and arguments.

    Args:
        cmd: Full command string to validate
        run_cmd: Expected command prefix (e.g., "scripts/run.sh")

    Returns:
        None if valid, error message string if invalid
    """
    # Validate global arguments
    allowed_global_args = ["--show", "--verbose", "--overwrite", "--shared", "--mail"]
    pattern = rf"{run_cmd}\s+(.*?)(?=\s+(video|sfm|process|train|export)\b|$)"
    match = re.search(pattern, cmd)
    if match:
        global_args = [arg for arg in match.group(1).strip().split() if arg.startswith("--")]
        for arg in global_args:
            if not any(arg.startswith(allowed) for allowed in allowed_global_args):
                return f"Invalid global argument: {arg}"

    # Validate video context arguments
    allowed_video_args = ["--fps", "--time_slice", "--hdr", "--skip", "--overwrite"]
    video_pattern = r"video\s+(.*?)(?=\s+(sfm|process|train|export)\b|$)"
    video_match = re.search(video_pattern, cmd)
    if video_match:
        video_args = [arg for arg in video_match.group(1).strip().split() if arg.startswith("--")]
        for arg in video_args:
            if not any(arg.startswith(allowed) for allowed in allowed_video_args):
                return f"Invalid video argument: {arg}"

    # Validate sfm context arguments
    allowed_sfm_args = [
        "--method",
        "--matcher",
        "--camera_model",
        "--extra",
        "--num_threads",
        "--refine_principal_point",
        "--vggsfm_max_points",
        "--vggsfm_max_tri_points",
        "--hloc_camera",
        "--hloc_feature",
        "--hloc_matcher",
        "--hloc_weights",
        "--skip",
        "--overwrite",
    ]
    sfm_pattern = r"sfm\s+(.*?)(?=\s+(process|train|export)\b|$)"
    sfm_match = re.search(sfm_pattern, cmd)
    if sfm_match:
        sfm_args = [arg for arg in sfm_match.group(1).strip().split() if arg.startswith("--")]
        for arg in sfm_args:
            if not any(arg.startswith(allowed) for allowed in allowed_sfm_args):
                return f"Invalid sfm argument: {arg}"

    # Validate process context arguments
    allowed_process_args = [
        "--min-match-ratio",
        "--crop-factor",
        "--mask",
        "--skip",
        "--overwrite",
    ]
    process_pattern = r"process\s+(.*?)(?=\s+(train|export)\b|$)"
    process_match = re.search(process_pattern, cmd)
    if process_match:
        process_args = [
            arg for arg in process_match.group(1).strip().split() if arg.startswith("--")
        ]
        for arg in process_args:
            if not any(arg.startswith(allowed) for allowed in allowed_process_args):
                return f"Invalid process argument: {arg}"

    # Validate train context arguments
    allowed_train_args = [
        "--model",
        "--config",
        "--name",
        "--vis",
        "--downscale-factor",
        "--scale-factor",
        "--center-method",
        "--orientation-method",
        "--auto-scale-poses",
        "--train-split-fraction",
        "--pipeline.model.eval-num-rays-per-chunk",
        "--pipeline.datamanager.train-num-rays-per-batch",
        "--pipeline.datamanager.eval-num-rays-per-batch",
        "--pipeline.datamanager.camera-optimizer.mode",
        "--pipeline.model.sdf-field.use-reflections",
        "--pipeline.model.sdf-field.use-n-dot-v",
        "--pipeline.model.sdf-field.use-diffuse-color",
        "--pipeline.model.sdf-field.use-specular-tint",
        "--pipeline.model.sdf-field.use-appearance-embedding",
        "--pipeline.model.sdf-field.enable-pred-roughness",
        "--pipeline.model.orientation-loss-mult",
        "--pipeline.model.distortion-loss-mult",
        "--logging.local-writer.enable",
        "--viewer.quit-on-train-completion",
        "--skip",
        "--overwrite",
    ]
    train_pattern = r"train\s+(.*?)(?=\s+(export)\b|$)"
    train_match = re.search(train_pattern, cmd)
    if train_match:
        train_args = [arg for arg in train_match.group(1).strip().split() if arg.startswith("--")]
        for arg in train_args:
            if not any(arg.startswith(allowed) for allowed in allowed_train_args):
                return f"Invalid train argument: {arg}"

    # Validate export context arguments
    allowed_export_args = [
        "--resolution",
        "--marching-cube-threshold",
        "--num-pixels-per-side",
        "--px-per-uv-triangle",
        "--downscale-factor",
        "--method",
        "--target-num-faces",
        "--bounding-box-min",
        "--bounding-box-max",
        "--obb-center",
        "--obb-scale",
        "--mesh-only",
        "--texture-only",
        "--input-mesh-filename",
        "--skip",
        "--overwrite",
    ]
    export_pattern = r"export\s+(.*?)$"
    export_match = re.search(export_pattern, cmd)
    if export_match:
        export_args = [arg for arg in export_match.group(1).strip().split() if arg.startswith("--")]
        for arg in export_args:
            if not any(arg.startswith(allowed) for allowed in allowed_export_args):
                return f"Invalid export argument: {arg}"

    return None


def run_pipeline(
    input_path: Optional[str] = None,
    mode: str = "local",
    # Global args
    global_show: bool = False,
    global_verbose: bool = False,
    global_overwrite: bool = False,
    # Video context
    video_enable: bool = False,
    video_fps: Optional[int] = None,
    video_time_slice: Optional[str] = None,
    video_hdr: bool = False,
    video_skip: bool = False,
    video_overwrite: bool = False,
    # SfM context
    sfm_enable: bool = False,
    sfm_method: Optional[str] = None,
    sfm_matcher: Optional[str] = None,
    sfm_camera_model: Optional[str] = None,
    sfm_extra: bool = False,
    sfm_refine_principal_point: Optional[bool] = None,
    sfm_num_threads: Optional[int] = None,
    sfm_hloc_feature: Optional[str] = None,
    sfm_hloc_matcher: Optional[str] = None,
    sfm_hloc_weights: Optional[str] = None,
    sfm_hloc_camera: Optional[str] = None,
    sfm_vggsfm_max_points: Optional[int] = None,
    sfm_vggsfm_max_tri_points: Optional[int] = None,
    sfm_skip: bool = False,
    sfm_overwrite: bool = False,
    # Process context
    process_enable: bool = False,
    process_mask: Optional[str] = None,
    process_crop_factor: Optional[float] = None,
    process_min_match_ratio: Optional[float] = None,
    process_skip: bool = False,
    process_overwrite: bool = False,
    # Train context
    train_enable: bool = False,
    train_model: Optional[str] = None,
    train_config: Optional[str] = None,
    train_name: Optional[str] = None,
    train_vis: Optional[str] = None,
    train_downscale_factor: Optional[int] = None,
    train_scale_factor: Optional[float] = None,
    train_center_method: Optional[str] = None,
    train_orientation_method: Optional[str] = None,
    train_auto_scale_poses: Optional[str] = None,
    train_split_fraction: Optional[float] = None,
    train_eval_num_rays_per_chunk: Optional[int] = None,
    train_train_num_rays_per_batch: Optional[int] = None,
    train_eval_num_rays_per_batch: Optional[int] = None,
    train_camera_optimizer_mode: Optional[str] = None,
    train_use_reflections: bool = False,
    train_use_diffuse_specular: bool = False,
    train_enable_pred_roughness: bool = False,
    train_orientation_loss_mult: Optional[float] = None,
    train_distortion_loss_mult: Optional[float] = None,
    train_disable_appearance_embedding: bool = False,
    train_viewer_quit_on_completion: bool = False,
    train_skip: bool = False,
    train_overwrite: bool = False,
    # Export context
    export_enable: bool = False,
    export_resolution: Optional[int] = None,
    export_method: Optional[str] = None,
    export_marching_cube_threshold: Optional[float] = None,
    export_num_pixels_per_side: Optional[int] = None,
    export_target_num_faces: Optional[int] = None,
    export_px_per_uv_triangle: Optional[int] = None,
    export_obb_center_x: Optional[float] = None,
    export_obb_center_y: Optional[float] = None,
    export_obb_center_z: Optional[float] = None,
    export_obb_scale_x: Optional[float] = None,
    export_obb_scale_y: Optional[float] = None,
    export_obb_scale_z: Optional[float] = None,
    export_downscale_factor: Optional[int] = None,
    export_mesh_only: bool = False,
    export_texture_only: bool = False,
    export_input_mesh_filename: Optional[str] = None,
    export_skip: bool = False,
    export_overwrite: bool = False,
    # Extra args (verbatim, expert use)
    sfm_extra_args: Optional[str] = None,
    process_extra_args: Optional[str] = None,
    train_extra_args: Optional[str] = None,
    export_extra_args: Optional[str] = None,
) -> str:
    """
    Build command string for running the pipeline.

    Args:
        input_path: Path to video file or image directory
        mode: Execution mode ("local" or "docker")
        global_show: Show intermediate results
        global_verbose: Verbose output
        global_overwrite: Overwrite existing outputs
        video_enable: Enable video context
        video_fps: Frames per second for video extraction
        video_time_slice: Time slice for video (e.g., "0:10")
        video_hdr: Enable HDR processing
        video_skip: Skip video processing
        video_overwrite: Overwrite video outputs
        sfm_enable: Enable SfM context
        sfm_method: SfM method (colmap, glomap, etc.)
        sfm_matcher: Feature matcher
        sfm_camera_model: Camera model for SfM
        sfm_extra: Enable extra SfM options (heavier, CPU-heavy)
        sfm_refine_principal_point: Whether to refine principal point
        sfm_num_threads: Number of threads for SfM
        sfm_hloc_feature: HLoc feature extractor name
        sfm_hloc_matcher: HLoc matcher name
        sfm_hloc_weights: HLoc matcher weights (indoor/outdoor)
        sfm_hloc_camera: HLoc camera model
        sfm_vggsfm_max_points: VGGSfM max points
        sfm_vggsfm_max_tri_points: VGGSfM max triangle points
        sfm_skip: Skip SfM processing
        sfm_overwrite: Overwrite SfM outputs
        process_enable: Enable process context
        process_mask: Background masking method (rembg, sam2)
        process_crop_factor: Crop factor for processing
        process_min_match_ratio: Minimum match ratio
        process_skip: Skip processing
        process_overwrite: Overwrite process outputs
        train_enable: Enable train context
        train_model: Model to train (neus-facto, etc.)
        train_config: Training config
        train_name: Experiment name
        train_vis: Visualization method (viewer, tensorboard, wandb)
        train_downscale_factor: Image downscale factor for training data
        train_scale_factor: Scene scale factor
        train_center_method: Pose centering method
        train_orientation_method: Pose orientation method
        train_auto_scale_poses: Auto scale poses mode
        train_split_fraction: Train/validation split fraction
        train_eval_num_rays_per_chunk: Rays per eval chunk
        train_train_num_rays_per_batch: Rays per training batch
        train_eval_num_rays_per_batch: Rays per eval batch
        train_camera_optimizer_mode: Camera optimizer mode (e.g. SO3xR3)
        train_use_reflections: Enable SDF reflection model
        train_use_diffuse_specular: Enable diffuse+specular SDF colors
        train_enable_pred_roughness: Enable PBR roughness prediction
        train_orientation_loss_mult: Ref-NeRF orientation loss multiplier
        train_distortion_loss_mult: Mip-NeRF 360 distortion loss multiplier
        train_disable_appearance_embedding: Disable appearance embedding
        train_viewer_quit_on_completion: Close viewer when training ends
        train_skip: Skip training
        train_overwrite: Overwrite training outputs
        export_enable: Enable export context
        export_resolution: Export resolution
        export_method: NeRF export method (poisson, tsdf, pointcloud, gaussian-splat)
        export_marching_cube_threshold: Marching cubes isosurface threshold
        export_num_pixels_per_side: Texture resolution in pixels per side
        export_target_num_faces: Target number of faces for simplification
        export_px_per_uv_triangle: Pixels per UV triangle for UV baking
        export_obb_center_x/y/z: Oriented bounding-box center components
        export_obb_scale_x/y/z: Oriented bounding-box scale components
        export_downscale_factor: Downscale factor for TSDF export
        export_mesh_only: SDF only: extract mesh but skip texturing
        export_texture_only: SDF only: texture an existing mesh, skip extraction
        export_input_mesh_filename: SDF only: custom mesh file for texturing
        export_skip: Skip export
        export_overwrite: Overwrite export outputs
        sfm_extra_args: Additional SfM args (verbatim, expert use)
        process_extra_args: Additional process args (verbatim, expert use)
        train_extra_args: Additional train args (verbatim, expert use)
        export_extra_args: Additional export args (verbatim, expert use)

    Returns:
        Command string to execute, or empty string if invalid
    """
    if not input_path:
        return ""

    # Select run script based on mode
    run_script = "docker/run.sh" if mode == "docker" else "scripts/run.sh"

    # Quote path if it contains spaces
    if " " in input_path:
        input_path = f'"{input_path}"'

    cmd_parts = [run_script, input_path]

    # Add global args
    if global_show:
        cmd_parts.append("--show")
    if global_verbose:
        cmd_parts.append("--verbose")
    if global_overwrite:
        cmd_parts.append("--overwrite")

    # Add video context
    if video_enable:
        cmd_parts.append("video")
        if video_fps is not None:
            cmd_parts.extend(["--fps", str(video_fps)])
        if video_time_slice:
            cmd_parts.extend(["--time_slice", video_time_slice])
        if video_hdr:
            cmd_parts.append("--hdr")
        if video_skip:
            cmd_parts.append("--skip")
        if video_overwrite:
            cmd_parts.append("--overwrite")

    # Add sfm context
    if sfm_enable:
        cmd_parts.append("sfm")
        if sfm_method:
            cmd_parts.extend(["--method", sfm_method])
        if sfm_matcher and sfm_matcher != "sequential":
            cmd_parts.extend(["--matcher", sfm_matcher])
        if sfm_camera_model and sfm_camera_model != "OPENCV":
            cmd_parts.extend(["--camera_model", sfm_camera_model])
        if sfm_extra:
            cmd_parts.append("--extra")
        if sfm_refine_principal_point is not None and sfm_refine_principal_point is not True:
            cmd_parts.extend(
                ["--refine_principal_point", "True" if sfm_refine_principal_point else "False"]
            )
        if sfm_num_threads is not None and sfm_num_threads > 0:
            cmd_parts.extend(["--num_threads", str(sfm_num_threads)])
        if sfm_hloc_camera:
            cmd_parts.extend(["--hloc_camera", sfm_hloc_camera])
        if sfm_hloc_feature:
            cmd_parts.extend(["--hloc_feature", sfm_hloc_feature])
        if sfm_hloc_matcher:
            cmd_parts.extend(["--hloc_matcher", sfm_hloc_matcher])
        if sfm_hloc_weights:
            cmd_parts.extend(["--hloc_weights", sfm_hloc_weights])
        if sfm_vggsfm_max_points is not None:
            cmd_parts.extend(["--vggsfm_max_points", str(sfm_vggsfm_max_points)])
        if sfm_vggsfm_max_tri_points is not None:
            cmd_parts.extend(["--vggsfm_max_tri_points", str(sfm_vggsfm_max_tri_points)])
        if sfm_extra_args:
            cmd_parts.extend(shlex.split(sfm_extra_args))
        if sfm_skip:
            cmd_parts.append("--skip")
        if sfm_overwrite:
            cmd_parts.append("--overwrite")

    # Add process context
    if process_enable:
        cmd_parts.append("process")
        if process_mask:
            cmd_parts.extend(["--mask", process_mask])
        if process_crop_factor is not None:
            cmd_parts.extend(["--crop-factor", str(process_crop_factor)])
        if process_min_match_ratio is not None:
            cmd_parts.extend(["--min-match-ratio", str(process_min_match_ratio)])
        if process_extra_args:
            cmd_parts.extend(shlex.split(process_extra_args))
        if process_skip:
            cmd_parts.append("--skip")
        if process_overwrite:
            cmd_parts.append("--overwrite")

    # Add train context
    if train_enable:
        cmd_parts.append("train")
        if train_model:
            cmd_parts.extend(["--model", train_model])
        if train_config:
            cmd_parts.extend(["--config", train_config])
        if train_name:
            cmd_parts.extend(["--name", train_name])
        if train_vis:
            cmd_parts.extend(["--vis", train_vis])
        if train_downscale_factor is not None:
            cmd_parts.extend(["--downscale-factor", str(train_downscale_factor)])
        if train_scale_factor is not None:
            cmd_parts.extend(["--scale-factor", str(train_scale_factor)])
        if train_center_method:
            cmd_parts.extend(["--center-method", train_center_method])
        if train_orientation_method:
            cmd_parts.extend(["--orientation-method", train_orientation_method])
        if train_auto_scale_poses:
            cmd_parts.extend(["--auto-scale-poses", train_auto_scale_poses])
        if train_split_fraction is not None:
            cmd_parts.extend(["--train-split-fraction", str(train_split_fraction)])
        if train_eval_num_rays_per_chunk is not None:
            cmd_parts.extend(
                [
                    "--pipeline.model.eval-num-rays-per-chunk",
                    str(train_eval_num_rays_per_chunk),
                ]
            )
        if train_train_num_rays_per_batch is not None:
            cmd_parts.extend(
                [
                    "--pipeline.datamanager.train-num-rays-per-batch",
                    str(train_train_num_rays_per_batch),
                ]
            )
        if train_eval_num_rays_per_batch is not None:
            cmd_parts.extend(
                [
                    "--pipeline.datamanager.eval-num-rays-per-batch",
                    str(train_eval_num_rays_per_batch),
                ]
            )
        if train_camera_optimizer_mode:
            cmd_parts.extend(
                ["--pipeline.datamanager.camera-optimizer.mode", train_camera_optimizer_mode]
            )
        if train_use_reflections:
            cmd_parts.extend(
                [
                    "--pipeline.model.sdf-field.use-reflections",
                    "True",
                    "--pipeline.model.sdf-field.use-n-dot-v",
                    "True",
                ]
            )
        if train_use_diffuse_specular:
            cmd_parts.extend(
                [
                    "--pipeline.model.sdf-field.use-diffuse-color",
                    "True",
                    "--pipeline.model.sdf-field.use-specular-tint",
                    "True",
                ]
            )
        if train_enable_pred_roughness:
            cmd_parts.extend(
                [
                    "--pipeline.model.sdf-field.enable-pred-roughness",
                    "True",
                ]
            )
        if train_orientation_loss_mult is not None:
            cmd_parts.extend(
                [
                    "--pipeline.model.orientation-loss-mult",
                    str(train_orientation_loss_mult),
                ]
            )
        if train_distortion_loss_mult is not None:
            cmd_parts.extend(
                [
                    "--pipeline.model.distortion-loss-mult",
                    str(train_distortion_loss_mult),
                ]
            )
        if train_disable_appearance_embedding:
            cmd_parts.extend(
                [
                    "--pipeline.model.sdf-field.use-appearance-embedding",
                    "False",
                ]
            )
        if train_viewer_quit_on_completion:
            cmd_parts.extend(
                [
                    "--viewer.quit-on-train-completion",
                    "True",
                ]
            )
        if train_extra_args:
            cmd_parts.extend(shlex.split(train_extra_args))
        if train_skip:
            cmd_parts.append("--skip")
        if train_overwrite:
            cmd_parts.append("--overwrite")

    # Add export context
    if export_enable:
        cmd_parts.append("export")
        if export_resolution is not None:
            cmd_parts.extend(["--resolution", str(export_resolution)])
        if export_method:
            cmd_parts.extend(["--method", export_method])
        if export_marching_cube_threshold is not None:
            cmd_parts.extend(["--marching-cube-threshold", str(export_marching_cube_threshold)])
        if export_num_pixels_per_side is not None:
            cmd_parts.extend(["--num-pixels-per-side", str(export_num_pixels_per_side)])
        if export_target_num_faces is not None:
            cmd_parts.extend(["--target-num-faces", str(export_target_num_faces)])
        if export_px_per_uv_triangle is not None:
            cmd_parts.extend(["--px-per-uv-triangle", str(export_px_per_uv_triangle)])
        if (
            export_obb_center_x is not None
            and export_obb_center_y is not None
            and export_obb_center_z is not None
        ):
            cmd_parts.extend(
                [
                    "--obb-center",
                    str(export_obb_center_x),
                    str(export_obb_center_y),
                    str(export_obb_center_z),
                ]
            )
        if export_downscale_factor is not None:
            cmd_parts.extend(["--downscale-factor", str(export_downscale_factor)])
        if (
            export_obb_scale_x is not None
            and export_obb_scale_y is not None
            and export_obb_scale_z is not None
        ):
            cmd_parts.extend(
                [
                    "--obb-scale",
                    str(export_obb_scale_x),
                    str(export_obb_scale_y),
                    str(export_obb_scale_z),
                ]
            )
        if export_mesh_only:
            cmd_parts.append("--mesh-only")
        if export_texture_only:
            cmd_parts.append("--texture-only")
        if export_input_mesh_filename:
            cmd_parts.extend(["--input-mesh-filename", export_input_mesh_filename])
        if export_extra_args:
            cmd_parts.extend(shlex.split(export_extra_args))
        if export_skip:
            cmd_parts.append("--skip")
        if export_overwrite:
            cmd_parts.append("--overwrite")

    return " ".join(cmd_parts)


def create_ui() -> gr.Blocks:
    """Create and return the Gradio UI."""
    with gr.Blocks(title="Mini-Mesh: Video to 3D Pipeline") as demo:
        gr.Markdown("# Mini-Mesh: Video to 3D Mesh Pipeline")
        gr.Markdown(
            "This interface runs the public **mini-mesh** pipeline "
            "on your local machine or inside Docker."
        )
        gr.Markdown(
            "The workflow consists of:\n"
            "1. 🎬 Frame extraction from video input (optional, via the *Video* context).\n"
            "2. 📸 Structure-from-Motion (SfM) to estimate camera poses.\n"
            "3. 🖼️ Data processing and optional background masking.\n"
            "4. 🧠 Neural surface / NeRF training.\n"
            "5. ✨ Mesh extraction and texturing.\n\n"
            "Use the accordions below to tune each context. "
            "Per-stage *Skip* checkboxes let you disable individual steps.\n\n"
            "For detailed flag descriptions, VRAM tips, and example commands, see the project "
            "[README](https://github.com/hummat/mini-mesh#readme)."
        )

        with gr.Row():
            with gr.Column(scale=2):
                # Input section
                gr.Markdown("## Input")
                with gr.Tab("Path"):
                    input_path = gr.Textbox(
                        label="Video/Image Path",
                        placeholder="/path/to/video.mp4 or /path/to/images/",
                        info="Absolute path to an existing video file or image directory.",
                    )
                with gr.Tab("Video file"):
                    input_video_file = gr.File(
                        label="Video File (drag & drop)",
                        file_types=["video"],
                        type="filepath",
                    )
                with gr.Tab("Images directory"):
                    input_images_path = gr.Textbox(
                        label="Images Directory Path",
                        placeholder="/path/to/images/",
                        info="Absolute path to an existing directory containing images.",
                    )

                mode = gr.Radio(
                    label="Execution Mode",
                    choices=["local", "docker"],
                    value="docker",
                    info="Use local installation or Docker container",
                )

                # Global args
                with gr.Accordion("Global Settings", open=False):
                    with gr.Row():
                        global_show = gr.Checkbox(label="Show", info="Display intermediate results")
                        global_verbose = gr.Checkbox(label="Verbose", info="Enable verbose output")
                        global_overwrite = gr.Checkbox(
                            label="Overwrite", info="Overwrite existing outputs"
                        )

                # Video context
                with gr.Accordion("1. Video", open=False):
                    video_fps = gr.Number(
                        label="FPS", value=None, precision=0, info="Frames per second to extract"
                    )
                    video_time_slice = gr.Textbox(
                        label="Time Slice", placeholder="0:10", info="Time range (e.g., 0:10)"
                    )
                    video_hdr = gr.Checkbox(label="HDR", info="Enable HDR processing")
                    with gr.Row():
                        video_skip = gr.Checkbox(label="Skip")
                        video_overwrite = gr.Checkbox(label="Overwrite")

                # SfM context
                with gr.Accordion("2. SfM", open=False):
                    sfm_method = gr.Dropdown(
                        label="Method",
                        choices=["colmap", "glomap", "hloc", "vggsfm"],
                        value="colmap",
                        info="SfM reconstruction method",
                    )
                    sfm_matcher = gr.Dropdown(
                        label="Matcher",
                        choices=["exhaustive", "sequential", "vocab_tree", "superglue"],
                        value="sequential",
                        info="Feature matching method",
                    )
                    with gr.Accordion("Advanced SfM options", open=False):
                        sfm_camera_model = gr.Dropdown(
                            label="Camera Model",
                            choices=[
                                "SIMPLE_PINHOLE",
                                "PINHOLE",
                                "SIMPLE_RADIAL",
                                "RADIAL",
                                "OPENCV",
                                "FISHEYE",
                            ],
                            value="OPENCV",
                            info="Camera model to use in COLMAP/GLOMAP/HLoc.",
                        )
                        sfm_extra = gr.Checkbox(
                            label="Extra COLMAP options",
                            info=(
                                "Enable extra feature/matching options in COLMAP "
                                "(slower, sometimes more robust)."
                            ),
                        )
                        sfm_refine_principal_point = gr.Checkbox(
                            label="Refine principal point",
                            value=True,
                            info="Bundle adjust with principal point refinement.",
                        )
                        sfm_num_threads = gr.Number(
                            label="Num threads",
                            value=None,
                            precision=0,
                            info="Override automatic thread selection for SfM.",
                        )
                        with gr.Accordion("Deep SfM (HLoc / VGGSfM)", open=False):
                            sfm_hloc_feature = gr.Dropdown(
                                label="HLoc feature",
                                choices=[
                                    "superpoint_aachen",
                                    "superpoint_inloc",
                                    "superpoint_max",
                                ],
                                value=None,
                                info="Feature extractor for HLoc.",
                            )
                            sfm_hloc_matcher = gr.Dropdown(
                                label="HLoc matcher",
                                choices=[
                                    "superglue",
                                    "superpoint+lightglue",
                                    "superglue-fast",
                                    "NN-superpoint",
                                    "NN-ratio",
                                    "NN-mutual",
                                ],
                                value=None,
                                info="Matcher for HLoc.",
                            )
                            sfm_hloc_weights = gr.Dropdown(
                                label="HLoc weights",
                                choices=["indoor", "outdoor"],
                                value=None,
                                info="HLoc matcher weights.",
                            )
                            sfm_hloc_camera = gr.Dropdown(
                                label="HLoc camera model",
                                choices=[
                                    "SIMPLE_PINHOLE",
                                    "PINHOLE",
                                    "SIMPLE_RADIAL",
                                    "RADIAL",
                                    "OPENCV",
                                    "FISHEYE",
                                ],
                                value=None,
                                info="Camera model for HLoc.",
                            )
                            sfm_vggsfm_max_points = gr.Number(
                                label="VGGSfM max points",
                                value=None,
                                precision=0,
                                info="Maximum number of points used by VGGSfM.",
                            )
                            sfm_vggsfm_max_tri_points = gr.Number(
                                label="VGGSfM max triangle points",
                                value=None,
                                precision=0,
                                info="Maximum number of triangle points used by VGGSfM.",
                            )
                            sfm_extra_args = gr.Textbox(
                                label="Extra SfM arguments",
                                placeholder="Advanced: additional COLMAP / GLOMAP flags",
                                info="Verbatim extra args appended to the SfM context.",
                            )
                    with gr.Row():
                        sfm_skip = gr.Checkbox(label="Skip")
                        sfm_overwrite = gr.Checkbox(label="Overwrite")

                # Process context
                with gr.Accordion("3. Process", open=False):
                    process_mask = gr.Dropdown(
                        label="Background Mask",
                        choices=["none", "rembg", "sam2"],
                        value="none",
                        info="Background masking method",
                    )
                    process_crop_factor = gr.Textbox(
                        label="Crop Factor",
                        placeholder="auto or '0.1 0.1 0.1 0.1'",
                        info=(
                            "Advanced crop factor passed to sdf-process-data "
                            "(e.g., auto or four floats). Leave empty for default."
                        ),
                    )
                    process_min_match_ratio = gr.Number(
                        label="Min Match Ratio",
                        value=None,
                        info="Minimum match ratio for filtering",
                    )
                    process_extra_args = gr.Textbox(
                        label="Extra process arguments",
                        placeholder="Advanced: additional sdf-process-data flags",
                        info="Verbatim extra args appended to the process context.",
                    )
                    with gr.Row():
                        process_skip = gr.Checkbox(label="Skip")
                        process_overwrite = gr.Checkbox(label="Overwrite")

                # Train context
                with gr.Accordion("4. Train", open=False):
                    train_model = gr.Dropdown(
                        label="Model",
                        choices=["neus", "neus-facto", "nerfacto", "splatfacto"],
                        value="neus",
                        info="Training model type",
                    )
                    train_config = gr.Dropdown(
                        label="Config",
                        choices=[
                            "neus-facto-short",
                            "neus-facto",
                            "neus-grid-short",
                            "nerfacto-short",
                            "nerfacto",
                            "nerfacto-big",
                            "nerfacto-huge",
                        ],
                        value="neus-grid-short",
                        info="Training configuration",
                    )
                    train_name = gr.Textbox(
                        label="Experiment Name",
                        placeholder="my-experiment",
                        info="Optional experiment name",
                    )
                    train_vis = gr.Dropdown(
                        label="Visualization",
                        choices=["viewer", "tensorboard", "wandb"],
                        value="tensorboard",
                        info="Visualization method",
                    )
                    with gr.Accordion("Advanced data options", open=False):
                        train_downscale_factor = gr.Number(
                            label="Downscale Factor",
                            value=None,
                            precision=0,
                            info="Image downscale factor for training data",
                        )
                        train_scale_factor = gr.Number(
                            label="Scale Factor",
                            value=None,
                            info="Scene scale factor",
                        )
                        train_center_method = gr.Textbox(
                            label="Center Method",
                            placeholder="focus",
                            info="Pose centering method (e.g., focus)",
                        )
                        train_orientation_method = gr.Textbox(
                            label="Orientation Method",
                            placeholder="vertical",
                            info="Pose orientation method (e.g., vertical)",
                        )
                        train_auto_scale_poses = gr.Textbox(
                            label="Auto Scale Poses",
                            placeholder="median / True / False",
                            info="Auto pose scaling mode, leave empty for default.",
                        )
                        train_split_fraction = gr.Number(
                            label="Train Split Fraction",
                            value=None,
                            info="Train/validation split fraction (e.g., 0.95).",
                        )
                        train_eval_num_rays_per_chunk = gr.Number(
                            label="Eval rays per chunk",
                            value=None,
                            precision=0,
                            info="Override --pipeline.model.eval-num-rays-per-chunk.",
                        )
                        train_train_num_rays_per_batch = gr.Number(
                            label="Train rays per batch",
                            value=None,
                            precision=0,
                            info="Override --pipeline.datamanager.train-num-rays-per-batch.",
                        )
                        train_eval_num_rays_per_batch = gr.Number(
                            label="Eval rays per batch",
                            value=None,
                            precision=0,
                            info="Override --pipeline.datamanager.eval-num-rays-per-batch.",
                        )
                    with gr.Accordion("Advanced model options", open=False):
                        train_camera_optimizer_mode = gr.Textbox(
                            label="Camera optimizer mode",
                            placeholder="SO3xR3",
                            info="Sets --pipeline.datamanager.camera-optimizer.mode.",
                        )
                        train_use_reflections = gr.Checkbox(
                            label="Enable reflections (SDF)",
                            info="Sets Ref-NeRF-style reflection flags for SDF models.",
                        )
                        train_use_diffuse_specular = gr.Checkbox(
                            label="Enable diffuse+specular colors (SDF)",
                            info="Enables diffuse/specular color modeling for SDF models.",
                        )
                        train_enable_pred_roughness = gr.Checkbox(
                            label="Enable predicted roughness (PBR)",
                            info="Predict PBR roughness [0,1]; enables roughness map export.",
                        )
                        train_orientation_loss_mult = gr.Number(
                            label="Orientation loss multiplier",
                            value=None,
                            info="Ref-NeRF orientation loss (normals face camera). Default: 0.0.",
                        )
                        train_distortion_loss_mult = gr.Number(
                            label="Distortion loss multiplier",
                            value=None,
                            info="Mip-NeRF 360 distortion loss (reduce double walls). Default 0.0.",
                        )
                        train_disable_appearance_embedding = gr.Checkbox(
                            label="Disable appearance embedding",
                            info="Disables --pipeline.model.sdf-field.use-appearance-embedding.",
                        )
                        train_viewer_quit_on_completion = gr.Checkbox(
                            label="Close viewer when training ends",
                            info="Sets --viewer.quit-on-train-completion True.",
                        )
                        train_extra_args = gr.Textbox(
                            label="Extra train arguments",
                            placeholder="Advanced: additional ns-train / sdf-train flags",
                            info="Verbatim extra args appended to the train context.",
                        )
                    with gr.Row():
                        train_skip = gr.Checkbox(label="Skip")
                        train_overwrite = gr.Checkbox(label="Overwrite")

                # Export context
                with gr.Accordion("5. Export", open=False):
                    export_resolution = gr.Number(
                        label="Resolution",
                        value=None,
                        precision=0,
                        info="Mesh resolution",
                    )
                    export_method = gr.Dropdown(
                        label="NeRF Export Method",
                        choices=["poisson", "tsdf", "pointcloud", "gaussian-splat"],
                        value="poisson",
                        info="NeRF export method (ignored for SDF models)",
                    )
                    export_marching_cube_threshold = gr.Number(
                        label="Marching Cube Threshold",
                        value=None,
                        info="Isosurface value for marching cubes (SDF models).",
                    )
                    export_num_pixels_per_side = gr.Number(
                        label="Texture Resolution (pixels per side)",
                        value=None,
                        precision=0,
                        info="Texture resolution for UV baking.",
                    )
                    export_target_num_faces = gr.Number(
                        label="Target Number of Faces",
                        value=None,
                        precision=0,
                        info="Target number of faces for mesh simplification.",
                    )
                    export_px_per_uv_triangle = gr.Number(
                        label="Pixels per UV Triangle",
                        value=None,
                        precision=0,
                        info="Pixels per UV triangle for UV baking.",
                    )
                    with gr.Row():
                        export_mesh_only = gr.Checkbox(
                            label="Mesh only (SDF)",
                            info="SDF only: extract mesh but skip texturing.",
                        )
                        export_texture_only = gr.Checkbox(
                            label="Texture only (SDF)",
                            info="SDF only: texture an existing mesh, skip extraction.",
                        )
                    export_input_mesh_filename = gr.Textbox(
                        label="Input mesh filename (SDF, optional)",
                        placeholder="Defaults to mesh.ply in the experiment directory",
                        info="Custom mesh file for texturing. Requires 'Texture only (SDF)'.",
                    )
                    with gr.Accordion("Advanced OBB (NeRF only)", open=False):
                        export_obb_center_x = gr.Number(
                            label="OBB Center X",
                            value=None,
                            info="OBB center X coordinate.",
                        )
                        export_obb_center_y = gr.Number(
                            label="OBB Center Y",
                            value=None,
                            info="OBB center Y coordinate.",
                        )
                        export_obb_center_z = gr.Number(
                            label="OBB Center Z",
                            value=None,
                            info="OBB center Z coordinate.",
                        )
                        export_obb_scale_x = gr.Number(
                            label="OBB Scale X",
                            value=None,
                            info="OBB scale X component.",
                        )
                        export_obb_scale_y = gr.Number(
                            label="OBB Scale Y",
                            value=None,
                            info="OBB scale Y component.",
                        )
                        export_obb_scale_z = gr.Number(
                            label="OBB Scale Z",
                            value=None,
                            info="OBB scale Z component.",
                        )
                    with gr.Accordion("Advanced SDF/volume options", open=False):
                        export_downscale_factor = gr.Number(
                            label="TSDF downscale factor",
                            value=None,
                            precision=0,
                            info="Sets --downscale-factor for TSDF exports.",
                        )
                        export_extra_args = gr.Textbox(
                            label="Extra export arguments",
                            placeholder=("Advanced: additional ns-export / sdf-extract-mesh flags"),
                            info="Verbatim extra args appended to the export context.",
                        )
                    with gr.Row():
                        export_skip = gr.Checkbox(label="Skip")
                        export_overwrite = gr.Checkbox(label="Overwrite")

                # Submit button
                submit_btn = gr.Button("Build Command", variant="primary", size="lg")

            # Output column
            with gr.Column(scale=1):
                gr.Markdown("## Command Output")
                command_output = gr.Textbox(
                    label="Generated Command",
                    lines=10,
                    max_lines=20,
                    interactive=False,
                    info="Command that will be executed",
                )
                validation_output = gr.Textbox(
                    label="Validation",
                    lines=2,
                    interactive=False,
                    info="Command validation result",
                )

        # Build command function
        def build_command(
            input_path_val,
            input_video_file_val,
            input_images_path_val,
            mode_val,
            global_show_val,
            global_verbose_val,
            global_overwrite_val,
            video_fps_val,
            video_time_slice_val,
            video_hdr_val,
            video_skip_val,
            video_overwrite_val,
            sfm_method_val,
            sfm_matcher_val,
            sfm_camera_model_val,
            sfm_extra_val,
            sfm_refine_principal_point_val,
            sfm_num_threads_val,
            sfm_hloc_feature_val,
            sfm_hloc_matcher_val,
            sfm_hloc_weights_val,
            sfm_hloc_camera_val,
            sfm_vggsfm_max_points_val,
            sfm_vggsfm_max_tri_points_val,
            sfm_skip_val,
            sfm_overwrite_val,
            process_mask_val,
            process_crop_factor_val,
            process_min_match_ratio_val,
            process_skip_val,
            process_overwrite_val,
            train_model_val,
            train_config_val,
            train_name_val,
            train_vis_val,
            train_downscale_factor_val,
            train_scale_factor_val,
            train_center_method_val,
            train_orientation_method_val,
            train_auto_scale_poses_val,
            train_split_fraction_val,
            train_eval_num_rays_per_chunk_val,
            train_train_num_rays_per_batch_val,
            train_eval_num_rays_per_batch_val,
            train_camera_optimizer_mode_val,
            train_use_reflections_val,
            train_use_diffuse_specular_val,
            train_enable_pred_roughness_val,
            train_orientation_loss_mult_val,
            train_distortion_loss_mult_val,
            train_disable_appearance_embedding_val,
            train_viewer_quit_on_completion_val,
            train_extra_args_val,
            train_skip_val,
            train_overwrite_val,
            export_resolution_val,
            export_method_val,
            export_marching_cube_threshold_val,
            export_num_pixels_per_side_val,
            export_target_num_faces_val,
            export_px_per_uv_triangle_val,
            export_mesh_only_val,
            export_texture_only_val,
            export_input_mesh_filename_val,
            export_obb_center_x_val,
            export_obb_center_y_val,
            export_obb_center_z_val,
            export_obb_scale_x_val,
            export_obb_scale_y_val,
            export_obb_scale_z_val,
            export_downscale_factor_val,
            sfm_extra_args_val,
            process_extra_args_val,
            export_extra_args_val,
            export_skip_val,
            export_overwrite_val,
        ):
            """Build command and validate it."""

            def _norm_num(val):
                if val is None:
                    return None
                if isinstance(val, str) and not val.strip():
                    return None
                try:
                    fval = float(val)
                except (TypeError, ValueError):
                    return None
                if fval == 0:
                    return None
                return val

            # Resolve input path priority: explicit path > images dir path > uploaded video
            resolved_input_path = None
            if input_path_val and str(input_path_val).strip():
                resolved_input_path = str(input_path_val).strip()
            elif input_images_path_val and str(input_images_path_val).strip():
                resolved_input_path = str(input_images_path_val).strip()
            elif input_video_file_val:
                # File component with type="filepath" returns a filesystem path string
                resolved_input_path = str(input_video_file_val)

            # Convert "none" mask to None
            if process_mask_val == "none":
                process_mask_val = None

            # Normalize numeric inputs: drop zero/empty to avoid overriding defaults
            video_fps_val = _norm_num(video_fps_val)
            sfm_num_threads_val = _norm_num(sfm_num_threads_val)
            sfm_vggsfm_max_points_val = _norm_num(sfm_vggsfm_max_points_val)
            sfm_vggsfm_max_tri_points_val = _norm_num(sfm_vggsfm_max_tri_points_val)
            process_min_match_ratio_val = _norm_num(process_min_match_ratio_val)
            train_downscale_factor_val = _norm_num(train_downscale_factor_val)
            train_scale_factor_val = _norm_num(train_scale_factor_val)
            train_split_fraction_val = _norm_num(train_split_fraction_val)
            train_eval_num_rays_per_chunk_val = _norm_num(train_eval_num_rays_per_chunk_val)
            train_train_num_rays_per_batch_val = _norm_num(train_train_num_rays_per_batch_val)
            train_eval_num_rays_per_batch_val = _norm_num(train_eval_num_rays_per_batch_val)
            train_orientation_loss_mult_val = _norm_num(train_orientation_loss_mult_val)
            train_distortion_loss_mult_val = _norm_num(train_distortion_loss_mult_val)
            export_resolution_val = _norm_num(export_resolution_val)
            export_marching_cube_threshold_val = _norm_num(export_marching_cube_threshold_val)
            export_num_pixels_per_side_val = _norm_num(export_num_pixels_per_side_val)
            export_target_num_faces_val = _norm_num(export_target_num_faces_val)
            export_px_per_uv_triangle_val = _norm_num(export_px_per_uv_triangle_val)
            export_obb_center_x_val = _norm_num(export_obb_center_x_val)
            export_obb_center_y_val = _norm_num(export_obb_center_y_val)
            export_obb_center_z_val = _norm_num(export_obb_center_z_val)
            export_obb_scale_x_val = _norm_num(export_obb_scale_x_val)
            export_obb_scale_y_val = _norm_num(export_obb_scale_y_val)
            export_obb_scale_z_val = _norm_num(export_obb_scale_z_val)
            export_downscale_factor_val = _norm_num(export_downscale_factor_val)

            # Drop values that match script defaults to keep command short
            if sfm_method_val == "colmap":
                sfm_method_val = None
            if sfm_matcher_val == "sequential":
                sfm_matcher_val = None
            if sfm_camera_model_val == "OPENCV":
                sfm_camera_model_val = None
            if train_model_val == "neus":
                train_model_val = None
            if train_config_val == "neus-grid-short":
                train_config_val = None
            if train_vis_val == "tensorboard":
                train_vis_val = None
            if export_method_val == "poisson":
                export_method_val = None

            # Build command
            has_extra_args = any(
                bool(x and str(x).strip())
                for x in [
                    process_extra_args_val,
                    sfm_extra_args_val,
                    train_extra_args_val,
                    export_extra_args_val,
                ]
            )

            video_enable = any(
                [
                    video_fps_val,
                    video_time_slice_val,
                    video_hdr_val,
                    video_skip_val,
                    video_overwrite_val,
                ]
            )
            sfm_enable = any(
                [
                    sfm_method_val,
                    sfm_matcher_val,
                    sfm_camera_model_val,
                    sfm_extra_val,
                    sfm_refine_principal_point_val is False,
                    sfm_num_threads_val,
                    sfm_hloc_feature_val,
                    sfm_hloc_matcher_val,
                    sfm_hloc_weights_val,
                    sfm_hloc_camera_val,
                    sfm_vggsfm_max_points_val,
                    sfm_vggsfm_max_tri_points_val,
                    sfm_skip_val,
                    sfm_overwrite_val,
                    sfm_extra_args_val,
                ]
            )
            process_enable = any(
                [
                    process_mask_val,
                    process_crop_factor_val,
                    process_min_match_ratio_val,
                    process_skip_val,
                    process_overwrite_val,
                    process_extra_args_val,
                ]
            )
            train_enable = any(
                [
                    train_model_val,
                    train_config_val,
                    train_name_val,
                    train_vis_val,
                    train_downscale_factor_val,
                    train_scale_factor_val,
                    train_center_method_val,
                    train_orientation_method_val,
                    train_auto_scale_poses_val,
                    train_split_fraction_val,
                    train_eval_num_rays_per_chunk_val,
                    train_train_num_rays_per_batch_val,
                    train_eval_num_rays_per_batch_val,
                    train_camera_optimizer_mode_val,
                    train_use_reflections_val,
                    train_use_diffuse_specular_val,
                    train_enable_pred_roughness_val,
                    train_orientation_loss_mult_val,
                    train_distortion_loss_mult_val,
                    train_disable_appearance_embedding_val,
                    train_viewer_quit_on_completion_val,
                    train_skip_val,
                    train_overwrite_val,
                    train_extra_args_val,
                ]
            )
            export_enable = any(
                [
                    export_resolution_val,
                    export_method_val,
                    export_marching_cube_threshold_val,
                    export_num_pixels_per_side_val,
                    export_target_num_faces_val,
                    export_px_per_uv_triangle_val,
                    export_mesh_only_val,
                    export_texture_only_val,
                    export_obb_center_x_val,
                    export_obb_center_y_val,
                    export_obb_center_z_val,
                    export_obb_scale_x_val,
                    export_obb_scale_y_val,
                    export_obb_scale_z_val,
                    export_downscale_factor_val,
                    export_skip_val,
                    export_overwrite_val,
                    export_extra_args_val,
                ]
            )
            cmd = run_pipeline(
                input_path=resolved_input_path,
                mode=mode_val,
                global_show=global_show_val,
                global_verbose=global_verbose_val,
                global_overwrite=global_overwrite_val,
                video_enable=video_enable,
                video_fps=int(video_fps_val) if video_fps_val else None,
                video_time_slice=video_time_slice_val if video_time_slice_val else None,
                video_hdr=video_hdr_val,
                video_skip=video_skip_val,
                video_overwrite=video_overwrite_val,
                sfm_enable=sfm_enable,
                sfm_method=sfm_method_val or None,
                sfm_matcher=sfm_matcher_val or None,
                sfm_camera_model=sfm_camera_model_val or None,
                sfm_extra=sfm_extra_val,
                sfm_refine_principal_point=sfm_refine_principal_point_val,
                sfm_num_threads=int(sfm_num_threads_val)
                if sfm_num_threads_val is not None and float(sfm_num_threads_val) > 0
                else None,
                sfm_hloc_feature=sfm_hloc_feature_val or None,
                sfm_hloc_matcher=sfm_hloc_matcher_val or None,
                sfm_hloc_weights=sfm_hloc_weights_val or None,
                sfm_hloc_camera=sfm_hloc_camera_val or None,
                sfm_vggsfm_max_points=int(sfm_vggsfm_max_points_val)
                if sfm_vggsfm_max_points_val is not None
                else None,
                sfm_vggsfm_max_tri_points=int(sfm_vggsfm_max_tri_points_val)
                if sfm_vggsfm_max_tri_points_val is not None
                else None,
                sfm_skip=sfm_skip_val,
                sfm_overwrite=sfm_overwrite_val,
                process_enable=process_enable,
                process_mask=process_mask_val,
                process_crop_factor=process_crop_factor_val if process_crop_factor_val else None,
                process_min_match_ratio=float(process_min_match_ratio_val)
                if process_min_match_ratio_val is not None
                else None,
                process_skip=process_skip_val,
                process_overwrite=process_overwrite_val,
                train_enable=train_enable,
                train_model=train_model_val or None,
                train_config=train_config_val or None,
                train_name=train_name_val if train_name_val else None,
                train_vis=train_vis_val or None,
                train_downscale_factor=int(train_downscale_factor_val)
                if train_downscale_factor_val is not None
                else None,
                train_scale_factor=float(train_scale_factor_val)
                if train_scale_factor_val is not None
                else None,
                train_center_method=train_center_method_val or None,
                train_orientation_method=train_orientation_method_val or None,
                train_auto_scale_poses=train_auto_scale_poses_val or None,
                train_split_fraction=float(train_split_fraction_val)
                if train_split_fraction_val is not None
                else None,
                train_eval_num_rays_per_chunk=int(train_eval_num_rays_per_chunk_val)
                if train_eval_num_rays_per_chunk_val is not None
                else None,
                train_train_num_rays_per_batch=int(train_train_num_rays_per_batch_val)
                if train_train_num_rays_per_batch_val is not None
                else None,
                train_eval_num_rays_per_batch=int(train_eval_num_rays_per_batch_val)
                if train_eval_num_rays_per_batch_val is not None
                else None,
                train_camera_optimizer_mode=train_camera_optimizer_mode_val or None,
                train_use_reflections=bool(train_use_reflections_val),
                train_use_diffuse_specular=bool(train_use_diffuse_specular_val),
                train_enable_pred_roughness=bool(train_enable_pred_roughness_val),
                train_orientation_loss_mult=float(train_orientation_loss_mult_val)
                if train_orientation_loss_mult_val is not None
                else None,
                train_distortion_loss_mult=float(train_distortion_loss_mult_val)
                if train_distortion_loss_mult_val is not None
                else None,
                train_disable_appearance_embedding=bool(train_disable_appearance_embedding_val),
                train_viewer_quit_on_completion=bool(train_viewer_quit_on_completion_val),
                train_extra_args=train_extra_args_val or None,
                train_skip=train_skip_val,
                train_overwrite=train_overwrite_val,
                export_enable=export_enable,
                export_resolution=int(export_resolution_val) if export_resolution_val else None,
                export_method=export_method_val or None,
                export_marching_cube_threshold=float(export_marching_cube_threshold_val)
                if export_marching_cube_threshold_val is not None
                else None,
                export_num_pixels_per_side=int(export_num_pixels_per_side_val)
                if export_num_pixels_per_side_val is not None
                else None,
                export_target_num_faces=int(export_target_num_faces_val)
                if export_target_num_faces_val is not None
                else None,
                export_px_per_uv_triangle=int(export_px_per_uv_triangle_val)
                if export_px_per_uv_triangle_val is not None
                else None,
                export_mesh_only=bool(export_mesh_only_val),
                export_texture_only=bool(export_texture_only_val),
                export_input_mesh_filename=(
                    str(export_input_mesh_filename_val).strip()
                    if export_input_mesh_filename_val
                    and str(export_input_mesh_filename_val).strip()
                    else None
                ),
                export_obb_center_x=float(export_obb_center_x_val)
                if export_obb_center_x_val is not None
                else None,
                export_obb_center_y=float(export_obb_center_y_val)
                if export_obb_center_y_val is not None
                else None,
                export_obb_center_z=float(export_obb_center_z_val)
                if export_obb_center_z_val is not None
                else None,
                export_obb_scale_x=float(export_obb_scale_x_val)
                if export_obb_scale_x_val is not None
                else None,
                export_obb_scale_y=float(export_obb_scale_y_val)
                if export_obb_scale_y_val is not None
                else None,
                export_obb_scale_z=float(export_obb_scale_z_val)
                if export_obb_scale_z_val is not None
                else None,
                export_downscale_factor=int(export_downscale_factor_val)
                if export_downscale_factor_val is not None
                else None,
                sfm_extra_args=sfm_extra_args_val or None,
                process_extra_args=process_extra_args_val or None,
                export_extra_args=export_extra_args_val or None,
                export_skip=export_skip_val,
                export_overwrite=export_overwrite_val,
            )

            # Validate command
            if cmd:
                if has_extra_args:
                    validation_msg = (
                        "⚠ Skipped strict validation due to extra args. "
                        "Review the command manually before executing."
                    )
                else:
                    run_script = "docker/run.sh" if mode_val == "docker" else "scripts/run.sh"
                    validation = test_cmd(cmd, run_script)
                    if validation is None:
                        validation_msg = "✓ Command is valid"
                    else:
                        validation_msg = f"✗ {validation}"
            else:
                validation_msg = "✗ No input path provided"

            return cmd, validation_msg

        # Wire submit button
        submit_btn.click(
            build_command,
            inputs=[
                input_path,
                input_video_file,
                input_images_path,
                mode,
                global_show,
                global_verbose,
                global_overwrite,
                video_fps,
                video_time_slice,
                video_hdr,
                video_skip,
                video_overwrite,
                sfm_method,
                sfm_matcher,
                sfm_camera_model,
                sfm_extra,
                sfm_refine_principal_point,
                sfm_num_threads,
                sfm_hloc_feature,
                sfm_hloc_matcher,
                sfm_hloc_weights,
                sfm_hloc_camera,
                sfm_vggsfm_max_points,
                sfm_vggsfm_max_tri_points,
                sfm_skip,
                sfm_overwrite,
                process_mask,
                process_crop_factor,
                process_min_match_ratio,
                process_skip,
                process_overwrite,
                train_model,
                train_config,
                train_name,
                train_vis,
                train_downscale_factor,
                train_scale_factor,
                train_center_method,
                train_orientation_method,
                train_auto_scale_poses,
                train_split_fraction,
                train_eval_num_rays_per_chunk,
                train_train_num_rays_per_batch,
                train_eval_num_rays_per_batch,
                train_camera_optimizer_mode,
                train_use_reflections,
                train_use_diffuse_specular,
                train_enable_pred_roughness,
                train_orientation_loss_mult,
                train_distortion_loss_mult,
                train_disable_appearance_embedding,
                train_viewer_quit_on_completion,
                train_extra_args,
                train_skip,
                train_overwrite,
                export_resolution,
                export_method,
                export_marching_cube_threshold,
                export_num_pixels_per_side,
                export_target_num_faces,
                export_px_per_uv_triangle,
                export_mesh_only,
                export_texture_only,
                export_input_mesh_filename,
                export_obb_center_x,
                export_obb_center_y,
                export_obb_center_z,
                export_obb_scale_x,
                export_obb_scale_y,
                export_obb_scale_z,
                export_downscale_factor,
                sfm_extra_args,
                process_extra_args,
                export_extra_args,
                export_skip,
                export_overwrite,
            ],
            outputs=[command_output, validation_output],
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch()
