from __future__ import annotations

from pathlib import Path


def _freecad_app():
    try:
        import FreeCAD as app
    except ImportError as exc:  # pragma: no cover - depends on container image
        raise RuntimeError(
            "FreeCAD is not installed in this environment."
        ) from exc
    return app


def load_document(source_path: Path, destination_path: Path) -> None:
    app = _freecad_app()
    document = app.openDocument(str(source_path))
    if document is None:
        raise RuntimeError(f"FreeCAD could not open {source_path}")

    document_name = document.Name
    try:
        document.recompute()
        document.saveAs(str(destination_path))
    finally:
        app.closeDocument(document_name)


def add_loaded_object(source_path: Path, destination_path: Path) -> None:
    app = _freecad_app()
    document = app.openDocument(str(source_path))
    if document is None:
        raise RuntimeError(f"FreeCAD could not open {source_path}")

    document_name = document.Name
    try:
        loaded_object = document.getObject("loaded")
        if loaded_object is None:
            try:
                loaded_object = document.addObject("App::DocumentObjectGroup", "loaded")
            except Exception:
                loaded_object = document.addObject("App::FeaturePython", "loaded")
            loaded_object.Label = "loaded"

        document.recompute()
        document.saveAs(str(destination_path))
    finally:
        app.closeDocument(document_name)

