from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _freecadcmd() -> str:
    executable = shutil.which("freecadcmd") or shutil.which("FreeCADCmd")
    if executable is None:
        raise RuntimeError("FreeCADCmd is not installed in this environment.")
    return executable


def _run_freecad_script(script: str, source_path: Path, destination_path: Path) -> None:
    payload = script.format(
        source_path=repr(str(source_path)),
        destination_path=repr(str(destination_path)),
    )
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
        handle.write(payload)
        script_path = Path(handle.name)

    try:
        result = subprocess.run(
            [_freecadcmd(), str(script_path)],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ},
        )
        if result.returncode != 0:
            raise RuntimeError(
                "FreeCADCmd failed.\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            )
    finally:
        try:
            script_path.unlink()
        except FileNotFoundError:
            pass


def load_document(source_path: Path, destination_path: Path) -> None:
    script = """
from pathlib import Path

import FreeCAD as App

source = Path({source_path})
destination = Path({destination_path})

document = App.openDocument(str(source))
if document is None:
    raise RuntimeError("FreeCAD could not open " + str(source))

document_name = document.Name
try:
    document.recompute()
    document.saveAs(str(destination))
finally:
    App.closeDocument(document_name)
"""
    _run_freecad_script(script, source_path, destination_path)


def add_loaded_object(source_path: Path, destination_path: Path) -> None:
    script = """
from pathlib import Path

import FreeCAD as App

source = Path({source_path})
destination = Path({destination_path})

document = App.openDocument(str(source))
if document is None:
    raise RuntimeError("FreeCAD could not open " + str(source))

document_name = document.Name
try:
    loaded_object = document.getObject("loaded")
    if loaded_object is None:
        loaded_object = document.addObject("App::DocumentObjectGroup", "loaded")
        loaded_object.Label = "loaded"

    document.recompute()
    document.saveAs(str(destination))
finally:
    App.closeDocument(document_name)
"""
    _run_freecad_script(script, source_path, destination_path)
