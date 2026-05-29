from __future__ import annotations

from celery_app import celery_app
from freecad_pipeline import add_loaded_object, load_document
from job_store import DATA_DIR, update_metadata


@celery_app.task(name="freecad.process_job")
def process_job(job_id: str) -> dict[str, str]:
    job_path = DATA_DIR / "jobs" / job_id
    source_file = job_path / "source.FCStd"
    loaded_file = job_path / "loaded.FCStd"
    modified_file = job_path / "modified.FCStd"

    try:
        update_metadata(job_id, status="processing", stage="loading document", error=None)
        load_document(source_file, loaded_file)

        update_metadata(job_id, status="processing", stage="adding loaded object", error=None)
        add_loaded_object(loaded_file, modified_file)

        update_metadata(
            job_id,
            status="completed",
            stage="finished",
            error=None,
            result_file=modified_file.name,
        )
        return {"job_id": job_id, "result_file": modified_file.name}
    except Exception as exc:
        update_metadata(job_id, status="failed", stage="failed", error=str(exc))
        raise
