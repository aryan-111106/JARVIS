import uuid
from typing import Any, Dict, Optional

from app.services.task_executor import TaskExecutor


class TaskManager:
    """Lightweight in-memory jobs (e.g. image generation status for clients that poll)."""

    _jobs: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def submit_image_prompt(cls, prompt: str) -> str:
        job_id = str(uuid.uuid4())
        url = TaskExecutor.pollinations_image_url(prompt)
        cls._jobs[job_id] = {
            "status": "completed",
            "prompt": prompt,
            "url": url,
        }
        return job_id

    @classmethod
    def get_job(cls, job_id: str) -> Optional[Dict[str, Any]]:
        return cls._jobs.get(job_id)
