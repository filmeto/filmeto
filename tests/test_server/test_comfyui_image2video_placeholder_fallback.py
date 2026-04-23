import pytest

from server.plugins.comfy_ui_server.main import ComfyUiServerPlugin


class _FakeClient:
    def __init__(self):
        self.uploaded = []
        self.workflow_seen = None

    async def upload_image(self, image_path):
        self.uploaded.append(image_path)
        return "uploaded_input.png"

    async def run_workflow(self, workflow, progress_callback, output_dir, task_id):
        self.workflow_seen = workflow
        return ["/tmp/fake_output.mp4"]


@pytest.mark.asyncio
async def test_image2video_fallback_replaces_placeholders_without_node_mapping():
    plugin = ComfyUiServerPlugin()
    client = _FakeClient()

    async def fake_load_workflow(name, server_config=None):
        assert name == "image2video"
        prompt_graph = {
            "16": {
                "inputs": {
                    "positive_prompt": "$prompt",
                }
            },
            "67": {
                "inputs": {
                    "image": "$inputImage",
                }
            },
        }
        # Simulate workspace workflow without filmeto.node_mapping.
        return prompt_graph, {}

    plugin._load_workflow = fake_load_workflow  # type: ignore[method-assign]

    result = await plugin._execute_image2video(
        client=client,
        task_id="task-placeholder-fallback",
        parameters={
            "prompt": "hello world",
            "processed_resources": ["/tmp/input.png"],
        },
        progress_callback=lambda _p, _m, _d: None,
        server_config=None,
    )

    assert result["status"] == "success"
    assert result["output_files"] == ["/tmp/fake_output.mp4"]
    assert client.workflow_seen["16"]["inputs"]["positive_prompt"] == "hello world"
    assert client.workflow_seen["67"]["inputs"]["image"] == "uploaded_input.png"
