"""Tests for the Background Processing skill."""

import time

from domain.skills.background_processing import BackgroundProcessor, JobStatus


class TestBackgroundProcessor:
    def test_submit_and_complete_job(self):
        processor = BackgroundProcessor(max_workers=2)

        def handler(payload: dict) -> str:
            return f"processed_{payload['key']}"

        processor.register_handler("test", handler)
        job = processor.submit("test", {"key": "value"})

        time.sleep(0.2)

        assert processor.get_status(job.id) == JobStatus.COMPLETED
        assert processor.get_result(job.id) == "processed_value"

    def test_job_failure_retries(self):
        processor = BackgroundProcessor(max_workers=1)
        attempt_count = 0

        def failing_handler(payload: dict) -> str:
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError(f"Attempt {attempt_count} failed")

        processor.register_handler("failing", failing_handler)
        job = processor.submit("failing", {})

        time.sleep(0.5)

        assert processor.get_status(job.id) == JobStatus.FAILED
        assert job.retry_count == job.max_retries

    def test_unregistered_job_type(self):
        processor = BackgroundProcessor(max_workers=1)
        job = processor.submit("unknown", {})

        time.sleep(0.2)

        assert processor.get_status(job.id) == JobStatus.FAILED
        assert job.error is not None
