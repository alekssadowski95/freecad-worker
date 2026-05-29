# freecad-worker

Minimal Flask app that accepts uploaded FreeCAD `.FCStd` files, queues a background Celery job, opens the file in headless FreeCAD, adds an object named `loaded`, saves the modified document, and exposes every generated file on a download page.

## Routes

- `GET /upload` shows the upload form.
- `POST /upload` saves the file and queues the FreeCAD job.
- `GET /files` lists all jobs and downloadable files.
- `GET /files/<job_id>/<filename>` downloads a specific file.

## Run with Docker

```bash
docker compose up --build
```

Open `http://localhost:8000/upload` to submit a `.FCStd` file.

To run multiple Flask apps on the same server, keep the container port fixed at `8000` and set a different host port with `HOST_PORT` before starting Compose. For example:

```bash
HOST_PORT=8001 docker compose up --build
```

## What gets created

Each upload gets its own folder under `data/jobs/<job_id>/` with:

- `source.FCStd`
- `loaded.FCStd`
- `modified.FCStd`
- `job.json`

The download page shows the non-metadata files in a list once they are available.
