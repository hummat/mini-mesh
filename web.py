import os

import gradio as gr
import subprocess
from typing import Generator


def run_workflow(
    input_path: str,
    global_docker: bool,
    global_show: bool,
    global_verbose: bool,
    global_overwrite: bool,
    video_enabled: bool,
    video_fps: int,
    video_hdr: bool,
    video_overwrite: bool,
    sfm_enabled: bool,
    sfm_method: str,
    sfm_overwrite: bool,
    train_enabled: bool,
    train_model: str,
    train_name: str,
    train_config: str,
    train_overwrite: bool,
    export_enabled: bool,
    export_resolution: int,
    export_overwrite: bool,
) -> Generator[str, None, None]:
    cmd = ["docker/run.sh"] if global_docker else ["scripts/run.sh"]
    cmd.append(input_path)

    if global_show:
        cmd.append("--show")
    if global_verbose:
        cmd.append("--verbose")
    if global_overwrite:
        cmd.append("--overwrite")

    cmd.append("video")
    if video_enabled:
        if video_fps != 2:
            cmd.extend(["--fps", str(video_fps)])
        if video_hdr:
            cmd.append("--hdr")
        if video_overwrite:
            cmd.append("--overwrite")
    else:
        cmd.append("--skip")

    cmd.append("sfm")
    if sfm_enabled:
        if sfm_method != "colmap":
            cmd.extend(["--method", sfm_method])
        if sfm_overwrite:
            cmd.append("--overwrite")
    else:
        cmd.append("--skip")

    cmd.append("train")
    if train_enabled:
        cmd.extend(["--model", train_model])
        if train_name:
            cmd.extend(["--name", train_name])
        if train_config != "neus-grid-dev":
            cmd.extend(["--config", train_config])
        if train_overwrite:
            cmd.append("--overwrite")
    else:
        cmd.append("--skip")

    cmd.append("export")
    if export_enabled:
        if export_overwrite:
            cmd.append("--overwrite")
        if export_resolution != 2048:
            cmd.extend(["--resolution", str(export_resolution)])
    else:
        cmd.append("--skip")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    accumulated_output = " ".join(cmd) + "\n"
    try:
        for line in iter(process.stdout.readline, ""):
            accumulated_output += line
            yield accumulated_output
        process.stdout.close()
        process.wait()
    except Exception as e:
        process.kill()
        raise e


def run():
    with gr.Blocks() as app:
        gr.Markdown("# Video to Mesh Pipeline")

        with gr.Row():
            input_path = gr.Textbox(label="Input Path", placeholder="/path/to/your/video/or/images")

        with gr.Accordion("Global Settings", open=False):
            with gr.Row():
                global_docker = gr.Checkbox(label="Use Docker", value=True)
                global_verbose = gr.Checkbox(label="Verbose Output")
                global_overwrite = gr.Checkbox(label="Overwrite All")

        with gr.Accordion("Video", open=False):
            video_enabled = gr.Checkbox(label="Enable Video Step", value=True)
            video_fps = gr.Slider(label="FPS", minimum=1, maximum=5, value=2, step=1)
            video_hdr = gr.Checkbox(label="HDR")
            video_overwrite = gr.Checkbox(label="Overwrite Video Step")

        with gr.Accordion("SFM", open=False):
            sfm_enabled = gr.Checkbox(label="Enable SfM Step", value=True)
            sfm_method = gr.Dropdown(
                label="SfM Method",
                choices=["colmap", "glomap", "hloc", "vggsfm"],
                value="colmap",
            )
            sfm_show = gr.Checkbox(label="Show SfM result in Colmap GUI")
            sfm_overwrite = gr.Checkbox(label="Overwrite SfM Step")

        with gr.Accordion("Train", open=False):
            train_enabled = gr.Checkbox(label="Enable Training Step", value=True)
            train_model = gr.Dropdown(
                label="Model",
                choices=["neus", "neus-facto", "neuralangelo"],
                value="neus",
            )
            train_name = gr.Textbox(label="Experiment Name")
            train_config = gr.Textbox(label="Config", value="neus-grid-dev")
            train_overwrite = gr.Checkbox(label="Overwrite Training Step")

        with gr.Accordion("Export", open=False):
            export_enabled = gr.Checkbox(label="Enable Export Step", value=True)
            export_resolution = gr.Slider(
                label="Resolution",
                minimum=512,
                maximum=8192,
                value=2048,
                step=128,
            )
            export_overwrite = gr.Checkbox(label="Overwrite Export Step")

        submit = gr.Button("Run Workflow")
        output = gr.Textbox(label="Output", lines=20, interactive=False)

        submit.click(
            fn=run_workflow,
            inputs=[
                input_path,
                global_docker,
                sfm_show,
                global_verbose,
                global_overwrite,
                video_enabled,
                video_fps,
                video_hdr,
                video_overwrite,
                sfm_enabled,
                sfm_method,
                sfm_overwrite,
                train_enabled,
                train_model,
                train_name,
                train_config,
                train_overwrite,
                export_enabled,
                export_resolution,
                export_overwrite,
            ],
            outputs=output,
            show_progress="full",
        )

    app.queue().launch(server_name=os.environ.get("HOSTNAME", "localhost"))


if __name__ == "__main__":
    run()
