"""Render catalogue and installation views in Blender from the printable meshes."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import trimesh
import numpy as np
from PIL import Image

from working_oomp_populate import get_usage


def main(**kwargs):
    root = Path(kwargs.get("root", Path(__file__).resolve().parent))
    records = kwargs["records"]
    blender = kwargs.get("blender") or shutil.which("blender")
    source = root / "source_file"
    script = root / "render_studio.py"
    hardware_files = sorted(source.glob("oomp_*/parts/*/three_d_model/model_full.glb"))
    plate = source / "oomlout_oobb_part_plate_version_5/parts/oobb_part_plate_basic_3_width_3_height_3_depth/3dpr_solidcraft.stl"
    assets = {}
    expected = []
    expected.append(source / "previews" / "plate.png")
    expected.extend(source / "previews" / (f.parent.parent.name + ".png") for f in hardware_files)
    for record in records:
        folder = root / "parts" / record["oomp_id"]
        assets[record["oomp_id"]] = str(folder / "3dpr.stl")
        expected.append(folder / "studio.png")
        if record["taxonomy_4"] == "adapter":
            expected.append(folder / "installation.png")
            if record["taxonomy_5"] == "m6" and record["taxonomy_6"] == "nut":
                expected.append(folder / "bolt_head.png")
    for mounting in ("to_flat", "to_m6"):
        folder = root / "output" / f"basic_set_{mounting}"
        expected.append(folder / "assembled.png")
        expected.append(folder / "exploded.png")
        expected.append(folder / "assembly" / "finished.png")
        expected.extend(folder / "assembly" / f"step_{i}.png" for i in range(1, 5))
    digest = hashlib.sha256()
    for file in [Path(__file__), script, root / "working_oomp_populate.py", plate, *hardware_files, *map(Path, assets.values())]:
        digest.update(file.read_bytes())
    key = digest.hexdigest()
    stamp = root / "output" / ".render.sha256"
    def check_images():
        for file in expected:
            with Image.open(file) as image:
                image.verify()

    if stamp.is_file() and stamp.read_text().strip() == key:
        try:
            check_images()
        except (OSError, SyntaxError):
            pass
        else:
            return
    if not blender:
        raise FileNotFoundError("Install Blender and put blender on PATH to regenerate the studio views.")
    with TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        for file in hardware_files:
            mesh = trimesh.load_scene(file).to_mesh()
            # glTF uses metres and Y up. STL and the studio use millimetres and Z up.
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
            mesh.apply_scale(1000)
            identity = file.parent.parent.name
            target = workspace / (identity + ".stl")
            mesh.export(target)
            assets[identity] = str(target)
        assets["plate"] = str(plate)
        tasks = []
        for record in records:
            details = record["oobb_details"]
            example = get_usage()[(details["size"], details["fastener_type"])]
            task = {
                "id": record["oomp_id"],
                "details": details,
                "example": example,
            }
            tasks.append(task)
        job = {
            "root": str(root),
            "assets": assets,
            "parts": tasks,
        }
        manifest = workspace / "job.json"
        manifest.write_text(json.dumps(job), encoding="utf-8")
        subprocess.run([blender, "-b", "--python-exit-code", "1", "-P", str(script), "--", str(manifest)], check=True)
    check_images()
    stamp.write_text(key + "\n")
