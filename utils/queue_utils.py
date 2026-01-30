# async_queue.py
import asyncio
import threading
import queue
import traceback
from asyncio import Queue, Task
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Optional, Union, Awaitable
import logging
import time

logger = logging.getLogger(__name__)

class AsyncQueueManager:
    """
    基于 qasync 的非等待式异步消费队列管理器
    专为 PySide/PyQt 设计，支持 GUI 主线程中安全运行 asyncio
    """

    def __init__(
        self,
        processor: Callable[[Any], None],
        maxsize: int = 100,
        max_concurrent: int = 1,
        name: str = "AsyncConsumer"
    ):
        """
        :param processor: 异步处理函数，签名: async def func(item) -> None
        :param maxsize: 队列最大容量
        :param max_concurrent: 最大并发数（1为串行处理，>1为并发处理）
        :param name: 消费者名称（用于日志）
        """
        if not asyncio.iscoroutinefunction(processor):
            raise TypeError("processor 必须是一个 async def 函数")

        self.processor = processor
        self.queue = Queue(maxsize=maxsize)
        self.max_concurrent = max_concurrent
        self.name = name
        self._task: Optional[Task] = None
        self._running = False

    def put(self, item: Any):
        """
        非等待式提交任务（线程安全，可在任意线程调用）
        立即返回，不阻塞生产者
        """
        if not self._running:
            raise RuntimeError(f"{self.name} 尚未启动，请先调用 start()")

        # 使用 asyncio.run_coroutine_threadsafe 确保线程安全
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._put_safe(item),
                asyncio.get_event_loop()
            )
            # 不 await，立即返回
        except Exception as e:
            logger.error(f"❌ 提交任务失败 {item}: {e}")

    async def _put_safe(self, item: Any):
        """安全入队（避免 QueueFull）"""
        if self.queue.full():
            logger.warning(f"⚠️ {self.name} 队列已满，丢弃任务: {item}")
            return
        self.queue.put_nowait(item)

    async def start(self):
        """启动消费者（必须在事件循环中调用）"""
        if self._running:
            logger.info(f"⚠️ {self.name} 已经在运行中")
            return
        logger.info(f"🔄 {self.name} 开始启动...")
        self._running = True
        self._task = asyncio.create_task(self._run())  # Python 3.7 compatibility - no name parameter
        logger.info(f"✅ {self.name} 已启动 | 容量: {self.queue.maxsize} | 最大并发数: {self.max_concurrent}")
        # Give a tiny bit of time for the task to actually start
        await asyncio.sleep(0.01)

    async def stop(self):
        """停止消费者，等待当前任务完成"""
        if not self._running:
            return
        # Set running to False to signal the worker to stop accepting new items
        self._running = False
        
        # Wait for the main task to complete naturally or handle cancellation properly
        if self._task:
            try:
                # Wait for the main task to finish processing (it should exit the loop when self._running is False)
                await self._task
            except asyncio.CancelledError:
                # The task was cancelled, which is fine
                pass
        logger.info(f"🛑 {self.name} 已停止")

    async def join(self):
        """等待所有任务处理完成"""
        await self.queue.join()

    async def _run(self):
        """后台消费循环"""
        try:
            logger.info(f"🟢 {self.name} 循环开始 | 最大并发数: {self.max_concurrent}")
            
            # 如果并发数为1，使用串行处理
            if self.max_concurrent <= 1:
                logger.info(f"🔵 {self.name} 使用串行处理模式")
                while True:  # 不仅检查 self._running，还要处理队列中剩余的任务
                    try:
                        # 当 running 为 False 且队列为空时，退出循环
                        if not self._running and self.queue.empty():
                            logger.info(f"🟡 {self.name} 退出条件: _running=False 且队列为空")
                            break
                        item = await self.queue.get()
                        logger.info(f"📦 {self.name} 获取到项目: {item}")
                        try:
                            await self.processor(item)
                            logger.info(f"✅ {self.name} 处理完成: {item}")
                        except Exception as e:
                            logger.error(f"❌ {self.name} 处理失败 {item}: {e}", exc_info=True)
                        finally:
                            self.queue.task_done()
                            logger.info(f"✅ {self.name} task_done 调用: {item}")
                    except asyncio.CancelledError:
                        logger.info(f"🛑 {self.name} 被取消")
                        break
                    except Exception as e:
                        logger.error(f"❌ {self.name} 发生未预期错误: {e}", exc_info=True)
            else:
                # 并发处理模式
                logger.info(f"🔵 {self.name} 使用并发处理模式 | 并发数: {self.max_concurrent}")
                
                # 创建信号量来限制并发数
                semaphore = asyncio.Semaphore(self.max_concurrent)
                
                async def process_with_semaphore(item):
                    async with semaphore:
                        try:
                            logger.info(f"📦 {self.name} 开始处理: {item}")
                            await self.processor(item)
                            logger.info(f"✅ {self.name} 处理完成: {item}")
                        except Exception as e:
                            logger.error(f"❌ {self.name} 处理失败 {item}: {e}", exc_info=True)
                        finally:
                            self.queue.task_done()
                            logger.info(f"✅ {self.name} task_done 调用: {item}")
                
                # 持续从队列获取任务并提交到并发池
                # 先处理运行时的项目，然后处理停止后的剩余项目
                # Continue until both conditions are met: 
                # 1. We've been asked to stop (self._running is False)
                # 2. Queue is empty
                while not (not self._running and self.queue.empty()):
                    try:
                        # Try to get an item from the queue
                        # Use timeout to periodically check if we should stop
                        try:
                            item = await asyncio.wait_for(self.queue.get(), timeout=0.5)
                            logger.info(f"📦 {self.name} 获取到项目: {item}")
                            # Create a task to process the item concurrently
                            asyncio.create_task(process_with_semaphore(item))
                        except asyncio.TimeoutError:
                            # Timeout occurred, check the stop condition again
                            continue
                    except asyncio.CancelledError:
                        logger.info(f"🛑 {self.name} 被取消")
                        break
                    except Exception as e:
                        logger.error(f"❌ {self.name} 发生未预期错误: {e}", exc_info=True)
                
                # At this point, either we've been asked to stop and queue is empty,
                # or the task was cancelled. Wait for any remaining queue operations to complete.
                logger.info(f"⏳ {self.name} 等待队列中所有任务完成")
                await self.queue.join()
                logger.info(f"✅ {self.name} 队列中所有任务已完成")
            
            logger.info(f"👋 {self.name} 循环退出")
        except Exception as e:
            logger.error(f"❌ {self.name} _run方法发生未预期的顶级错误: {e}", exc_info=True)
            raise


class SyncQueueManager:
    """
    阻塞式同步消费队列管理器
    支持阻塞式消费任务，同时兼容异步任务执行方法
    """
    
    def __init__(
        self,
        processor: Union[Callable[[Any], Any], Callable[[Any], Awaitable]],
        maxsize: int = 100,
        max_concurrent: int = 1,
        name: str = "SyncConsumer",
        thread_pool_size: int = 4
    ):
        """
        :param processor: 处理函数，可以是同步或异步函数
        :param maxsize: 队列最大容量
        :param max_concurrent: 最大并发数（1为串行处理，>1为并发处理）
        :param name: 消费者名称（用于日志）
        :param thread_pool_size: 线程池大小，用于运行异步事件循环
        """
        self.processor = processor
        self.queue = queue.Queue(maxsize=maxsize)
        self.max_concurrent = max_concurrent
        self.name = name
        self.thread_pool_size = thread_pool_size
        
        self._running = False
        self._worker_threads = []
        self._executor = ThreadPoolExecutor(max_workers=thread_pool_size)
        self._loop = None
        self._loop_thread = None

    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None):
        """
        提交任务到队列
        
        :param item: 要处理的项目
        :param block: 是否阻塞等待（当队列满时）
        :param timeout: 超时时间
        """
        if not self._running:
            raise RuntimeError(f"{self.name} 尚未启动，请先调用 start()")
        
        self.queue.put(item, block=block, timeout=timeout)
        logger.info(f"📦 {self.name} 任务已提交: {item}")

    def start(self):
        """启动消费者"""
        if self._running:
            logger.info(f"⚠️ {self.name} 已经在运行中")
            return
        
        logger.info(f"🔄 {self.name} 开始启动...")
        self._running = True
        
        # Start the asyncio event loop in a separate thread
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_event_loop, args=(self._loop,), daemon=True)
        self._loop_thread.start()
        
        # Wait for the event loop to be ready
        time.sleep(0.01)
        
        # Start worker threads based on concurrency setting
        if self.max_concurrent <= 1:
            # Serial processing: start one worker
            worker = threading.Thread(target=self._serial_worker, daemon=True)
            worker.start()
            self._worker_threads = [worker]
            logger.info(f"✅ {self.name} 已启动 | 模式: 串行 | 容量: {self.queue.maxsize}")
        else:
            # Concurrent processing: start multiple workers
            self._worker_threads = []
            for i in range(min(self.max_concurrent, self.thread_pool_size)):
                worker = threading.Thread(target=self._concurrent_worker, daemon=True)
                worker.start()
                self._worker_threads.append(worker)
            logger.info(f"✅ {self.name} 已启动 | 模式: 并发 | 容量: {self.queue.maxsize} | 并发数: {self.max_concurrent}")

    def stop(self):
        """停止消费者，等待当前任务完成"""
        if not self._running:
            return
        
        logger.info(f"🛑 {self.name} 准备停止...")
        self._running = False
        
        # Wait for all worker threads to finish
        for worker_thread in self._worker_threads:
            worker_thread.join(timeout=5.0)  # Wait up to 5 seconds for each thread
        
        # Shutdown the executor
        self._executor.shutdown(wait=True, timeout=5.0)
        
        # Stop the event loop thread
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._stop_event_loop(), self._loop)
        
        if self._loop_thread:
            self._loop_thread.join(timeout=5.0)
        
        logger.info(f"🛑 {self.name} 已停止")

    def join(self):
        """等待队列中所有任务处理完成"""
        self.queue.join()

    def _run_event_loop(self, loop):
        """在单独的线程中运行 asyncio 事件循环"""
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def _stop_event_loop(self):
        """停止事件循环"""
        # Cancel all running tasks
        tasks = [task for task in asyncio.all_tasks(self._loop) if not task.done()]
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to finish cancellation
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Stop the event loop
        self._loop.call_soon_threadsafe(self._loop.stop)

    def _run_in_event_loop(self, coro):
        """在事件循环中运行协程"""
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result()  # This will block until the coroutine completes
        else:
            # Fallback: run in a new event loop
            return asyncio.run(coro)

    def _serial_worker(self):
        """串行工作线程"""
        logger.info(f"🟢 {self.name} 串行工作线程启动")
        
        while self._running or not self.queue.empty():
            try:
                # Get item from queue with timeout to periodically check if still running
                try:
                    item = self.queue.get(timeout=0.5)
                except queue.Empty:
                    continue  # Check the running condition again
                
                logger.info(f"📦 {self.name} 获取到项目: {item}")
                
                # Process the item
                self._process_item(item)
                
                # Mark task as done
                self.queue.task_done()
                logger.info(f"✅ {self.name} 任务完成: {item}")
                
            except Exception as e:
                logger.error(f"❌ {self.name} 工作线程发生错误: {e}", exc_info=True)

        logger.info(f"👋 {self.name} 串行工作线程退出")

    def _concurrent_worker(self):
        """并发工作线程"""
        logger.info(f"🟢 {self.name} 并发工作线程启动")
        
        while self._running or not self.queue.empty():
            try:
                # Get item from queue with timeout to periodically check if still running
                try:
                    item = self.queue.get(timeout=0.5)
                except queue.Empty:
                    continue  # Check the running condition again
                
                logger.info(f"📦 {self.name} 获取到项目: {item}")
                
                # Process the item
                self._process_item(item)
                
                # Mark task as done
                self.queue.task_done()
                logger.info(f"✅ {self.name} 任务完成: {item}")
                
            except Exception as e:
                logger.error(f"❌ {self.name} 并发工作线程发生错误: {e}", exc_info=True)

        logger.info(f"👋 {self.name} 并发工作线程退出")

    def _process_item(self, item: Any):
        """处理单个项目，兼容同步和异步处理器"""
        try:
            if asyncio.iscoroutinefunction(self.processor):
                # If processor is async, run it in the event loop
                coro = self.processor(item)
                self._run_in_event_loop(coro)
            else:
                # If processor is sync, run it directly
                self.processor(item)
        except Exception as e:
            logger.error(f"❌ {self.name} 处理项目失败 {item}: {e}", exc_info=True)