"""Pack the catalogue STLs into the editable, single-plate Bambu Studio project.

source_file/default.3mf is a copy of three_d_printing_base/default.3mf.
Template SHA-256: 2dbe41cec9ed16e34dbe2c74a136f2b2d7bc7ec4a4ba0353d2cfd04c581c8d9e.
"""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image, ImageDraw
import trimesh

from p1s_print_kit import add_printable_copy
from working_oomp_populate import PROJECT_TITLE


CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
ET.register_namespace("", CORE)


def make_mesh(**kwargs):
    mesh = kwargs["mesh"]

    geometry = ET.Element(f"{{{CORE}}}mesh")
    vertices = ET.SubElement(geometry, f"{{{CORE}}}vertices")
    for x, y, z in mesh.vertices:
        ET.SubElement(vertices, f"{{{CORE}}}vertex", x=f"{x:.9g}", y=f"{y:.9g}", z=f"{z:.9g}")
    triangles = ET.SubElement(geometry, f"{{{CORE}}}triangles")
    for a, b, c in mesh.faces:
        ET.SubElement(triangles, f"{{{CORE}}}triangle", v1=str(a), v2=str(b), v3=str(c))
    return geometry


def main(**kwargs):
    root = Path(kwargs.get("root", Path(__file__).resolve().parent))
    records = kwargs["records"]
    mounting = kwargs["mounting"]
    records = [record for record in records if record["taxonomy_9"] == mounting]
    copies = kwargs.get("basic_set_copies", 5)
    gap = kwargs.get("basic_set_gap", 5)
    plate_name = "Basic set - " + mounting.replace("_", " ")
    template = root / "source_file" / "default.3mf"
    destination = root / "output" / f"basic_set_{mounting}" / "working.3mf"

    diameter = max(record["oobb_details"]["diameter"] for record in records)
    pitch = diameter + gap
    if copies < 1 or gap <= 0 or max(len(records), copies) * pitch > 200:
        raise ValueError("The basic set must fit in the central 200 mm square of the P1S plate.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(template) as source, TemporaryDirectory(dir=destination.parent) as temporary:
        settings = ET.fromstring(source.read("Metadata/model_settings.config"))
        plate = settings.find("plate")
        plate.find("metadata[@key='plater_name']").set("value", plate_name)
        for entry in list(plate):
            if entry.get("key") in ("thumbnail_no_light_file", "top_file", "pick_file"):
                plate.remove(entry)

        model = ET.fromstring(source.read("3D/3dmodel.model"))
        model.attrib.pop("requiredextensions", None)
        for entry in model.findall(f"{{{CORE}}}metadata"):
            if entry.get("name") == "Title":
                entry.text = f"{PROJECT_TITLE} - {mounting.replace('_', ' ')}"
            elif entry.get("name") not in ("Application", "BambuStudio:3mfVersion", "Thumbnail_Middle", "Thumbnail_Small"):
                model.remove(entry)
        resources = model.find(f"{{{CORE}}}resources")
        build = model.find(f"{{{CORE}}}build")
        preview = Image.new("RGB", (768, 768), "#eeeeea")
        draw = ImageDraw.Draw(preview)

        for row, record in enumerate(records):
            details = record["oobb_details"]
            size = details["size"].upper().replace("_", ".")
            fastener = details["fastener_type"].replace("screw_wood", "wood screw")
            name = f"{size} {fastener} {details['oobb_type']}"
            mesh = trimesh.load_mesh(root / "parts" / record["oomp_id"] / "3dpr.stl")
            if not mesh.is_volume or mesh.body_count != 1:
                raise ValueError(f"Invalid production mesh for {name}")
            if abs(mesh.bounds[0, 2]) > 0.001 or max(abs(mesh.bounds[:, :2].flatten())) > diameter / 2 + 0.001:
                raise ValueError(f"{name} is outside its planned print envelope")
            geometry = make_mesh(mesh=mesh)
            top_faces = mesh.triangles[mesh.face_normals[:, 2] > 0.001]

            for copy_index in range(copies):
                x = 128 + (copy_index - (copies - 1) / 2) * pitch
                y = 128 + ((len(records) - 1) / 2 - row) * pitch
                transform = f"1 0 0 0 1 0 0 0 1 {x:g} {y:g} 0"
                add_printable_copy(
                    serial=row * copies + copy_index + 1,
                    name=f"{name} ({copy_index + 1} of {copies})",
                    mesh=geometry,
                    resources=resources,
                    build=build,
                    settings=settings,
                    plate=plate,
                    transform=transform,
                    filament=1,
                )
                for triangle in top_faces:
                    points = [(round(3 * (x + vx)), round(3 * (256 - y - vy))) for vx, vy, _ in triangle]
                    draw.polygon(points, fill="#242424")

        archive = Path(temporary) / destination.name
        with ZipFile(archive, "w", ZIP_DEFLATED) as output:
            for filename in ("[Content_Types].xml", "_rels/.rels", "Metadata/project_settings.config",
                             "Metadata/slice_info.config", "Metadata/filament_sequence.json"):
                output.writestr(filename, source.read(filename))
            output.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))
            output.writestr("Metadata/model_settings.config", ET.tostring(settings, encoding="utf-8", xml_declaration=True))
            for filename, size in (("plate_1.png", 512), ("plate_1_small.png", 128)):
                image = BytesIO()
                preview.resize((size, size), Image.Resampling.LANCZOS).save(image, "PNG")
                output.writestr(f"Metadata/{filename}", image.getvalue())
        archive.replace(destination)
