from __future__ import annotations

import uuid
from pathlib import Path

from flask import Flask, abort, redirect, render_template_string, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from job_store import default_metadata, job_dir, list_jobs, write_metadata


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 200

UPLOAD_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>FreeCAD Worker</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f6f1ea;
        --panel: #ffffff;
        --text: #1f2933;
        --muted: #61707d;
        --accent: #1756a9;
        --border: #d9e2ec;
      }
      body {
        margin: 0;
        font-family: Arial, Helvetica, sans-serif;
        background: linear-gradient(180deg, #f6f1ea 0%, #eef4fb 100%);
        color: var(--text);
      }
      .wrap {
        max-width: 860px;
        margin: 0 auto;
        padding: 40px 20px 60px;
      }
      .card {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
        padding: 24px;
      }
      h1 { margin-top: 0; }
      p { color: var(--muted); line-height: 1.5; }
      form {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
        margin-top: 20px;
      }
      input[type="file"] {
        padding: 10px;
        border: 1px solid var(--border);
        border-radius: 10px;
        background: #fff;
      }
      button, .button {
        display: inline-block;
        border: 0;
        border-radius: 10px;
        padding: 11px 16px;
        background: var(--accent);
        color: white;
        text-decoration: none;
        font-weight: 700;
        cursor: pointer;
      }
      .hint {
        margin-top: 16px;
        font-size: 0.95rem;
      }
      .notice {
        margin-top: 16px;
        padding: 12px 14px;
        border-radius: 12px;
        background: #eef6ff;
        color: #103d74;
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>Upload a FreeCAD file</h1>
        <p>The worker loads the uploaded <code>.FCStd</code> file in headless FreeCAD, adds a new object named <code>loaded</code>, saves the modified file, and exposes everything on the results page.</p>
        <form method="post" enctype="multipart/form-data">
          <input type="file" name="file" accept=".FCStd,.fcstd" required>
          <button type="submit">Upload and queue</button>
        </form>
        <p class="hint"><a class="button" href="{{ url_for('files_view') }}">Go to downloads</a></p>
        {% if uploaded_job_id %}
          <div class="notice">Queued job <code>{{ uploaded_job_id }}</code>. It will appear on the downloads page as soon as the worker finishes.</div>
        {% endif %}
      </div>
    </div>
  </body>
</html>
"""

FILES_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>FreeCAD Outputs</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f6f1ea;
        --panel: #ffffff;
        --text: #1f2933;
        --muted: #61707d;
        --accent: #1756a9;
        --border: #d9e2ec;
        --good: #0b6b3a;
        --bad: #9b1c1c;
      }
      body {
        margin: 0;
        font-family: Arial, Helvetica, sans-serif;
        background: linear-gradient(180deg, #f6f1ea 0%, #eef4fb 100%);
        color: var(--text);
      }
      .wrap {
        max-width: 1100px;
        margin: 0 auto;
        padding: 40px 20px 60px;
      }
      .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 18px;
      }
      .button {
        display: inline-block;
        border-radius: 10px;
        padding: 11px 16px;
        background: var(--accent);
        color: white;
        text-decoration: none;
        font-weight: 700;
      }
      .card {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 18px;
        box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
        padding: 24px;
        margin-bottom: 18px;
      }
      h1, h2 { margin-top: 0; }
      p { color: var(--muted); line-height: 1.5; }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      th, td {
        text-align: left;
        vertical-align: top;
        padding: 12px 10px;
        border-top: 1px solid var(--border);
      }
      th { color: var(--muted); font-size: 0.9rem; }
      code {
        background: #eef3f8;
        padding: 2px 6px;
        border-radius: 6px;
      }
      ul { margin: 0; padding-left: 18px; }
      li { margin: 4px 0; }
      .status-completed { color: var(--good); font-weight: 700; }
      .status-failed { color: var(--bad); font-weight: 700; }
      .status-processing, .status-queued { font-weight: 700; }
      .error { color: var(--bad); }
      .empty {
        padding: 16px;
        border: 1px dashed var(--border);
        border-radius: 14px;
        color: var(--muted);
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="topbar">
        <h1>Downloaded FreeCAD files</h1>
        <a class="button" href="{{ url_for('upload_file') }}">Upload another file</a>
      </div>
      <div class="card">
        <p>This page lists every job folder and every file created by the worker. Each file can be downloaded directly.</p>
        {% if uploaded_job_id %}
          <p><strong>Queued job:</strong> <code>{{ uploaded_job_id }}</code></p>
        {% endif %}
      </div>
      {% if jobs %}
        {% for job in jobs %}
          <div class="card">
            <h2>Job <code>{{ job.job_id }}</code></h2>
            <p>
              Original file: <code>{{ job.original_filename }}</code><br>
              Status: <span class="status-{{ job.status }}">{{ job.status }}</span><br>
              Stage: <code>{{ job.stage }}</code>
            </p>
            {% if job.error %}
              <p class="error">{{ job.error }}</p>
            {% endif %}
            {% if job.files %}
              <ul>
                {% for filename in job.files %}
                  <li>
                    <a href="{{ url_for('download_file', job_id=job.job_id, filename=filename) }}">{{ filename }}</a>
                  </li>
                {% endfor %}
              </ul>
            {% else %}
              <div class="empty">No downloadable files yet.</div>
            {% endif %}
          </div>
        {% endfor %}
      {% else %}
        <div class="card">
          <div class="empty">No jobs have been uploaded yet.</div>
        </div>
      {% endif %}
    </div>
  </body>
</html>
"""


@app.get("/")
def index():
    return redirect(url_for("upload_file"))


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        uploaded = request.files.get("file")
        if not uploaded or not uploaded.filename:
            abort(400, "Please choose a FreeCAD file.")

        filename = secure_filename(uploaded.filename)
        if Path(filename).suffix.lower() != ".fcstd":
            abort(400, "Only .FCStd files are supported.")

        job_id = uuid.uuid4().hex
        directory = job_dir(job_id)
        directory.mkdir(parents=True, exist_ok=False)

        source_path = directory / "source.FCStd"
        uploaded.save(source_path)
        write_metadata(job_id, default_metadata(job_id, filename))

        from tasks import process_job

        process_job.delay(job_id)

        return redirect(url_for("files_view", uploaded=job_id))

    return render_template_string(UPLOAD_TEMPLATE, uploaded_job_id=request.args.get("uploaded"))


@app.get("/files")
def files_view():
    return render_template_string(
        FILES_TEMPLATE,
        jobs=list_jobs(),
        uploaded_job_id=request.args.get("uploaded"),
    )


@app.get("/files/<job_id>/<path:filename>")
def download_file(job_id: str, filename: str):
    directory = job_dir(job_id)
    if not directory.exists():
        abort(404)
    allowed_files = {
        file.name
        for file in directory.iterdir()
        if file.is_file() and file.name != "job.json"
    }
    if filename not in allowed_files:
        abort(404)
    return send_from_directory(directory, filename, as_attachment=True)
