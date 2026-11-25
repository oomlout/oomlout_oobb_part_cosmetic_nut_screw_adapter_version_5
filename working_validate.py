"""Check the two print sets, printable navigation leaves and published local links."""

import json
from itertools import combinations
from math import dist
from pathlib import Path
import re
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import fitz
import numpy as np
import trimesh

from p1s_print_kit import validate_editable_copies
from working_oomp_populate import PROJECT_ID, PROJECT_TITLE


def main(**kwargs):
    root = Path(kwargs.get("root", Path(__file__).resolve().parent))
    records = kwargs["records"]
    navigation = root / "navigation_oobb"
    expected_leaves = set()
    for record in records:
        folder = root / "parts" / record["oomp_id"]
        d = record["oobb_details"]
        leaf = navigation.joinpath(*(record[f"taxonomy_{n}"] for n in range(1, 10)))
        expected_leaves.add(leaf)
        mesh = trimesh.load_mesh(folder / "3dpr.stl")
        if (
            not mesh.is_volume
            or mesh.body_count != 1
            or not np.allclose(mesh.extents, [d["diameter"], d["diameter"], d["depth"]])
        ):
            raise ValueError(f"Incorrect dimensions or disconnected mesh in {folder}")
        if (leaf / "3dpr.stl").read_bytes() != (folder / "3dpr.stl").read_bytes() or (
            leaf / "oomp_id.txt"
        ).read_text().strip() != folder.name:
            raise ValueError(f"Navigation leaf does not match {folder}")
    if {f.parent for f in navigation.rglob("3dpr.stl")} != expected_leaves:
        raise ValueError("Unexpected printable leaf outside the current taxonomy")
    with ZipFile(root / "source_file/default.3mf") as template:
        settings = template.read("Metadata/project_settings.config")
    for mounting in ("to_flat", "to_m6"):
        kit = root / "output" / f"basic_set_{mounting}"
        selected = [record for record in records if record["taxonomy_9"] == mounting]
        with ZipFile(kit / "working.3mf") as archive:
            if archive.testzip() or archive.read("Metadata/project_settings.config") != settings:
                raise ValueError(f"Damaged archive or unexpected printer profile in {kit}")
            model = ET.fromstring(archive.read("3D/3dmodel.model"))
            if model.findtext("{*}metadata[@name='Title']") != f"{PROJECT_TITLE} - {mounting.replace('_', ' ')}":
                raise ValueError(f"Incorrect project title in {kit}")
            items = model.findall(".//{*}build/{*}item")
            config = ET.fromstring(archive.read("Metadata/model_settings.config"))
            copies = kwargs.get("basic_set_copies", 5)
            meshes = validate_editable_copies(
                model=model,
                settings=config,
                count=len(selected) * copies,
                filament_count=len(json.loads(settings)["filament_colour"]),
            )
            if len(config.findall("plate")) != 1:
                raise ValueError(f"Incorrect plate count in {kit}")
            radii = {}
            for row, record in enumerate(selected):
                original = trimesh.load_mesh(root / "parts" / record["oomp_id"] / "3dpr.stl")
                for item in items[row * copies:(row + 1) * copies]:
                    object_id = item.get("objectid")
                    vertices = np.array([
                        [float(v.get(k)) for k in "xyz"] for v in meshes[object_id].findall(".//{*}vertex")
                    ])
                    if vertices.shape != original.vertices.shape or not np.allclose(vertices, original.vertices):
                        raise ValueError(f"Incorrect geometry for {record['oomp_id']} in {kit}")
                    radii[object_id] = record["oobb_details"]["diameter"] / 2
            placements = []
            for item in items:
                x, y, z = map(float, item.get("transform").split()[-3:])
                r = radii[item.get("objectid")]
                if z != 0 or not (28 + r <= x <= 256 - r and 28 + r <= y <= 256 - r):
                    raise ValueError(f"Invalid position in {kit}")
                placements.append((x, y, r))
            if any(dist(a[:2], b[:2]) <= a[2] + b[2] for a, b in combinations(placements, 2)):
                raise ValueError(f"Overlapping print instances in {kit}")
        with fitz.open(kit / "assembly/assembly_instructions.pdf") as doc:
            if len(doc) != 9 or any(
                abs(page.rect.width - 841.89) > 1 or abs(page.rect.height - 595.28) > 1 for page in doc
            ):
                raise ValueError(f"Invalid landscape A4 book in {kit}")
            if PROJECT_ID not in doc[0].get_text() or "Capture an M6 bolt head" not in doc[4].get_text():
                raise ValueError(f"Incorrect cover or missing bolt-head guide in {kit}")
    for page in root.rglob("README.md"):
        for href in re.findall(r"\]\(([^)]+)\)", page.read_text(encoding="utf-8")):
            path = href.partition("#")[0]
            if path and "://" not in path and not (page.parent / path).exists():
                raise FileNotFoundError(f"{page}: {href}")
