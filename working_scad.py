"""Build the printable mesh from each OOMP record. All dimensions are in mm."""

from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory


def get_adapter(**kwargs):
    diameter = kwargs.get("diameter", 12)
    depth = kwargs.get("depth", 1.9)
    seat_radius = kwargs.get("seat_radius", 3.6)
    seat_depth = kwargs.get("seat_depth", 1.9)
    bore_radius = kwargs.get("bore_radius", 1.8)
    fastener_type = kwargs.get("fastener_type", "countersunk")

    sleeve_depth = kwargs.get("sleeve_depth", 0)
    sleeve_diameter = kwargs.get("sleeve_diameter", 5.75)
    body_depth = kwargs.get("body_depth", depth - sleeve_depth)

    if fastener_type == "nut":
        seat = f"cylinder(h={seat_depth:g}, r={seat_radius:g}, $fn=6);"
    else:
        seat = f"cylinder(h={seat_depth:g}, r1={bore_radius:g}, r2={seat_radius:g});"
    if sleeve_depth:
        # Print the broad flange on the bed and the locating sleeve upwards.
        return f"""translate([0, 0, {body_depth:g}]) rotate([180, 0, 0])
difference() {{
    union() {{
        cylinder(h={body_depth:g}, d={diameter:g});
        translate([0, 0, {-sleeve_depth:g}]) cylinder(h={sleeve_depth:g}, d={sleeve_diameter:g});
    }}
    translate([0, 0, {body_depth - seat_depth:g}]) {seat}
    translate([0, 0, {-sleeve_depth - 1:g}]) cylinder(h={depth + 2:g}, r={bore_radius:g});
}}
"""
    return f"""difference() {{
    cylinder(h={depth:g}, d={diameter:g});
    translate([0, 0, {depth - seat_depth:g}])
        {seat}
    translate([0, 0, -1])
        cylinder(h={depth + 2:g}, r={bore_radius:g});
}}
"""


def get_cap(**kwargs):
    diameter = kwargs.get("diameter", 14)
    depth = kwargs.get("depth", 2.9)
    wall_thickness = kwargs.get("wall_thickness", 1)
    roof_thickness = kwargs.get("roof_thickness", 1)
    fit_taper = kwargs.get("fit_taper", 0.075)

    inner_radius = diameter / 2 - wall_thickness
    # Print closed face down. The original over-cap opens at its wider end.
    return f"""difference() {{
    cylinder(h={depth:g}, d={diameter:g});
    translate([0, 0, {roof_thickness:g}])
        cylinder(h={depth - roof_thickness:g}, r1={inner_radius - fit_taper:g}, r2={inner_radius + fit_taper:g});
}}
"""


def main(**kwargs):
    root = Path(kwargs.get("root", Path(__file__).parent))
    records = kwargs["records"]
    openscad = kwargs.get("openscad") or shutil.which("openscad.com") or shutil.which("openscad")
    facets = kwargs.get("facets", 100)

    if not openscad:
        raise FileNotFoundError("Install OpenSCAD and put its executable on PATH.")
    recipes = {
        "adapter": get_adapter,
        "cap": get_cap,
    }
    for record in records:
        details = record["oobb_details"]
        recipe = recipes[details["oobb_type"]]
        folder = root / "parts" / record["oomp_id"]
        with TemporaryDirectory(dir=folder) as temporary:
            source = Path(temporary) / "3dpr.scad"
            mesh = Path(temporary) / "3dpr.stl"
            source.write_text(f"$fn = {facets};\n\n" + recipe(**details), encoding="utf-8", newline="\n")
            subprocess.run([openscad, "--export-format", "binstl", "-o", mesh, source], check=True)
            if mesh.stat().st_size <= 84:
                raise ValueError(f"Empty STL for {record['oomp_id']}")
            source.replace(folder / source.name)
            mesh.replace(folder / mesh.name)
