"""Unit tests for webui.py command validation and building."""

from __future__ import annotations

from pathlib import Path


class TestCommandValidation:
    """Test test_cmd() function for command validation."""

    def test_valid_minimal_command(self):
        """Test minimal valid command passes validation."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_valid_command_with_contexts(self):
        """Test valid command with all contexts passes."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 video sfm process train export"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_valid_global_args(self):
        """Test all valid global args are accepted."""
        from webui import test_cmd

        valid_args = [
            "scripts/run.sh /path/to/video.mp4 --show",
            "scripts/run.sh /path/to/video.mp4 --verbose",
            "scripts/run.sh /path/to/video.mp4 --overwrite",
            "scripts/run.sh /path/to/video.mp4 --shared",
            "scripts/run.sh /path/to/video.mp4 --mail user@example.com",
            "scripts/run.sh /path/to/video.mp4 --show --verbose",
            "scripts/run.sh /path/to/video.mp4 --show --verbose --overwrite",
            (
                "scripts/run.sh /path/to/video.mp4 --show --verbose "
                "--overwrite --shared --mail user@example.com"
            ),
        ]
        for cmd in valid_args:
            result = test_cmd(cmd, "scripts/run.sh")
            assert result is None, f"Valid command rejected: {cmd}"

    def test_invalid_global_arg(self):
        """Test invalid global args are rejected."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 --invalid-flag"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid global argument" in result

    def test_multiple_invalid_global_args(self):
        """Test multiple invalid global args are caught."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 --bad --worse"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid global argument" in result

    def test_global_args_before_contexts(self):
        """Test global args must come before context keywords."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 --verbose video --fps 2"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_mixed_global_and_context_args(self):
        """Test global args mixed with context args."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 --show --verbose video --fps 2 sfm --method glomap"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_invalid_commands_caught_by_validation(self):
        """Test that manually constructed invalid commands are caught."""
        from webui import test_cmd

        # Invalid global arg
        cmd = "scripts/run.sh /test.mp4 --bad-flag"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid global argument" in result

        # Invalid video arg
        cmd = "scripts/run.sh /test.mp4 video --invalid-arg"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid video argument" in result

        # Invalid train arg
        cmd = "scripts/run.sh /test.mp4 train --bad-train-arg"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid train argument" in result


class TestVideoContextValidation:
    """Test test_cmd() function for video context argument validation."""

    def test_valid_video_args(self):
        """Test all valid video context args are accepted."""
        from webui import test_cmd

        valid_commands = [
            "scripts/run.sh /path/to/video.mp4 video --fps 2",
            "scripts/run.sh /path/to/video.mp4 video --frames 300",
            "scripts/run.sh /path/to/video.mp4 video --max-frames 300",
            "scripts/run.sh /path/to/video.mp4 video --time_slice 0:10",
            "scripts/run.sh /path/to/video.mp4 video --hdr",
            "scripts/run.sh /path/to/video.mp4 video --skip",
            "scripts/run.sh /path/to/video.mp4 video --overwrite",
            "scripts/run.sh /path/to/video.mp4 video --fps 2 --hdr --time_slice 0:10",
        ]
        for cmd in valid_commands:
            result = test_cmd(cmd, "scripts/run.sh")
            assert result is None, f"Valid video command rejected: {cmd}"

    def test_invalid_video_arg(self):
        """Test invalid video context args are rejected."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 video --invalid-video-flag"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid video argument" in result

    def test_multiple_invalid_video_args(self):
        """Test multiple invalid video args are caught."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 video --bad --worse"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid video argument" in result

    def test_video_args_within_video_context(self):
        """Test video args must be within video context."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 video --fps 2 sfm --method glomap"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_video_args_with_multiple_contexts(self):
        """Test video args work alongside other contexts."""
        from webui import test_cmd

        cmd = (
            "scripts/run.sh /path/to/video.mp4 video --fps 2 --hdr "
            "sfm --method glomap process --mask rembg train --model neus-facto"
        )
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_video_context_with_global_args(self):
        """Test video context works with global args."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 --show --verbose video --fps 2 --hdr"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None


class TestSfmContextValidation:
    """Test test_cmd() function for sfm context argument validation."""

    def test_valid_sfm_args(self):
        """Test all valid sfm context args are accepted."""
        from webui import test_cmd

        valid_commands = [
            "scripts/run.sh /path/to/video.mp4 sfm --method colmap",
            "scripts/run.sh /path/to/video.mp4 sfm --method glomap",
            "scripts/run.sh /path/to/video.mp4 sfm --matcher superglue",
            "scripts/run.sh /path/to/video.mp4 sfm --camera_model OPENCV",
            "scripts/run.sh /path/to/video.mp4 sfm --extra",
            "scripts/run.sh /path/to/video.mp4 sfm --refine_principal_point True",
            "scripts/run.sh /path/to/video.mp4 sfm --vggsfm_max_points 16384",
            "scripts/run.sh /path/to/video.mp4 sfm --vggsfm_max_tri_points 8192",
            "scripts/run.sh /path/to/video.mp4 sfm --hloc_camera OPENCV",
            "scripts/run.sh /path/to/video.mp4 sfm --hloc_feature superpoint_aachen",
            "scripts/run.sh /path/to/video.mp4 sfm --hloc_matcher superglue",
            "scripts/run.sh /path/to/video.mp4 sfm --hloc_weights outdoor",
            "scripts/run.sh /path/to/video.mp4 sfm --skip",
            "scripts/run.sh /path/to/video.mp4 sfm --overwrite",
            (
                "scripts/run.sh /path/to/video.mp4 sfm --method colmap "
                "--matcher superglue --camera_model OPENCV"
            ),
            (
                "scripts/run.sh /path/to/video.mp4 sfm --method hloc "
                "--hloc_feature superpoint_aachen --hloc_matcher superglue "
                "--hloc_weights outdoor"
            ),
        ]
        for cmd in valid_commands:
            result = test_cmd(cmd, "scripts/run.sh")
            assert result is None, f"Valid sfm command rejected: {cmd}"

    def test_invalid_sfm_arg(self):
        """Test invalid sfm context args are rejected."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 sfm --invalid-sfm-flag"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid sfm argument" in result

    def test_multiple_invalid_sfm_args(self):
        """Test multiple invalid sfm args are caught."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 sfm --bad --worse"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid sfm argument" in result

    def test_sfm_args_within_sfm_context(self):
        """Test sfm args must be within sfm context."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 sfm --method glomap process --mask rembg"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_sfm_args_with_multiple_contexts(self):
        """Test sfm args work alongside other contexts."""
        from webui import test_cmd

        cmd = (
            "scripts/run.sh /path/to/video.mp4 video --fps 2 "
            "sfm --method colmap --matcher superglue process train"
        )
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_sfm_context_with_global_args(self):
        """Test sfm context works with global args."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 --show sfm --method glomap --matcher superglue"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None


class TestProcessContextValidation:
    """Test test_cmd() function for process context argument validation."""

    def test_valid_process_args(self):
        """Test all valid process context args are accepted."""
        from webui import test_cmd

        valid_commands = [
            "scripts/run.sh /path/to/video.mp4 process --mask rembg",
            "scripts/run.sh /path/to/video.mp4 process --mask sam2",
            "scripts/run.sh /path/to/video.mp4 process --min-match-ratio 0.5",
            "scripts/run.sh /path/to/video.mp4 process --crop-factor 1.2",
            "scripts/run.sh /path/to/video.mp4 process --skip",
            "scripts/run.sh /path/to/video.mp4 process --overwrite",
            "scripts/run.sh /path/to/video.mp4 process --mask rembg --crop-factor 1.2",
        ]
        for cmd in valid_commands:
            result = test_cmd(cmd, "scripts/run.sh")
            assert result is None, f"Valid process command rejected: {cmd}"

    def test_invalid_process_arg(self):
        """Test invalid process context args are rejected."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 process --invalid-process-flag"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid process argument" in result

    def test_multiple_invalid_process_args(self):
        """Test multiple invalid process args are caught."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 process --bad --worse"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid process argument" in result

    def test_process_args_within_process_context(self):
        """Test process args must be within process context."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 process --mask rembg train --model neus-facto"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_process_args_with_multiple_contexts(self):
        """Test process args work alongside other contexts."""
        from webui import test_cmd

        cmd = (
            "scripts/run.sh /path/to/video.mp4 video --fps 2 "
            "sfm --method glomap process --mask rembg --crop-factor 1.2 train"
        )
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_process_context_with_global_args(self):
        """Test process context works with global args."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 --verbose process --mask rembg --crop-factor 1.2"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None


class TestTrainContextValidation:
    """Test test_cmd() function for train context argument validation."""

    def test_valid_train_args(self):
        """Test all valid train context args are accepted."""
        from webui import test_cmd

        valid_commands = [
            "scripts/run.sh /path/to/video.mp4 train --model neus-facto",
            "scripts/run.sh /path/to/video.mp4 train --config neus-facto-short",
            "scripts/run.sh /path/to/video.mp4 train --name my-experiment",
            "scripts/run.sh /path/to/video.mp4 train --vis tensorboard",
            "scripts/run.sh /path/to/video.mp4 train --downscale-factor 2",
            "scripts/run.sh /path/to/video.mp4 train --scale-factor 1.5",
            "scripts/run.sh /path/to/video.mp4 train --center-method focus",
            "scripts/run.sh /path/to/video.mp4 train --orientation-method vertical",
            "scripts/run.sh /path/to/video.mp4 train --auto-scale-poses median",
            "scripts/run.sh /path/to/video.mp4 train --train-split-fraction 0.9",
            "scripts/run.sh /path/to/video.mp4 train --skip",
            "scripts/run.sh /path/to/video.mp4 train --overwrite",
            "scripts/run.sh /path/to/video.mp4 train --resume",
            "scripts/run.sh /path/to/video.mp4 train --resume-step 3000",
            (
                "scripts/run.sh /path/to/video.mp4 train "
                "--pipeline.model.eval-num-rays-per-chunk 4096"
            ),
            (
                "scripts/run.sh /path/to/video.mp4 train "
                "--pipeline.datamanager.train-num-rays-per-batch 4096"
            ),
            (
                "scripts/run.sh /path/to/video.mp4 train "
                "--pipeline.model.sdf-field.use-reflections True"
            ),
            ("scripts/run.sh /path/to/video.mp4 train --viewer.quit-on-train-completion True"),
            (
                "scripts/run.sh /path/to/video.mp4 train --model neus-facto "
                "--config neus-facto-short --vis tensorboard"
            ),
            (
                "scripts/run.sh /path/to/video.mp4 train "
                "--pipeline.model.sdf-field.enable-pred-roughness True"
            ),
            ("scripts/run.sh /path/to/video.mp4 train --pipeline.model.orientation-loss-mult 0.01"),
            ("scripts/run.sh /path/to/video.mp4 train --pipeline.model.distortion-loss-mult 0.001"),
            (
                "scripts/run.sh /path/to/video.mp4 train "
                "--pipeline.model.sdf-field.enable-pred-roughness True "
                "--pipeline.model.orientation-loss-mult 0.01 "
                "--pipeline.model.distortion-loss-mult 0.001"
            ),
        ]
        for cmd in valid_commands:
            result = test_cmd(cmd, "scripts/run.sh")
            assert result is None, f"Valid train command rejected: {cmd}"

    def test_invalid_train_arg(self):
        """Test invalid train context args are rejected."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 train --invalid-train-flag"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid train argument" in result

    def test_multiple_invalid_train_args(self):
        """Test multiple invalid train args are caught."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 train --bad --worse"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid train argument" in result

    def test_train_args_within_train_context(self):
        """Test train args must be within train context."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 train --model neus-facto export --resolution 2048"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_train_args_with_multiple_contexts(self):
        """Test train args work alongside other contexts."""
        from webui import test_cmd

        cmd = (
            "scripts/run.sh /path/to/video.mp4 video --fps 2 "
            "sfm --method glomap process --mask rembg "
            "train --model neus-facto --config neus-facto-short export"
        )
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_train_context_with_global_args(self):
        """Test train context works with global args."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 --show train --model neus-facto --vis tensorboard"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None


class TestExportContextValidation:
    """Test test_cmd() function for export context argument validation."""

    def test_valid_export_args(self):
        """Test all valid export context args are accepted."""
        from webui import test_cmd

        valid_commands = [
            "scripts/run.sh /path/to/video.mp4 export --resolution 2048",
            "scripts/run.sh /path/to/video.mp4 export --marching-cube-threshold 0.5",
            "scripts/run.sh /path/to/video.mp4 export --num-pixels-per-side 2048",
            "scripts/run.sh /path/to/video.mp4 export --downscale-factor 2",
            "scripts/run.sh /path/to/video.mp4 export --method poisson",
            "scripts/run.sh /path/to/video.mp4 export --target-num-faces 50000",
            "scripts/run.sh /path/to/video.mp4 export --bounding-box-min -1.0 -1.0 -1.0",
            "scripts/run.sh /path/to/video.mp4 export --bounding-box-max 1.0 1.0 1.0",
            "scripts/run.sh /path/to/video.mp4 export --px-per-uv-triangle 4",
            "scripts/run.sh /path/to/video.mp4 export --obb-center 0 0 0",
            "scripts/run.sh /path/to/video.mp4 export --obb-scale 1 1 1",
            "scripts/run.sh /path/to/video.mp4 export --mesh-only",
            "scripts/run.sh /path/to/video.mp4 export --texture-only",
            (
                "scripts/run.sh /path/to/video.mp4 export "
                "--texture-only --input-mesh-filename /tmp/edited_mesh.ply"
            ),
            "scripts/run.sh /path/to/video.mp4 export --skip",
            "scripts/run.sh /path/to/video.mp4 export --overwrite",
            "scripts/run.sh /path/to/video.mp4 export --resolution 2048 --method poisson",
        ]
        for cmd in valid_commands:
            result = test_cmd(cmd, "scripts/run.sh")
            assert result is None, f"Valid export command rejected: {cmd}"

    def test_invalid_export_arg(self):
        """Test invalid export context args are rejected."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 export --invalid-export-flag"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid export argument" in result

    def test_multiple_invalid_export_args(self):
        """Test multiple invalid export args are caught."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 export --bad --worse"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is not None
        assert "Invalid export argument" in result

    def test_export_args_within_export_context(self):
        """Test export args must be within export context."""
        from webui import test_cmd

        cmd = "scripts/run.sh /path/to/video.mp4 export --resolution 2048"
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_export_args_with_multiple_contexts(self):
        """Test export args work alongside other contexts."""
        from webui import test_cmd

        cmd = (
            "scripts/run.sh /path/to/video.mp4 video --fps 2 "
            "sfm --method glomap process --mask rembg "
            "train --model neus-facto export --resolution 2048 --method poisson"
        )
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None

    def test_export_context_with_global_args(self):
        """Test export context works with global args."""
        from webui import test_cmd

        cmd = (
            "scripts/run.sh /path/to/video.mp4 --verbose export --resolution 2048 --method poisson"
        )
        result = test_cmd(cmd, "scripts/run.sh")
        assert result is None


class TestRunPipelineInputPath:
    """Test run_pipeline() function for input path handling."""

    def test_basic_command_with_input_path(self):
        """Test run_pipeline builds basic command with input path."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4")
        assert cmd == "scripts/run.sh /path/to/video.mp4"

    def test_input_path_with_spaces(self):
        """Test input path with spaces is properly quoted."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/my video.mp4")
        assert cmd == 'scripts/run.sh "/path/to/my video.mp4"'

    def test_missing_input_path(self):
        """Test missing input path returns error."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path=None)
        assert cmd == ""

    def test_empty_input_path(self):
        """Test empty input path returns error."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="")
        assert cmd == ""


class TestRunPipelineGlobalArgs:
    """Test run_pipeline() function for global argument building."""

    def test_global_show(self):
        """Test global --show flag."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", global_show=True)
        assert cmd == "scripts/run.sh /path/to/video.mp4 --show"

    def test_global_verbose(self):
        """Test global --verbose flag."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", global_verbose=True)
        assert cmd == "scripts/run.sh /path/to/video.mp4 --verbose"

    def test_global_overwrite(self):
        """Test global --overwrite flag."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", global_overwrite=True)
        assert cmd == "scripts/run.sh /path/to/video.mp4 --overwrite"

    def test_multiple_global_args(self):
        """Test multiple global args."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            global_show=True,
            global_verbose=True,
            global_overwrite=True,
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 --show --verbose --overwrite"


class TestRunPipelineVideoContext:
    """Test run_pipeline() function for video context building."""

    def test_video_context_basic(self):
        """Test basic video context."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", video_enable=True)
        assert cmd == "scripts/run.sh /path/to/video.mp4 video"

    def test_video_fps(self):
        """Test video --fps argument."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", video_enable=True, video_fps=2)
        assert cmd == "scripts/run.sh /path/to/video.mp4 video --fps 2"

    def test_video_frames(self):
        """Test video --frames argument."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", video_enable=True, video_frames=300)
        assert cmd == "scripts/run.sh /path/to/video.mp4 video --frames 300"

    def test_video_max_frames(self):
        """Test video --max-frames argument."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", video_enable=True, video_max_frames=300)
        assert cmd == "scripts/run.sh /path/to/video.mp4 video --max-frames 300"

    def test_video_time_slice(self):
        """Test video --time_slice argument."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4", video_enable=True, video_time_slice="0:10"
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 video --time_slice 0:10"

    def test_video_hdr(self):
        """Test video --hdr flag."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", video_enable=True, video_hdr=True)
        assert cmd == "scripts/run.sh /path/to/video.mp4 video --hdr"

    def test_video_multiple_args(self):
        """Test video context with multiple arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            video_enable=True,
            video_fps=2,
            video_hdr=True,
            video_skip=True,
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 video --fps 2 --hdr --skip"


class TestRunPipelineSfmContext:
    """Test run_pipeline() function for sfm context building."""

    def test_sfm_context_basic(self):
        """Test basic sfm context."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", sfm_enable=True)
        assert cmd == "scripts/run.sh /path/to/video.mp4 sfm"

    def test_sfm_method(self):
        """Test sfm --method argument."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", sfm_enable=True, sfm_method="glomap")
        assert cmd == "scripts/run.sh /path/to/video.mp4 sfm --method glomap"

    def test_sfm_matcher(self):
        """Test sfm --matcher argument."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4", sfm_enable=True, sfm_matcher="superglue"
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 sfm --matcher superglue"

    def test_sfm_auto_method_and_matcher_are_omitted(self):
        """Auto SfM selections should be left for scripts/run.sh to resolve."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            sfm_enable=True,
            sfm_method="auto",
            sfm_matcher="auto",
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 sfm"

    def test_sfm_multiple_args(self):
        """Test sfm context with multiple arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            sfm_enable=True,
            sfm_method="colmap",
            sfm_matcher="superglue",
            sfm_skip=True,
        )
        assert (
            cmd
            == "scripts/run.sh /path/to/video.mp4 sfm --method colmap --matcher superglue --skip"
        )


class TestRunPipelineProcessContext:
    """Test run_pipeline() function for process context building."""

    def test_process_context_basic(self):
        """Test basic process context."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", process_enable=True)
        assert cmd == "scripts/run.sh /path/to/video.mp4 process"

    def test_process_mask(self):
        """Test process --mask argument."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4", process_enable=True, process_mask="rembg"
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 process --mask rembg"

    def test_process_crop_factor(self):
        """Test process --crop-factor argument."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            process_enable=True,
            process_crop_factor=1.2,
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 process --crop-factor 1.2"

    def test_process_multiple_args(self):
        """Test process context with multiple arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            process_enable=True,
            process_mask="sam2",
            process_crop_factor=1.5,
            process_overwrite=True,
        )
        assert (
            cmd
            == "scripts/run.sh /path/to/video.mp4 process --mask sam2 --crop-factor 1.5 --overwrite"
        )


class TestRunPipelineTrainContext:
    """Test run_pipeline() function for train context building."""

    def test_train_context_basic(self):
        """Test basic train context."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", train_enable=True)
        assert cmd == "scripts/run.sh /path/to/video.mp4 train"

    def test_train_model(self):
        """Test train --model argument."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4", train_enable=True, train_model="neus-facto"
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 train --model neus-facto"

    def test_train_config(self):
        """Test train --config argument."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_config="neus-facto-short",
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 train --config neus-facto-short"

    def test_train_multiple_args(self):
        """Test train context with multiple arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_model="neus-facto",
            train_config="neus-facto-short",
            train_vis="tensorboard",
            train_skip=True,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 train --model neus-facto "
            "--config neus-facto-short --vis tensorboard --skip"
        )

    def test_train_data_args(self):
        """Test train context with data-related arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_model="neus-facto",
            train_downscale_factor=2,
            train_scale_factor=1.5,
            train_center_method="focus",
            train_orientation_method="vertical",
            train_auto_scale_poses="median",
            train_split_fraction=0.9,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 train --model neus-facto "
            "--downscale-factor 2 --scale-factor 1.5 --center-method focus "
            "--orientation-method vertical --auto-scale-poses median "
            "--train-split-fraction 0.9"
        )

    def test_train_brdf_flags(self):
        """Test train context with BRDF/shading flags."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_use_reflections=True,
            train_use_diffuse_specular=True,
            train_use_specular_tint=True,
            train_enable_pred_roughness=True,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 train "
            "--pipeline.model.sdf-field.use-reflections True "
            "--pipeline.model.sdf-field.use-n-dot-v True "
            "--pipeline.model.sdf-field.use-diffuse-color True "
            "--pipeline.model.sdf-field.use-specular-tint True "
            "--pipeline.model.sdf-field.enable-pred-roughness True"
        )

    def test_train_regularization_losses(self):
        """Test train context with regularization loss multipliers."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_model="neus-facto",
            train_orientation_loss_mult=0.01,
            train_distortion_loss_mult=0.001,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 train --model neus-facto "
            "--pipeline.model.orientation-loss-mult 0.01 "
            "--pipeline.model.distortion-loss-mult 0.001"
        )

    def test_train_all_new_flags_combined(self):
        """Test train context with all new BRDF and loss flags."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_model="neus-facto",
            train_config="neus-facto",
            train_use_reflections=True,
            train_use_diffuse_specular=True,
            train_use_specular_tint=True,
            train_enable_pred_roughness=True,
            train_orientation_loss_mult=0.01,
            train_distortion_loss_mult=0.001,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 train --model neus-facto "
            "--config neus-facto "
            "--pipeline.model.sdf-field.use-reflections True "
            "--pipeline.model.sdf-field.use-n-dot-v True "
            "--pipeline.model.sdf-field.use-diffuse-color True "
            "--pipeline.model.sdf-field.use-specular-tint True "
            "--pipeline.model.sdf-field.enable-pred-roughness True "
            "--pipeline.model.orientation-loss-mult 0.01 "
            "--pipeline.model.distortion-loss-mult 0.001"
        )

    def test_train_diffuse_specular_does_not_enable_specular_tint(self):
        """Diffuse/specular split should not imply metal-only specular tint."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_use_diffuse_specular=True,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 train "
            "--pipeline.model.sdf-field.use-diffuse-color True"
        )

    def test_train_specular_tint_flag(self):
        """Test train context with metal specular tint enabled separately."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_use_specular_tint=True,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 train "
            "--pipeline.model.sdf-field.use-specular-tint True"
        )


class TestRunPipelineExportContext:
    """Test run_pipeline() function for export context building."""

    def test_export_context_basic(self):
        """Test basic export context."""
        from webui import run_pipeline

        cmd = run_pipeline(input_path="/path/to/video.mp4", export_enable=True)
        assert cmd == "scripts/run.sh /path/to/video.mp4 export"

    def test_export_resolution(self):
        """Test export --resolution argument."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4", export_enable=True, export_resolution=2048
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 export --resolution 2048"

    def test_export_method(self):
        """Test export --method argument."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4", export_enable=True, export_method="poisson"
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 export --method poisson"

    def test_export_multiple_args(self):
        """Test export context with multiple arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            export_enable=True,
            export_resolution=2048,
            export_method="poisson",
            export_overwrite=True,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 export --resolution 2048 "
            "--method poisson --overwrite"
        )

    def test_export_additional_args(self):
        """Test export context with additional SDF/NeRF arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            export_enable=True,
            export_resolution=256,
            export_method="poisson",
            export_marching_cube_threshold=0.5,
            export_num_pixels_per_side=4096,
            export_target_num_faces=50000,
            export_px_per_uv_triangle=4,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 export --resolution 256 "
            "--method poisson --marching-cube-threshold 0.5 "
            "--num-pixels-per-side 4096 --target-num-faces 50000 "
            "--px-per-uv-triangle 4"
        )

    def test_export_obb_args(self):
        """Test export context with OBB arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            export_enable=True,
            export_method="poisson",
            export_obb_center_x=0.0,
            export_obb_center_y=1.0,
            export_obb_center_z=2.0,
            export_obb_scale_x=1.0,
            export_obb_scale_y=2.0,
            export_obb_scale_z=3.0,
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 export --method poisson "
            "--obb-center 0.0 1.0 2.0 --obb-scale 1.0 2.0 3.0"
        )

    def test_export_mesh_only_and_texture_only(self):
        """Test export context with mesh-only / texture-only flags."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            export_enable=True,
            export_mesh_only=True,
        )
        assert cmd == "scripts/run.sh /path/to/video.mp4 export --mesh-only"

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            export_enable=True,
            export_texture_only=True,
            export_input_mesh_filename="/tmp/edited_mesh.ply",
        )
        assert cmd == (
            "scripts/run.sh /path/to/video.mp4 export "
            "--texture-only --input-mesh-filename /tmp/edited_mesh.ply"
        )


class TestRunPipelineMultipleContexts:
    """Test run_pipeline() function with multiple contexts combined."""

    def test_all_contexts_combined(self):
        """Test command with all contexts enabled."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            global_verbose=True,
            video_enable=True,
            video_fps=2,
            sfm_enable=True,
            sfm_method="glomap",
            process_enable=True,
            process_mask="rembg",
            train_enable=True,
            train_model="neus-facto",
            export_enable=True,
            export_resolution=2048,
        )
        expected = (
            "scripts/run.sh /path/to/video.mp4 --verbose "
            "video --fps 2 "
            "sfm --method glomap "
            "process --mask rembg "
            "train --model neus-facto "
            "export --resolution 2048"
        )
        assert cmd == expected

    def test_partial_contexts(self):
        """Test command with some contexts enabled."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            video_enable=True,
            video_fps=2,
            train_enable=True,
            train_model="neus-facto",
            export_enable=True,
            export_resolution=2048,
        )
        expected = (
            "scripts/run.sh /path/to/video.mp4 "
            "video --fps 2 "
            "train --model neus-facto "
            "export --resolution 2048"
        )
        assert cmd == expected

    def test_context_enable_flags_control_output(self):
        """Test that enable flags correctly control whether contexts appear."""
        from webui import run_pipeline

        # Contexts disabled (default)
        cmd = run_pipeline(
            input_path="/test.mp4",
            video_fps=2,  # Set but context not enabled
            sfm_method="glomap",  # Set but context not enabled
        )
        assert "video" not in cmd
        assert "sfm" not in cmd
        assert cmd == "scripts/run.sh /test.mp4"

        # Contexts enabled
        cmd = run_pipeline(
            input_path="/test.mp4",
            video_enable=True,
            video_fps=2,
            sfm_enable=True,
            sfm_method="glomap",
        )
        assert "video --fps 2" in cmd
        assert "sfm --method glomap" in cmd


class TestIntegration:
    """Integration tests verifying components work together correctly."""

    def test_run_pipeline_output_validates_successfully(self):
        """Test that run_pipeline output passes test_cmd validation."""
        from webui import run_pipeline, test_cmd

        # Build a complex command
        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            global_verbose=True,
            video_enable=True,
            video_fps=2,
            video_hdr=True,
            sfm_enable=True,
            sfm_method="glomap",
            sfm_matcher="superglue",
            process_enable=True,
            process_mask="rembg",
            process_crop_factor=1.2,
            train_enable=True,
            train_model="neus-facto",
            train_config="neus-facto-short",
            train_vis="tensorboard",
            export_enable=True,
            export_resolution=2048,
            export_method="poisson",
        )

        # Validate it
        validation_result = test_cmd(cmd, "scripts/run.sh")
        assert validation_result is None, f"Generated invalid command: {validation_result}"
        assert "scripts/run.sh" in cmd
        assert "/path/to/video.mp4" in cmd

    def test_all_single_context_commands_validate(self):
        """Test that each context independently produces valid commands."""
        from webui import run_pipeline, test_cmd

        test_cases = [
            # Video only
            {
                "input_path": "/test.mp4",
                "video_enable": True,
                "video_fps": 2,
            },
            # SfM only
            {
                "input_path": "/test.mp4",
                "sfm_enable": True,
                "sfm_method": "colmap",
            },
            # Process only
            {
                "input_path": "/test.mp4",
                "process_enable": True,
                "process_mask": "rembg",
            },
            # Train only
            {
                "input_path": "/test.mp4",
                "train_enable": True,
                "train_model": "neus-facto",
            },
            # Export only
            {
                "input_path": "/test.mp4",
                "export_enable": True,
                "export_resolution": 2048,
            },
        ]

        for params in test_cases:
            cmd = run_pipeline(**params)
            validation_result = test_cmd(cmd, "scripts/run.sh")
            assert validation_result is None, (
                f"Command failed validation: {cmd} -> {validation_result}"
            )

    def test_all_context_combinations_validate(self):
        """Test that various context combinations produce valid commands."""
        from webui import run_pipeline, test_cmd

        # Test 10 different realistic combinations
        combinations = [
            # Basic: video + train + export
            {
                "video_enable": True,
                "video_fps": 1,
                "train_enable": True,
                "train_model": "neus-facto",
                "export_enable": True,
                "export_resolution": 2048,
            },
            # SfM + train
            {
                "sfm_enable": True,
                "sfm_method": "glomap",
                "train_enable": True,
                "train_model": "nerfacto",
            },
            # Video + SfM + process
            {
                "video_enable": True,
                "video_fps": 2,
                "sfm_enable": True,
                "sfm_method": "colmap",
                "process_enable": True,
                "process_mask": "sam2",
            },
            # All contexts
            {
                "video_enable": True,
                "video_fps": 1,
                "sfm_enable": True,
                "sfm_method": "glomap",
                "process_enable": True,
                "process_mask": "rembg",
                "train_enable": True,
                "train_model": "neus-facto",
                "export_enable": True,
                "export_resolution": 4096,
            },
            # With global args
            {
                "global_verbose": True,
                "global_show": True,
                "train_enable": True,
                "train_model": "splatfacto",
            },
        ]

        for combo in combinations:
            params = {"input_path": "/test.mp4", **combo}
            cmd = run_pipeline(**params)
            validation_result = test_cmd(cmd, "scripts/run.sh")
            assert validation_result is None, (
                f"Combination failed: {combo} -> {cmd} -> {validation_result}"
            )

    def test_scripts_run_sh_exists(self):
        """Verify that scripts/run.sh exists (smoke test)."""
        import os

        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "run.sh")
        assert os.path.exists(script_path), (
            f"scripts/run.sh not found at {script_path}. Integration with actual pipeline may fail."
        )
        assert os.access(script_path, os.X_OK), (
            f"scripts/run.sh exists but is not executable: {script_path}"
        )

    def test_edge_cases_validate_correctly(self):
        """Test edge cases produce appropriate validation results."""
        from webui import run_pipeline, test_cmd

        # Empty input path should produce empty command
        cmd = run_pipeline(input_path="")
        assert cmd == ""

        # None input path should produce empty command
        cmd = run_pipeline(input_path=None)
        assert cmd == ""

        # Path with spaces should be quoted and validate
        cmd = run_pipeline(
            input_path="/path/to/my video.mp4", train_enable=True, train_model="neus-facto"
        )
        validation_result = test_cmd(cmd, "scripts/run.sh")
        assert validation_result is None
        assert '"/path/to/my video.mp4"' in cmd


class TestRunPipelineEdgeCases:
    """Test edge cases and less common code paths in run_pipeline()."""

    def test_video_overwrite_flag(self):
        """Test video context with overwrite flag."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            video_enable=True,
            video_overwrite=True,
        )
        assert "--overwrite" in cmd

    def test_sfm_overwrite_flag(self):
        """Test sfm context with overwrite flag."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            sfm_enable=True,
            sfm_overwrite=True,
        )
        assert "sfm --overwrite" in cmd

    def test_sfm_extra_args(self):
        """Test sfm context with extra args."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            sfm_enable=True,
            sfm_method="colmap",
            sfm_extra_args="--custom-flag value",
        )
        assert "sfm --method colmap --custom-flag value" in cmd

    def test_process_extra_args(self):
        """Test process context with extra args."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            process_enable=True,
            process_extra_args="--extra-option 123",
        )
        assert "process --extra-option 123" in cmd

    def test_train_extra_args(self):
        """Test train context with extra args."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            train_enable=True,
            train_extra_args="--custom-train-flag value",
        )
        assert "train --custom-train-flag value" in cmd

    def test_export_extra_args(self):
        """Test export context with extra args."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            export_enable=True,
            export_extra_args="--custom-export-flag",
        )
        assert "export --custom-export-flag" in cmd

    def test_sfm_refine_principal_point_false(self):
        """Test sfm with refine_principal_point=False."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            sfm_enable=True,
            sfm_refine_principal_point=False,
        )
        assert "--refine_principal_point False" in cmd

    def test_sfm_num_threads(self):
        """Test sfm with num_threads specified."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            sfm_enable=True,
            sfm_num_threads=8,
        )
        assert "--num_threads 8" in cmd

    def test_sfm_hloc_args(self):
        """Test sfm with hloc arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            sfm_enable=True,
            sfm_hloc_camera="OPENCV",
            sfm_hloc_feature="superpoint_aachen",
            sfm_hloc_matcher="superglue",
            sfm_hloc_weights="outdoor",
        )
        assert "--hloc_camera OPENCV" in cmd
        assert "--hloc_feature superpoint_aachen" in cmd
        assert "--hloc_matcher superglue" in cmd
        assert "--hloc_weights outdoor" in cmd

    def test_sfm_vggsfm_args(self):
        """Test sfm with vggsfm arguments."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            sfm_enable=True,
            sfm_vggsfm_max_points=16384,
            sfm_vggsfm_max_tri_points=8192,
        )
        assert "--vggsfm_max_points 16384" in cmd
        assert "--vggsfm_max_tri_points 8192" in cmd

    def test_process_crop_factor_string(self):
        """Test process with crop_factor as string."""
        import shlex

        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            process_enable=True,
            process_crop_factor="0.1 0.2 0.3 0.4",
        )
        assert '"0.1 0.2 0.3 0.4"' in cmd
        assert shlex.split(cmd)[-1] == "0.1 0.2 0.3 0.4"

    def test_process_min_match_ratio(self):
        """Test process with min_match_ratio."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            process_enable=True,
            process_min_match_ratio=0.5,
        )
        assert "--min-match-ratio 0.5" in cmd

    def test_train_all_ray_options(self):
        """Test train with all ray-related options."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            train_enable=True,
            train_eval_num_rays_per_chunk=8192,
            train_train_num_rays_per_batch=4096,
            train_eval_num_rays_per_batch=2048,
        )
        assert "--pipeline.model.eval-num-rays-per-chunk 8192" in cmd
        assert "--pipeline.datamanager.train-num-rays-per-batch 4096" in cmd
        assert "--pipeline.datamanager.eval-num-rays-per-batch 2048" in cmd

    def test_train_camera_optimizer_mode(self):
        """Test train with camera_optimizer_mode."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            train_enable=True,
            train_camera_optimizer_mode="SO3xR3",
        )
        assert "--pipeline.datamanager.camera-optimizer.mode SO3xR3" in cmd

    def test_train_disable_appearance_embedding(self):
        """Test train with appearance embedding disabled."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            train_enable=True,
            train_disable_appearance_embedding=True,
        )
        assert "--pipeline.model.sdf-field.use-appearance-embedding False" in cmd

    def test_train_viewer_quit_on_completion(self):
        """Test train with viewer quit on completion."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            train_enable=True,
            train_viewer_quit_on_completion=True,
        )
        assert "--viewer.quit-on-train-completion True" in cmd

    def test_export_downscale_factor(self):
        """Test export with downscale_factor."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            export_enable=True,
            export_downscale_factor=2,
        )
        assert "--downscale-factor 2" in cmd

    def test_docker_mode(self):
        """Test docker mode uses correct script."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            mode="docker",
            train_enable=True,
        )
        assert cmd.startswith("docker/run.sh")

    def test_sfm_camera_model_non_default(self):
        """Test sfm with non-default camera model."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            sfm_enable=True,
            sfm_camera_model="PINHOLE",
        )
        assert "--camera_model PINHOLE" in cmd

    def test_sfm_extra_flag(self):
        """Test sfm with extra flag."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            sfm_enable=True,
            sfm_extra=True,
        )
        assert "sfm --extra" in cmd

    def test_process_skip_flag(self):
        """Test process with skip flag."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            process_enable=True,
            process_skip=True,
        )
        assert "process --skip" in cmd

    def test_train_name(self):
        """Test train with experiment name."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            train_enable=True,
            train_name="my-experiment",
        )
        assert "--name my-experiment" in cmd

    def test_train_overwrite_flag(self):
        """Test train with overwrite flag."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            train_enable=True,
            train_overwrite=True,
        )
        assert "train --overwrite" in cmd

    def test_train_resume_flags(self):
        """Test train resume flags."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            train_enable=True,
            train_resume=True,
            train_resume_step=3000,
        )
        assert cmd == "scripts/run.sh /test.mp4 train --resume --resume-step 3000"

    def test_export_skip_flag(self):
        """Test export with skip flag."""
        from webui import run_pipeline

        cmd = run_pipeline(
            input_path="/test.mp4",
            export_enable=True,
            export_skip=True,
        )
        assert "export --skip" in cmd


class TestStructuredCommandBuilder:
    """Tests for argv-safe command construction used by the run launcher."""

    def test_build_pipeline_argv_preserves_path_with_spaces(self):
        """The executor should receive argv, not a shell-quoted command string."""
        from webui import build_pipeline_argv, run_pipeline

        argv = build_pipeline_argv(
            input_path="/path/to/my video.mp4",
            train_enable=True,
            train_model="neus-facto",
        )

        assert argv[:2] == ["scripts/run.sh", "/path/to/my video.mp4"]
        assert "--model" in argv
        assert (
            run_pipeline(
                input_path="/path/to/my video.mp4",
                train_enable=True,
                train_model="neus-facto",
            )
            == 'scripts/run.sh "/path/to/my video.mp4" train --model neus-facto'
        )

    def test_run_pipeline_quotes_whitespace_in_non_input_values(self):
        """Preview text should be copy-paste safe for every whitespace-bearing arg."""
        import shlex

        from webui import build_pipeline_argv, run_pipeline

        argv = build_pipeline_argv(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_name="my run",
            train_config="configs/has space.sh",
        )
        cmd = run_pipeline(
            input_path="/path/to/video.mp4",
            train_enable=True,
            train_name="my run",
            train_config="configs/has space.sh",
        )

        assert '"my run"' in cmd
        assert '"configs/has space.sh"' in cmd
        assert shlex.split(cmd) == argv

    def test_validate_run_argv_rejects_resume_with_overwrite(self):
        """The launcher should catch resume/overwrite conflicts before spawning."""
        from webui import validate_run_argv

        validation = validate_run_argv(["scripts/run.sh", "/x", "--overwrite", "train", "--resume"])

        assert validation is not None
        assert "resume" in validation
        assert "overwrite" in validation

    def test_ui_control_defaults_track_script_defaults(self):
        """The UI-visible defaults should match values omitted by the launcher."""
        text = Path(__file__).resolve().parents[1].joinpath("webui.py").read_text(encoding="utf-8")

        assert 'label="Method",' in text
        assert 'value="auto",' in text
        assert 'label="Matcher",' in text
        assert 'value="auto",' in text
        assert 'label="Model",' in text
        assert 'value="neus-facto",' in text
        assert 'label="Config",' in text
        assert 'value="neus-facto-short",' in text

        assert 'if sfm_method_val == "auto":' in text
        assert 'if sfm_matcher_val == "auto":' in text
        assert 'if train_model_val == "neus-facto":' in text
        assert 'if train_config_val == "neus-facto-short":' in text


class TestStageTracker:
    """Tests for parsing scripts/run.sh stage banners into UI state."""

    def test_stage_tracker_marks_running_skipped_and_done(self):
        """Stage summary should follow the existing run.sh log format."""
        from webui import StageTracker

        tracker = StageTracker()
        for line in [
            "=============================",
            "          1. VIDEO           ",
            "=============================",
            "[INFO]: Running video stage",
            "=============================",
            "          2. SfM             ",
            "=============================",
            "[INFO]: SfM output /tmp/sparse already exists; skipping (use --overwrite to rerun)",
            "=============================",
            "          FINISHED           ",
            "=============================",
            "Job 'demo': SUCCESS",
        ]:
            tracker.consume(line)

        assert "VIDEO: done" in tracker.summary()
        assert "SfM: skipped" in tracker.summary()
        assert "EXPORT: pending" in tracker.summary()

    def test_stage_tracker_uses_stage_prefix_not_path_substrings(self):
        """A path containing another stage name must not redirect skip state."""
        from webui import StageTracker

        tracker = StageTracker()
        for line in [
            "          2. SfM             ",
            (
                "[INFO]: SfM output /tmp/video_demo/sparse already exists; "
                "skipping (use --overwrite to rerun)"
            ),
        ]:
            tracker.consume(line)

        assert "VIDEO: pending" in tracker.summary()
        assert "SfM: skipped" in tracker.summary()


class FakeStdout:
    """Minimal stdout iterable for fake subprocesses."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = iter(lines)

    def readline(self) -> str:
        return next(self._lines, "")

    def close(self) -> None:
        return None


class FakeProcess:
    """Small fake Popen result for runner tests."""

    def __init__(self, lines: list[str], returncode: int = 0) -> None:
        self.stdout = FakeStdout(lines)
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode if self.terminated else None

    def wait(self, timeout: float | None = None) -> int:
        self.terminated = True
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15

    def kill(self) -> None:
        self.killed = True
        self.terminated = True
        self.returncode = -9


class TestPipelineRunner:
    """Tests for the local single-run subprocess wrapper."""

    def test_runner_streams_output_and_records_success(self, tmp_path: Path):
        """A run should yield streamed log text and final succeeded status."""
        from webui import PipelineRunner

        captured: dict[str, object] = {}

        def factory(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return FakeProcess(["line 1\n", "line 2\n"], returncode=0)

        runner = PipelineRunner(repo_root=tmp_path, process_factory=factory)
        updates = list(runner.run(["scripts/run.sh", "/tmp/input.mp4"]))

        assert captured["argv"][-2:] == ["scripts/run.sh", "/tmp/input.mp4"]
        assert captured["kwargs"]["shell"] is False
        assert updates[-1].status == "succeeded"
        assert updates[-1].exit_code == 0
        assert "line 1" in updates[-1].log

    def test_runner_uses_stdbuf_when_available(self, tmp_path: Path, monkeypatch):
        """Linux stdbuf should make child logs line-buffered when available."""
        import webui
        from webui import PipelineRunner

        captured: dict[str, object] = {}
        monkeypatch.setattr(webui.shutil, "which", lambda name: "/usr/bin/stdbuf")

        def factory(argv, **kwargs):
            captured["argv"] = argv
            return FakeProcess([], returncode=0)

        runner = PipelineRunner(repo_root=tmp_path, process_factory=factory)
        list(runner.run(["scripts/run.sh", "/tmp/input.mp4"]))

        assert captured["argv"][:3] == ["stdbuf", "-oL", "-eL"]

    def test_runner_reports_spawn_failures(self, tmp_path: Path):
        """OSError from Popen should become a visible failed run update."""
        from webui import PipelineRunner

        def factory(argv, **kwargs):
            raise PermissionError("cannot execute")

        runner = PipelineRunner(repo_root=tmp_path, process_factory=factory)
        updates = list(runner.run(["scripts/run.sh", "/tmp/input.mp4"]))

        assert updates[-1].status == "failed"
        assert "cannot execute" in updates[-1].log

    def test_runner_caps_streamed_log_buffer(self, tmp_path: Path):
        """Long runs should not resend an unbounded full log on every line."""
        from webui import PipelineRunner

        runner = PipelineRunner(
            repo_root=tmp_path,
            process_factory=lambda argv, **kwargs: FakeProcess(
                [f"line {index}\n" for index in range(5)],
                returncode=0,
            ),
            max_log_lines=3,
        )
        updates = list(runner.run(["scripts/run.sh", "/tmp/input.mp4"]))

        assert "line 0" not in updates[-1].log
        assert "line 2" in updates[-1].log

    def test_runner_rejects_second_active_run(self, tmp_path: Path):
        """Only one GPU-bound pipeline should be active from the Web UI."""
        from webui import PipelineRunner

        runner = PipelineRunner(
            repo_root=tmp_path,
            process_factory=lambda argv, **kwargs: FakeProcess([], returncode=0),
        )
        runner._process = FakeProcess([], returncode=None)  # noqa: SLF001

        try:
            updates = list(runner.run(["scripts/run.sh", "/tmp/input.mp4"]))
        finally:
            runner._process = None  # noqa: SLF001

        assert updates[-1].status == "failed"
        assert "already running" in updates[-1].log

    def test_runner_stop_terminates_active_process(self, tmp_path: Path):
        """Stop should terminate the active child process."""
        from webui import PipelineRunner

        fake = FakeProcess([], returncode=None)
        runner = PipelineRunner(
            repo_root=tmp_path,
            process_factory=lambda argv, **kwargs: fake,
        )
        runner._process = fake  # noqa: SLF001

        result = runner.stop()

        assert result == "stopped"
        assert fake.terminated is True


class TestArtifactDiscovery:
    """Tests for simple result artifact discovery."""

    def test_find_mesh_artifacts_prefers_mesh_like_outputs(self, tmp_path: Path):
        """The result panel should find common mesh/splat outputs after a run."""
        from webui import find_mesh_artifacts

        (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")
        (tmp_path / "train" / "demo" / "neus" / "run").mkdir(parents=True)
        mesh_dir = tmp_path / "train" / "demo" / "neus" / "run"
        mesh = mesh_dir / "mesh.ply"
        textured_mesh = mesh_dir / "mesh.obj"
        mesh.write_text("ply\n", encoding="utf-8")
        textured_mesh.write_text("obj\n", encoding="utf-8")

        assert find_mesh_artifacts(tmp_path)[:2] == [str(textured_mesh), str(mesh)]


class TestCreateUI:
    """Smoke tests for the Gradio layout."""

    def test_create_ui_builds_blocks(self):
        """create_ui() should construct a Gradio Blocks app without raising."""
        import gradio as gr
        from webui import create_ui

        demo = create_ui()
        assert isinstance(demo, gr.Blocks)
