"""Web UI for mini-mesh video to 3D mesh pipeline."""

import re
from typing import Optional

import gradio as gr


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
        "--pipeline.model.eval-num-rays-per-chunk",
        "--pipeline.datamanager.train-num-rays-per-batch",
        "--pipeline.datamanager.eval-num-rays-per-batch",
        "--pipeline.datamanager.camera-optimizer.mode",
        "--pipeline.model.sdf-field.use-reflections",
        "--pipeline.model.sdf-field.use-n-dot-v",
        "--pipeline.model.sdf-field.use-diffuse-color",
        "--pipeline.model.sdf-field.use-specular-tint",
        "--pipeline.model.sdf-field.use-appearance-embedding",
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
        "--method",
        "--target-num-faces",
        "--bounding-box-min",
        "--bounding-box-max",
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
    train_skip: bool = False,
    train_overwrite: bool = False,
    # Export context
    export_enable: bool = False,
    export_resolution: Optional[int] = None,
    export_method: Optional[str] = None,
    export_skip: bool = False,
    export_overwrite: bool = False,
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
        train_vis: Visualization method (tensorboard, etc.)
        train_skip: Skip training
        train_overwrite: Overwrite training outputs
        export_enable: Enable export context
        export_resolution: Export resolution
        export_method: Export method (poisson, etc.)
        export_skip: Skip export
        export_overwrite: Overwrite export outputs

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
        if sfm_matcher:
            cmd_parts.extend(["--matcher", sfm_matcher])
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
        if export_skip:
            cmd_parts.append("--skip")
        if export_overwrite:
            cmd_parts.append("--overwrite")

    return " ".join(cmd_parts)


def create_ui() -> gr.Blocks:
    """Create and return the Gradio UI."""
    with gr.Blocks(title="Mini-Mesh: Video to 3D Pipeline") as demo:
        gr.Markdown("# Mini-Mesh: Video to 3D Mesh Pipeline")
        gr.Markdown("Convert videos or image sequences into 3D meshes using NeRF/SDF methods.")

        with gr.Row():
            with gr.Column(scale=2):
                # Input section
                gr.Markdown("## Input")
                input_path = gr.Textbox(
                    label="Video/Image Path",
                    placeholder="/path/to/video.mp4 or /path/to/images/",
                    info="Path to input video file or image directory",
                )
                mode = gr.Radio(
                    label="Execution Mode",
                    choices=["local", "docker"],
                    value="local",
                    info="Use local installation or Docker container",
                )

                # Global args
                gr.Markdown("## Global Options")
                with gr.Row():
                    global_show = gr.Checkbox(label="Show", info="Display intermediate results")
                    global_verbose = gr.Checkbox(label="Verbose", info="Enable verbose output")
                    global_overwrite = gr.Checkbox(
                        label="Overwrite", info="Overwrite existing outputs"
                    )

                # Video context
                gr.Markdown("## Video Processing")
                video_enable = gr.Checkbox(label="Enable Video Context", value=False)
                with gr.Group(visible=False) as video_group:
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
                gr.Markdown("## Structure from Motion (SfM)")
                sfm_enable = gr.Checkbox(label="Enable SfM Context", value=False)
                with gr.Group(visible=False) as sfm_group:
                    sfm_method = gr.Dropdown(
                        label="Method",
                        choices=["colmap", "glomap", "hloc", "vggsfm"],
                        value="colmap",
                        info="SfM reconstruction method",
                    )
                    sfm_matcher = gr.Dropdown(
                        label="Matcher",
                        choices=["exhaustive", "sequential", "vocab_tree", "superglue"],
                        value="exhaustive",
                        info="Feature matching method",
                    )
                    with gr.Row():
                        sfm_skip = gr.Checkbox(label="Skip")
                        sfm_overwrite = gr.Checkbox(label="Overwrite")

                # Process context
                gr.Markdown("## Data Processing")
                process_enable = gr.Checkbox(label="Enable Process Context", value=False)
                with gr.Group(visible=False) as process_group:
                    process_mask = gr.Dropdown(
                        label="Background Mask",
                        choices=["none", "rembg", "sam2"],
                        value="none",
                        info="Background masking method",
                    )
                    process_crop_factor = gr.Number(
                        label="Crop Factor",
                        value=None,
                        info="Auto-crop factor (e.g., 1.2)",
                    )
                    process_min_match_ratio = gr.Number(
                        label="Min Match Ratio",
                        value=None,
                        info="Minimum match ratio for filtering",
                    )
                    with gr.Row():
                        process_skip = gr.Checkbox(label="Skip")
                        process_overwrite = gr.Checkbox(label="Overwrite")

                # Train context
                gr.Markdown("## Model Training")
                train_enable = gr.Checkbox(label="Enable Train Context", value=False)
                with gr.Group(visible=False) as train_group:
                    train_model = gr.Dropdown(
                        label="Model",
                        choices=["neus-facto", "neus-grid", "nerfacto", "splatfacto"],
                        value="neus-facto",
                        info="Training model type",
                    )
                    train_config = gr.Dropdown(
                        label="Config",
                        choices=[
                            "neus-facto-dev",
                            "neus-facto-fast",
                            "neus-grid-dev",
                            "nerfacto-dev",
                            "nerfacto",
                            "nerfacto-big",
                            "nerfacto-huge",
                        ],
                        value="neus-facto-dev",
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
                        value="viewer",
                        info="Visualization method",
                    )
                    with gr.Row():
                        train_skip = gr.Checkbox(label="Skip")
                        train_overwrite = gr.Checkbox(label="Overwrite")

                # Export context
                gr.Markdown("## Mesh Export")
                export_enable = gr.Checkbox(label="Enable Export Context", value=False)
                with gr.Group(visible=False) as export_group:
                    export_resolution = gr.Number(
                        label="Resolution",
                        value=2048,
                        precision=0,
                        info="Mesh resolution",
                    )
                    export_method = gr.Dropdown(
                        label="Method",
                        choices=["marching-cubes", "poisson"],
                        value="marching-cubes",
                        info="Mesh extraction method",
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

        # Dynamic UI updates
        def toggle_video_group(enabled):
            return gr.Group(visible=enabled)

        def toggle_sfm_group(enabled):
            return gr.Group(visible=enabled)

        def toggle_process_group(enabled):
            return gr.Group(visible=enabled)

        def toggle_train_group(enabled):
            return gr.Group(visible=enabled)

        def toggle_export_group(enabled):
            return gr.Group(visible=enabled)

        video_enable.change(toggle_video_group, video_enable, video_group)
        sfm_enable.change(toggle_sfm_group, sfm_enable, sfm_group)
        process_enable.change(toggle_process_group, process_enable, process_group)
        train_enable.change(toggle_train_group, train_enable, train_group)
        export_enable.change(toggle_export_group, export_enable, export_group)

        # Build command function
        def build_command(
            input_path_val,
            mode_val,
            global_show_val,
            global_verbose_val,
            global_overwrite_val,
            video_enable_val,
            video_fps_val,
            video_time_slice_val,
            video_hdr_val,
            video_skip_val,
            video_overwrite_val,
            sfm_enable_val,
            sfm_method_val,
            sfm_matcher_val,
            sfm_skip_val,
            sfm_overwrite_val,
            process_enable_val,
            process_mask_val,
            process_crop_factor_val,
            process_min_match_ratio_val,
            process_skip_val,
            process_overwrite_val,
            train_enable_val,
            train_model_val,
            train_config_val,
            train_name_val,
            train_vis_val,
            train_skip_val,
            train_overwrite_val,
            export_enable_val,
            export_resolution_val,
            export_method_val,
            export_skip_val,
            export_overwrite_val,
        ):
            """Build command and validate it."""
            # Convert "none" mask to None
            if process_mask_val == "none":
                process_mask_val = None

            # Build command
            cmd = run_pipeline(
                input_path=input_path_val,
                mode=mode_val,
                global_show=global_show_val,
                global_verbose=global_verbose_val,
                global_overwrite=global_overwrite_val,
                video_enable=video_enable_val,
                video_fps=int(video_fps_val) if video_fps_val else None,
                video_time_slice=video_time_slice_val if video_time_slice_val else None,
                video_hdr=video_hdr_val,
                video_skip=video_skip_val,
                video_overwrite=video_overwrite_val,
                sfm_enable=sfm_enable_val,
                sfm_method=sfm_method_val if sfm_enable_val else None,
                sfm_matcher=sfm_matcher_val if sfm_enable_val else None,
                sfm_skip=sfm_skip_val,
                sfm_overwrite=sfm_overwrite_val,
                process_enable=process_enable_val,
                process_mask=process_mask_val,
                process_crop_factor=process_crop_factor_val,
                process_min_match_ratio=process_min_match_ratio_val,
                process_skip=process_skip_val,
                process_overwrite=process_overwrite_val,
                train_enable=train_enable_val,
                train_model=train_model_val if train_enable_val else None,
                train_config=train_config_val if train_enable_val else None,
                train_name=train_name_val if train_name_val else None,
                train_vis=train_vis_val if train_enable_val else None,
                train_skip=train_skip_val,
                train_overwrite=train_overwrite_val,
                export_enable=export_enable_val,
                export_resolution=int(export_resolution_val) if export_resolution_val else None,
                export_method=export_method_val if export_enable_val else None,
                export_skip=export_skip_val,
                export_overwrite=export_overwrite_val,
            )

            # Validate command
            if cmd:
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
                mode,
                global_show,
                global_verbose,
                global_overwrite,
                video_enable,
                video_fps,
                video_time_slice,
                video_hdr,
                video_skip,
                video_overwrite,
                sfm_enable,
                sfm_method,
                sfm_matcher,
                sfm_skip,
                sfm_overwrite,
                process_enable,
                process_mask,
                process_crop_factor,
                process_min_match_ratio,
                process_skip,
                process_overwrite,
                train_enable,
                train_model,
                train_config,
                train_name,
                train_vis,
                train_skip,
                train_overwrite,
                export_enable,
                export_resolution,
                export_method,
                export_skip,
                export_overwrite,
            ],
            outputs=[command_output, validation_output],
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch()
