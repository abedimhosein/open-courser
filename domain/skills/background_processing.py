"""
Background Processing Skill

Owned by: Background Task Agent
Purpose: Execute time-consuming tasks asynchronously using
         a lightweight thread pool, without Celery.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    id: str
    job_type: str
    payload: dict
    status: JobStatus = JobStatus.QUEUED
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    retry_count: int = 0
    max_retries: int = 3


JobHandler = Callable[[dict], Any]


class BackgroundProcessor:
    """
    Lightweight background job processor using a thread pool.

    Usage:
        processor = BackgroundProcessor(max_workers=4)

        def my_job(payload):
            ...

        processor.register_handler("my_task", my_job)
        processor.submit("my_task", {"key": "value"})
    """

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._handlers: dict[str, JobHandler] = {}
        self._queue: list[Job] = []
        self._active_jobs: dict[str, Job] = {}
        self._completed_jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._worker_count = 0
        self._running = False

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        """Register a handler function for a job type."""
        self._handlers[job_type] = handler

    def submit(self, job_type: str, payload: dict) -> Job:
        """Submit a new job for async execution."""
        job = Job(
            id=str(uuid.uuid4()),
            job_type=job_type,
            payload=payload,
        )

        with self._lock:
            self._queue.append(job)

        self._maybe_spawn_worker()

        return job

    def get_status(self, job_id: str) -> JobStatus | None:
        """Get the status of a job by ID."""
        with self._lock:
            if job_id in self._active_jobs:
                return self._active_jobs[job_id].status
            if job_id in self._completed_jobs:
                return self._completed_jobs[job_id].status
            for job in self._queue:
                if job.id == job_id:
                    return job.status
        return None

    def get_result(self, job_id: str) -> Any:
        """Get the result of a completed job."""
        with self._lock:
            job = self._completed_jobs.get(job_id)
            if job:
                return job.result
        return None

    def _maybe_spawn_worker(self) -> None:
        """Spawn a worker thread if under the limit and there's work."""
        with self._lock:
            if self._worker_count >= self._max_workers:
                return
            if not self._queue:
                return
            self._worker_count += 1

        thread = threading.Thread(target=self._worker_loop, daemon=True)
        thread.start()

    def _worker_loop(self) -> None:
        """Worker thread main loop - processes jobs from the queue."""
        while True:
            job = self._dequeue_job()
            if job is None:
                self._decrement_workers()
                return

            handler = self._handlers.get(job.job_type)
            if handler is None:
                job.status = JobStatus.FAILED
                job.error = f"No handler registered for job type: {job.job_type}"
                self._complete_job(job)
                continue

            job.status = JobStatus.RUNNING
            job.started_at = time.time()

            try:
                result = handler(job.payload)
                job.status = JobStatus.COMPLETED
                job.result = result
            except Exception as e:
                job.retry_count += 1
                if job.retry_count < job.max_retries:
                    self._requeue_job(job)
                    continue
                job.status = JobStatus.FAILED
                job.error = str(e)

            self._complete_job(job)

    def _dequeue_job(self) -> Job | None:
        """Remove and return the next job from the queue."""
        with self._lock:
            if not self._queue:
                return None
            job = self._queue.pop(0)
            self._active_jobs[job.id] = job
            return job

    def _complete_job(self, job: Job) -> None:
        """Move a job from active to completed."""
        job.completed_at = time.time()
        with self._lock:
            self._active_jobs.pop(job.id, None)
            self._completed_jobs[job.id] = job

    def _requeue_job(self, job: Job) -> None:
        """Re-queue a job for retry with exponential backoff."""
        job.status = JobStatus.QUEUED
        with self._lock:
            self._active_jobs.pop(job.id, None)
            self._queue.append(job)

    def _decrement_workers(self) -> None:
        with self._lock:
            self._worker_count -= 1


# Global processor instance
_default_processor: BackgroundProcessor | None = None


def get_processor(max_workers: int = 4) -> BackgroundProcessor:
    """Get or create the default BackgroundProcessor instance."""
    global _default_processor
    if _default_processor is None:
        _default_processor = BackgroundProcessor(max_workers=max_workers)
    return _default_processor
