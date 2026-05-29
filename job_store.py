from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
JOBS_DIR = DATA_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def metadata_path(job_id: str) -> Path:
    return job_dir(job_id) / "job.json"


def default_metadata(job_id: str, original_filename: str) -> dict[str, Any]:
    timestamp = utc_now()
    return {
        "job_id": job_id,
        "original_filename": original_filename,
        "status": "queued",
        "stage": "queued",
        "created_at": timestamp,
        "updated_at": timestamp,
        "error": None,
    }


def write_metadata(job_id: str, metadata: dict[str, Any]) -> None:
    path = metadata_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def load_metadata(job_id: str) -> dict[str, Any]:
    path = metadata_path(job_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def update_metadata(job_id: str, **updates: Any) -> dict[str, Any]:
    metadata = load_metadata(job_id)
    metadata.update(updates)
    metadata["updated_at"] = utc_now()
    write_metadata(job_id, metadata)
    return metadata


def list_jobs() -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    if not JOBS_DIR.exists():
        return jobs

    for directory in JOBS_DIR.iterdir():
        if not directory.is_dir():
            continue
        metadata_file = directory / "job.json"
        if not metadata_file.exists():
            continue
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        files = sorted(
            file.name
            for file in directory.iterdir()
            if file.is_file() and file.name != "job.json"
        )
        metadata["files"] = files
        jobs.append(metadata)

    jobs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return jobs
