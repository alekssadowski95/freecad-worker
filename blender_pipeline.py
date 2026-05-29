from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from string import Template


def _blender() -> str:
    executable = shutil.which("blender") or shutil.which("Blender")
    if executable is None:
        raise RuntimeError("Blender is not installed in this environment.")
    return executable


def render_thumbnail(mesh_path: Path, image_path: Path) -> None:
    script = Template(
        """
from pathlib import Path

import bpy
from mathutils import Vector

mesh_path = Path(${mesh_path})
image_path = Path(${image_path})

def import_mesh(path: Path) -> None:
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=str(path))
        return

    try:
        bpy.ops.preferences.addon_enable(module="io_scene_obj")
    except Exception:
        pass
    bpy.ops.import_scene.obj(filepath=str(path))


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

import_mesh(mesh_path)
bpy.context.view_layer.update()

mesh_objects = [obj for obj in scene.objects if obj.type == "MESH"]
if not mesh_objects:
    raise RuntimeError("Blender did not import any mesh objects")

bounds = [obj.matrix_world @ Vector(corner) for obj in mesh_objects for corner in obj.bound_box]
min_x = min(vector.x for vector in bounds)
min_y = min(vector.y for vector in bounds)
min_z = min(vector.z for vector in bounds)
max_x = max(vector.x for vector in bounds)
max_y = max(vector.y for vector in bounds)
max_z = max(vector.z for vector in bounds)

center = Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0))
size = max(max_x - min_x, max_y - min_y, max_z - min_z, 1.0)

target = bpy.data.objects.new("ThumbnailTarget", None)
target.location = center
scene.collection.objects.link(target)

camera_data = bpy.data.cameras.new("ThumbnailCamera")
camera = bpy.data.objects.new("ThumbnailCamera", camera_data)
camera.location = center + Vector((size * 2.0, -size * 2.0, size * 1.5))
camera.data.type = "ORTHO"
camera.data.ortho_scale = size * 2.2
camera.data.clip_start = 0.01
camera.data.clip_end = size * 20.0
scene.collection.objects.link(camera)

track = camera.constraints.new(type="TRACK_TO")
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"
scene.camera = camera

sun_data = bpy.data.lights.new("ThumbnailSun", type="SUN")
sun_data.energy = 3.0
sun = bpy.data.objects.new("ThumbnailSun", sun_data)
sun.rotation_euler = (0.9, 0.0, 0.8)
scene.collection.objects.link(sun)

world = bpy.data.worlds.new("ThumbnailWorld")
world.use_nodes = True
background = world.node_tree.nodes["Background"]
background.inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
background.inputs[1].default_value = 0.85
scene.world = world

scene.render.engine = "CYCLES"
scene.cycles.samples = 16
scene.cycles.device = "CPU"
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(image_path)

bpy.ops.render.render(write_still=True)
"""
    ).substitute(mesh_path=repr(str(mesh_path)), image_path=repr(str(image_path)))

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
        handle.write(script)
        script_path = Path(handle.name)

    try:
        result = subprocess.run(
            [_blender(), "--background", "--python-exit-code", "1", "--python", str(script_path)],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ},
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Blender failed.\n"
                f"STDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            )
    finally:
        try:
            script_path.unlink()
        except FileNotFoundError:
            pass
