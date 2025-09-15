"""Advanced async patterns with injx dependency injection."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol, runtime_checkable

from injx import Container, Scope, Token


# Data models
@dataclass
class Task:
    id: str
    payload: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    status: str = "pending"


@dataclass
class WorkResult:
    task_id: str
    result: Any
    processing_time: float
    worker_id: str


# Protocols for async services
@runtime_checkable
class TaskQueue(Protocol):
    """Protocol for async task queue."""

    async def enqueue(self, task: Task) -> None: ...
    async def dequeue(self) -> Task | None: ...
    async def get_queue_size(self) -> int: ...


@runtime_checkable
class WorkerPool(Protocol):
    """Protocol for async worker pool."""

    async def submit_task(self, task: Task) -> WorkResult: ...
    async def get_worker_stats(self) -> Dict[str, Any]: ...


@runtime_checkable
class ResultStore(Protocol):
    """Protocol for storing task results."""

    async def store_result(self, result: WorkResult) -> None: ...
    async def get_result(self, task_id: str) -> WorkResult | None: ...
    async def get_all_results(self) -> List[WorkResult]: ...


# Async implementations
class AsyncTaskQueue:
    """In-memory async task queue with proper cleanup."""

    def __init__(self):
        self._queue = asyncio.Queue()
        self._closed = False

    async def enqueue(self, task: Task) -> None:
        if self._closed:
            raise RuntimeError("Queue is closed")
        await self._queue.put(task)

    async def dequeue(self) -> Task | None:
        if self._closed:
            return None

        try:
            # Wait up to 1 second for a task
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    async def get_queue_size(self) -> int:
        return self._queue.qsize()

    async def aclose(self) -> None:
        """Cleanup method."""
        self._closed = True
        # Clear remaining tasks
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break


class AsyncWorkerPool:
    """Async worker pool that processes tasks concurrently."""

    def __init__(self, queue: TaskQueue, num_workers: int = 3):
        self.queue = queue
        self.num_workers = num_workers
        self._workers: List[asyncio.Task] = []
        self._stats = {
            "tasks_processed": 0,
            "total_processing_time": 0.0,
            "active_workers": 0,
        }
        self._running = False
        self._results: Dict[str, WorkResult] = {}

    async def start_workers(self) -> None:
        """Start worker tasks."""
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(f"worker-{i}"))
            for i in range(self.num_workers)
        ]

    async def _worker_loop(self, worker_id: str) -> None:
        """Main worker loop."""
        while self._running:
            task = await self.queue.dequeue()
            if task is None:
                continue

            self._stats["active_workers"] += 1

            try:
                start_time = time.time()

                # Simulate work (CPU-bound or I/O-bound)
                if task.payload.get("type") == "cpu_bound":
                    result = await self._cpu_bound_work(task.payload)
                elif task.payload.get("type") == "io_bound":
                    result = await self._io_bound_work(task.payload)
                else:
                    result = await self._default_work(task.payload)

                processing_time = time.time() - start_time

                work_result = WorkResult(
                    task_id=task.id,
                    result=result,
                    processing_time=processing_time,
                    worker_id=worker_id,
                )

                self._results[task.id] = work_result
                self._stats["tasks_processed"] += 1
                self._stats["total_processing_time"] += processing_time

                print(
                    f"[{worker_id}] Completed task {task.id} in {processing_time:.3f}s"
                )

            except Exception as e:
                print(f"[{worker_id}] Error processing task {task.id}: {e}")
            finally:
                self._stats["active_workers"] -= 1

    async def _cpu_bound_work(self, payload: Dict[str, Any]) -> str:
        """Simulate CPU-bound work using thread pool."""

        def cpu_work():
            # Simulate computation
            total = sum(i**2 for i in range(payload.get("iterations", 1000)))
            return f"CPU result: {total}"

        # Use thread pool for CPU-bound work
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, cpu_work)
            return result

    async def _io_bound_work(self, payload: Dict[str, Any]) -> str:
        """Simulate I/O-bound work."""
        delay = payload.get("delay", 0.5)
        await asyncio.sleep(delay)
        return f"I/O result after {delay}s"

    async def _default_work(self, payload: Dict[str, Any]) -> str:
        """Default work simulation."""
        await asyncio.sleep(0.1)
        return f"Processed: {payload}"

    async def submit_task(self, task: Task) -> WorkResult:
        """Submit a task and wait for result."""
        await self.queue.enqueue(task)

        # Wait for result (with timeout)
        for _ in range(100):  # 10 second timeout
            if task.id in self._results:
                return self._results[task.id]
            await asyncio.sleep(0.1)

        raise TimeoutError(f"Task {task.id} did not complete within timeout")

    async def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker pool statistics."""
        queue_size = await self.queue.get_queue_size()
        avg_processing_time = (
            self._stats["total_processing_time"] / self._stats["tasks_processed"]
            if self._stats["tasks_processed"] > 0
            else 0.0
        )

        return {
            **self._stats,
            "queue_size": queue_size,
            "avg_processing_time": avg_processing_time,
            "results_count": len(self._results),
        }

    async def aclose(self) -> None:
        """Cleanup worker pool."""
        self._running = False

        # Cancel all worker tasks
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()
        print("Worker pool shut down")


class AsyncResultStore:
    """In-memory result store with async operations."""

    def __init__(self):
        self._results: Dict[str, WorkResult] = {}
        self._lock = asyncio.Lock()

    async def store_result(self, result: WorkResult) -> None:
        async with self._lock:
            self._results[result.task_id] = result

    async def get_result(self, task_id: str) -> WorkResult | None:
        async with self._lock:
            return self._results.get(task_id)

    async def get_all_results(self) -> List[WorkResult]:
        async with self._lock:
            return list(self._results.values())


# High-level service orchestrator
class TaskProcessingService:
    """Service that orchestrates async task processing."""

    def __init__(self, worker_pool: WorkerPool, result_store: ResultStore):
        self.worker_pool = worker_pool
        self.result_store = result_store

    async def process_task(self, task: Task) -> WorkResult:
        """Process a single task."""
        print(f"Processing task {task.id}")

        # Submit to worker pool
        result = await self.worker_pool.submit_task(task)

        # Store result
        await self.result_store.store_result(result)

        return result

    async def process_batch(self, tasks: List[Task]) -> List[WorkResult]:
        """Process multiple tasks concurrently."""
        print(f"Processing batch of {len(tasks)} tasks")

        # Process tasks concurrently
        results = await asyncio.gather(
            *[self.process_task(task) for task in tasks], return_exceptions=True
        )

        # Filter out exceptions
        successful_results = [r for r in results if isinstance(r, WorkResult)]

        print(f"Batch completed: {len(successful_results)}/{len(tasks)} successful")
        return successful_results

    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        worker_stats = await self.worker_pool.get_worker_stats()
        all_results = await self.result_store.get_all_results()

        return {
            "worker_stats": worker_stats,
            "total_results": len(all_results),
            "results_by_worker": {
                worker_id: len([r for r in all_results if r.worker_id == worker_id])
                for worker_id in set(r.worker_id for r in all_results)
            },
        }


async def setup_async_services() -> Container:
    """Setup async services with dependency injection."""
    container = Container()

    # Define tokens
    queue_token = Token[TaskQueue]("task_queue", protocol=TaskQueue)
    worker_pool_token = Token[WorkerPool]("worker_pool", protocol=WorkerPool)
    result_store_token = Token[ResultStore]("result_store", protocol=ResultStore)
    processing_service_token = Token[TaskProcessingService](
        "processing_service", expected_type=TaskProcessingService
    )

    # Register implementations
    container.register(queue_token, AsyncTaskQueue, Scope.SINGLETON)
    container.register(result_store_token, AsyncResultStore, Scope.SINGLETON)

    # Register worker pool with dependency
    def create_worker_pool() -> AsyncWorkerPool:
        queue = container.resolve_protocol(TaskQueue)
        return AsyncWorkerPool(queue, num_workers=4)

    container.register(worker_pool_token, create_worker_pool, Scope.SINGLETON)

    # Register processing service with dependencies
    def create_processing_service() -> TaskProcessingService:
        worker_pool = container.resolve_protocol(WorkerPool)
        result_store = container.resolve_protocol(ResultStore)
        return TaskProcessingService(worker_pool, result_store)

    container.register(
        processing_service_token, create_processing_service, Scope.SINGLETON
    )

    return container


async def demo_async_patterns():
    """Demonstrate advanced async patterns with dependency injection."""
    print("=== Async Service Patterns Demo ===\n")

    # Setup container with async services
    container = await setup_async_services()

    # Get services
    processing_service_token = Token[TaskProcessingService](
        "processing_service", expected_type=TaskProcessingService
    )
    processing_service = container.get(processing_service_token)

    # Start worker pool
    worker_pool = container.resolve_protocol(WorkerPool)
    if hasattr(worker_pool, "start_workers"):
        await worker_pool.start_workers()

    print("1. Processing individual tasks:")

    # Create various types of tasks
    tasks = [
        Task("task-1", {"type": "cpu_bound", "iterations": 5000}),
        Task("task-2", {"type": "io_bound", "delay": 0.3}),
        Task("task-3", {"type": "default", "data": "some data"}),
        Task("task-4", {"type": "cpu_bound", "iterations": 3000}),
    ]

    # Process tasks individually
    for task in tasks:
        result = await processing_service.process_task(task)
        print(
            f"  {task.id}: {result.result} ({result.processing_time:.3f}s by {result.worker_id})"
        )

    print("\n2. Processing batch of tasks:")

    # Create batch of tasks
    batch_tasks = [
        Task(f"batch-{i}", {"type": "io_bound", "delay": 0.2}) for i in range(8)
    ]

    start_time = time.time()
    batch_results = await processing_service.process_batch(batch_tasks)
    batch_time = time.time() - start_time

    print(f"  Processed {len(batch_results)} tasks in {batch_time:.3f}s")
    print(
        f"  Average task time: {sum(r.processing_time for r in batch_results) / len(batch_results):.3f}s"
    )

    print("\n3. Processing statistics:")
    stats = await processing_service.get_processing_stats()
    print(f"  Total tasks processed: {stats['worker_stats']['tasks_processed']}")
    print(
        f"  Average processing time: {stats['worker_stats']['avg_processing_time']:.3f}s"
    )
    print(f"  Results by worker: {stats['results_by_worker']}")
    print(f"  Queue size: {stats['worker_stats']['queue_size']}")

    print("\n4. Stress test with concurrent batches:")

    # Create multiple batches to process concurrently
    stress_batches = [
        [
            Task(f"stress-{batch}-{i}", {"type": "default", "batch": batch})
            for i in range(3)
        ]
        for batch in range(5)
    ]

    stress_start = time.time()
    stress_results = await asyncio.gather(
        *[processing_service.process_batch(batch) for batch in stress_batches],
        return_exceptions=True,
    )
    stress_time = time.time() - stress_start

    total_stress_tasks = sum(len(batch) for batch in stress_batches)
    successful_stress = sum(
        len(results) for results in stress_results if isinstance(results, list)
    )

    print(
        f"  Stress test: {successful_stress}/{total_stress_tasks} tasks in {stress_time:.3f}s"
    )

    print("\n5. Final statistics:")
    final_stats = await processing_service.get_processing_stats()
    print(f"  Total processed: {final_stats['worker_stats']['tasks_processed']}")
    print(f"  Total results stored: {final_stats['total_results']}")

    print("\n6. Cleanup:")
    await container.dispose()
    print("  All async resources cleaned up")


if __name__ == "__main__":
    asyncio.run(demo_async_patterns())
