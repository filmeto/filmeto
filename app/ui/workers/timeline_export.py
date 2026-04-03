"""Timeline video export worker (FFmpeg pipeline)."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

from app.ui.core.base_worker import BaseWorker


class TimelineExportWorker(BaseWorker):
    """Runs FFmpeg-based export off the UI thread via ``TaskManager``."""

    def __init__(self, export_params: Dict[str, Any], task_id: Optional[str] = None):
        super().__init__(task_id=task_id, task_type="timeline_export")
        self.export_params = export_params

    def execute(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_run())
        finally:
            loop.close()

    async def _async_run(self) -> None:
        from utils.ffmpeg_utils import images_to_video, merge_videos, ensure_ffmpeg

        if not await ensure_ffmpeg():
            raise RuntimeError("FFmpeg is required but could not be installed.")

        timeline_items = self.export_params["timeline_items"]
        export_mode = self.export_params["export_mode"]
        items_per_video = self.export_params["items_per_video"]
        output_dir = self.export_params["output_dir"]
        fps = self.export_params["fps"]

        if export_mode == "all_as_one":
            await self._export_all_as_one(timeline_items, output_dir, fps)
        elif export_mode == "grouped":
            await self._export_grouped(timeline_items, items_per_video, output_dir, fps)
        elif export_mode == "individual":
            await self._export_individual(timeline_items, output_dir, fps)

    def _get_unique_filename(self, base_path: str) -> str:
        if not os.path.exists(base_path):
            return base_path

        directory = os.path.dirname(base_path)
        filename = os.path.basename(base_path)
        name, ext = os.path.splitext(filename)

        counter = 1
        while True:
            new_filename = f"{name} ({counter}){ext}"
            new_path = os.path.join(directory, new_filename)
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    async def _export_all_as_one(self, timeline_items, output_dir: str, fps: int) -> None:
        from utils.ffmpeg_utils import images_to_video, merge_videos

        all_media_paths: List[str] = []
        for item in timeline_items:
            self.check_cancelled()
            video_path = item.get_video_path()
            image_path = item.get_image_path()

            if video_path and os.path.exists(video_path):
                all_media_paths.append(video_path)
            elif image_path and os.path.exists(image_path):
                all_media_paths.append(image_path)

        if not all_media_paths:
            raise RuntimeError("No media items found to export.")

        base_output_path = os.path.join(output_dir, "timeline_export_all.mp4")
        output_path = self._get_unique_filename(base_output_path)

        image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp")
        all_images = all(
            path.lower().endswith(image_extensions) for path in all_media_paths
        )

        if all_images:
            success = await images_to_video(
                all_media_paths, output_path, duration_per_image=1.0, fps=fps
            )
        else:
            video_paths = [
                p for p in all_media_paths if not p.lower().endswith(image_extensions)
            ]
            if video_paths:
                success = await merge_videos(video_paths, output_path)
            else:
                success = await images_to_video(
                    all_media_paths, output_path, duration_per_image=1.0, fps=fps
                )

        if not success:
            raise RuntimeError("Failed to create video from timeline items.")

    async def _export_grouped(
        self, timeline_items, items_per_video: int, output_dir: str, fps: int
    ) -> None:
        from utils.ffmpeg_utils import images_to_video, merge_videos

        groups = [
            timeline_items[i : i + items_per_video]
            for i in range(0, len(timeline_items), items_per_video)
        ]
        total_groups = len(groups)

        for idx, group in enumerate(groups):
            self.check_cancelled()
            group_media_paths: List[str] = []
            for item in group:
                video_path = item.get_video_path()
                image_path = item.get_image_path()

                if video_path and os.path.exists(video_path):
                    group_media_paths.append(video_path)
                elif image_path and os.path.exists(image_path):
                    group_media_paths.append(image_path)

            if not group_media_paths:
                continue

            base_output_path = os.path.join(
                output_dir, f"timeline_group_{idx + 1:03d}.mp4"
            )
            output_path = self._get_unique_filename(base_output_path)

            image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp")
            all_images = all(
                path.lower().endswith(image_extensions) for path in group_media_paths
            )

            if all_images:
                success = await images_to_video(
                    group_media_paths,
                    output_path,
                    duration_per_image=1.0,
                    fps=fps,
                )
            else:
                video_paths = [
                    p
                    for p in group_media_paths
                    if not p.lower().endswith(image_extensions)
                ]
                if video_paths:
                    success = await merge_videos(video_paths, output_path)
                else:
                    success = await images_to_video(
                        group_media_paths,
                        output_path,
                        duration_per_image=1.0,
                        fps=fps,
                    )

            if not success:
                raise RuntimeError(f"Failed to create video for group {idx + 1}")

            progress = int((idx + 1) / total_groups * 100)
            self.report_progress(progress)

    async def _export_individual(self, timeline_items, output_dir: str, fps: int) -> None:
        from utils.ffmpeg_utils import images_to_video, merge_videos

        total_items = len(timeline_items)

        for idx, item in enumerate(timeline_items):
            self.check_cancelled()
            video_path = item.get_video_path()
            image_path = item.get_image_path()

            if video_path and os.path.exists(video_path):
                media_path = video_path
            elif image_path and os.path.exists(image_path):
                media_path = image_path
            else:
                continue

            if media_path.lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".bmp")
            ):
                base_output_path = os.path.join(
                    output_dir, f"item_{item.get_timeline_index():03d}.mp4"
                )
                output_path = self._get_unique_filename(base_output_path)
                success = await images_to_video(
                    [media_path], output_path, duration_per_image=2.0, fps=fps
                )
            else:
                base_output_path = os.path.join(
                    output_dir, f"item_{item.get_timeline_index():03d}_video.mp4"
                )
                output_path = self._get_unique_filename(base_output_path)
                success = await merge_videos([media_path], output_path, codec="copy")

            if not success:
                raise RuntimeError(f"Failed to process item {idx + 1}")

            progress = int((idx + 1) / total_items * 100)
            self.report_progress(progress)
