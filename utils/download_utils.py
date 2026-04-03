# async_downloader.py
import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QProgressBar, QTextEdit, QFileDialog
)

import aiohttp


# ----------------------------- 1. 自定义信号类 -----------------------------
class DownloadWorkerSignals(QObject):
    started = Signal(str)           # 开始下载 url
    progress = Signal(str, int, int)  # url, downloaded, total
    finished = Signal(str, str)     # url, filepath
    error = Signal(str, str)        # url, message
    cancelled = Signal(str)         # url


# ----------------------------- 2. 下载任务处理器 -----------------------------
class DownloadWorker(QThread):
    """
    在独立线程中运行 asyncio 事件循环
    因为 asyncio 和 Qt 主循环不能直接共存
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = DownloadWorkerSignals()
        self._running_tasks = {}
        self.loop = None
        self._wire_event_bus()

    def _wire_event_bus(self) -> None:
        """Mirror download lifecycle to :class:`app.core.event_bus.EventBus` (Qt thread–safe)."""
        if getattr(self, "_bus_wired", False):
            return
        self._bus_wired = True
        try:
            from app.core.event_bus import EventBus
        except Exception:
            return
        bus = EventBus.instance()

        def task_id(url: str) -> str:
            return f"download:{url}"

        self.signals.started.connect(
            lambda url: bus.emit_task_started(task_id(url), "download_aiohttp")
        )
        self.signals.progress.connect(
            lambda url, downloaded, total: bus.emit_task_progress(
                task_id(url),
                int(min(100, downloaded * 100 // total)) if total and total > 0 else 0,
                f"{downloaded}/{total}" if total else str(downloaded),
            )
        )
        self.signals.finished.connect(
            lambda url, filepath: bus.emit_task_finished(task_id(url), filepath)
        )
        self.signals.error.connect(
            lambda url, msg: bus.emit_task_error(task_id(url), msg, None)
        )
        self.signals.cancelled.connect(
            lambda url: bus.emit_task_cancelled(task_id(url))
        )

    def run(self):
        """在子线程中启动 asyncio 事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self):
        """优雅关闭事件循环"""
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait()

    async def _download_file(self, url: str, filepath: str):
        """实际下载逻辑"""
        try:
            self.signals.started.emit(url)

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        msg = f"HTTP {response.status}"
                        self.signals.error.emit(url, msg)
                        return

                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            if url not in self._running_tasks:
                                return  # 被取消
                            f.write(chunk)
                            chunk_len = len(chunk)
                            downloaded += chunk_len
                            self.signals.progress.emit(url, downloaded, total_size)

                    # 下载完成
                    self.signals.finished.emit(url, filepath)

        except Exception as e:
            if url in self._running_tasks:
                self.signals.error.emit(url, str(e))

    def start_download(self, url: str, save_path: str = None):
        """启动下载任务"""
        if not save_path:
            filename = os.path.basename(urlparse(url).path)
            if not filename or filename.endswith("/"):
                filename = f"download_{hash(url) % 10000}.bin"
            save_path = os.path.join(str(Path.home() / "Downloads"), filename)

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # 标记任务正在运行
        self._running_tasks[url] = save_path

        # 提交到事件循环
        asyncio.run_coroutine_threadsafe(
            self._download_file(url, save_path),
            self.loop
        )

    def cancel_download(self, url: str):
        """取消下载"""
        if url in self._running_tasks:
            del self._running_tasks[url]
            self.signals.cancelled.emit(url)


# ----------------------------- 3. 文件处理事件系统 -----------------------------
class FileEventHandler:
    """
    文件处理事件处理器基类
    用户可继承并实现 on_file_downloaded
    """
    async def on_file_downloaded(self, filepath: str):
        """
        当文件下载完成后调用
        可执行：解压、导入、解析、上传等异步操作
        """
        print(f"默认处理器：文件已下载 -> {filepath}")
        # 示例：模拟后续处理
        await asyncio.sleep(1)
        print(f"处理完成: {filepath}")


# ----------------------------- 4. 主窗口 -----------------------------
class DownloaderWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("异步下载器")
        self.resize(600, 400)

        self.layout = QVBoxLayout()

        self.url_label = QLabel("下载URL:")
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("每行一个URL")

        self.save_btn = QPushButton("选择保存位置（可选）")
        self.save_path = None
        self.save_btn.clicked.connect(self.select_save_path)

        self.download_btn = QPushButton("开始下载")
        self.download_btn.clicked.connect(self.start_download)

        self.progress_label = QLabel("等待下载...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)

        # 添加组件
        self.layout.addWidget(self.url_label)
        self.layout.addWidget(self.url_input)
        self.layout.addWidget(self.save_btn)
        self.layout.addWidget(self.download_btn)
        self.layout.addWidget(self.progress_label)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.log_area)

        self.setLayout(self.layout)

        # 创建下载工作线程
        self.worker = DownloadWorker()
        self.worker.start()  # 启动子线程事件循环

        # 连接信号
        self.worker.signals.started.connect(self.on_started)
        self.worker.signals.progress.connect(self.on_progress)
        self.worker.signals.finished.connect(self.on_finished)
        self.worker.signals.error.connect(self.on_error)
        self.worker.signals.cancelled.connect(self.on_cancelled)

        # 当前下载的 URL
        self.current_url = None

    def select_save_path(self):
        path, _ = QFileDialog.getSaveFileName(self, "选择保存路径")
        if path:
            self.save_path = path
            self.save_btn.setText(f"保存到: {os.path.basename(path)}")

    def start_download(self):
        urls = self.url_input.toPlainText().strip().splitlines()
        urls = [url.strip() for url in urls if url.strip()]
        if not urls:
            self.log("请至少输入一个有效的URL")
            return

        self.current_url = urls[0]  # 简化：只处理第一个
        self.download_btn.setEnabled(False)
        self.log(f"开始下载: {self.current_url}")

        # 可自定义处理器
        self.file_handler = FileEventHandler()

        self.worker.start_download(self.current_url, self.save_path)

    def log(self, msg: str):
        self.log_area.append(msg)

    def on_started(self, url: str):
        self.log(f"🚀 开始下载: {url}")

    def on_progress(self, url: str, downloaded: int, total: int):
        if url == self.current_url:
            if total > 0:
                percent = (downloaded / total) * 100
                self.progress_bar.setMaximum(100)
                self.progress_bar.setValue(int(percent))
                self.progress_label.setText(f"下载中... {downloaded}/{total} ({percent:.1f}%)")
            else:
                self.progress_label.setText(f"下载中... {downloaded} bytes")

    def on_finished(self, url: str, filepath: str):
        if url == self.current_url:
            self.log(f"✅ 下载完成: {filepath}")
            self.progress_bar.setValue(100)
            self.progress_label.setText("下载完成，正在处理文件...")

            # 异步处理文件（不阻塞UI）
            asyncio.run_coroutine_threadsafe(
                self.handle_downloaded_file(filepath),
                self.worker.loop
            )

    async def handle_downloaded_file(self, filepath: str):
        """异步处理下载后的文件"""
        try:
            await self.file_handler.on_file_downloaded(filepath)
            self.worker.loop.call_soon_threadsafe(
                lambda: self.log(f"📁 文件处理完成: {filepath}")
            )
        except Exception as e:
            self.worker.loop.call_soon_threadsafe(
                lambda: self.log(f"❌ 处理失败: {e}")
            )
        finally:
            self.worker.loop.call_soon_threadsafe(self.reset_ui)

    def on_error(self, url: str, msg: str):
        if url == self.current_url:
            self.log(f"❌ 下载失败 {url}: {msg}")
            self.reset_ui()

    def on_cancelled(self, url: str):
        if url == self.current_url:
            self.log(f"⏹️ 下载取消: {url}")
            self.reset_ui()

    def reset_ui(self):
        self.download_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("等待下载...")

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.worker.stop()
        event.accept()


# Global download worker instance to ensure proper cleanup
_global_download_worker = None


def get_download_worker():
    """Get or create the global download worker instance."""
    global _global_download_worker
    if _global_download_worker is None:
        _global_download_worker = DownloadWorker()
        _global_download_worker.start()  # Start the worker thread
    return _global_download_worker


def shutdown_download_worker():
    """Shutdown the global download worker."""
    global _global_download_worker
    if _global_download_worker is not None:
        _global_download_worker.stop()
        _global_download_worker = None


# ----------------------------- 5. 使用示例 -----------------------------
if __name__ == "__main__":
    app = QApplication([])
    window = DownloaderWindow()
    window.show()

    # 可选：预填测试URL
    test_urls = [
        "https://httpbin.org/bytes/1024",
        # "https://your-server.com/largefile.zip"
    ]
    window.url_input.setText("\n".join(test_urls))

    app.exec()