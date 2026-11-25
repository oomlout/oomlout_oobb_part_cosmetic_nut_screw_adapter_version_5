"""Generate the project, print-set and taxonomy pages from the active records."""

import os
import re
import shutil
from pathlib import Path
from filecmp import cmp

from working_oomp_populate import PROJECT_ID, PROJECT_TITLE, assembly_steps, example_steps, get_mountings, get_usage

NOTICE = "AI-generated CAD images and instructions. Errors possible."


def link(folder, target):
    path = Path(os.path.relpath(target, folder)).as_posix()
    return path + "/" if target.is_dir() else path


def write_page(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def hardware_link(identity):
    repository = (
        "oomp_hardware_screw_version_5"
        if identity.startswith("hardware_screw_")
        else "oomp_hardware_bolt_version_5"
    )
    return f"https://github.com/oomlout/{repository}/tree/main/parts/{identity}"


def taxonomy_label(segment):
    labels = {
        "oobb": "OOBB",
        "m3": "M3",
        "m3_5": "M3.5",
        "m6": "M6",
        "to_flat": "To flat",
        "to_m6": "To M6",
        "nut": "Hex nut",
        "screw_wood": "Wood screw",
    }
    dimension = re.fullmatch(r"(\d+(?:_\d+)?)_mm_(diameter|depth)", segment)
    if dimension:
        return dimension[1].replace("_", ".") + " mm " + dimension[2]
    return labels.get(segment, segment.replace("_", " ").capitalize())


def main(**kwargs):
    root = Path(kwargs.get("root", Path(__file__).parent))
    records = kwargs["records"]
    navigation = root / "navigation_oobb"
    examples = get_usage()
    mountings = get_mountings()

    branches = {}
    pairs = {}
    for record in records:
        d = record["oobb_details"]
        key = (d["mounting"], d["size"], d["fastener_type"])
        pairs.setdefault(key, {})[d["oobb_type"]] = record
    backing_folder = root / "parts" / pairs["to_flat", "m3", "nut"]["adapter"]["oomp_id"]
    for record in records:
        d = record["oobb_details"]
        mounting = d["mounting"]
        kind = d["oobb_type"]
        example = examples[d["size"], d["fastener_type"]]
        pair = pairs[mounting, d["size"], d["fastener_type"]]
        adapter = pair["adapter"]
        cap = pair["cap"]
        mate = pair["cap" if kind == "adapter" else "adapter"]
        title = f"{example['label']} {kind} · {mountings[mounting]['title']}"
        canonical = root / "parts" / record["oomp_id"]
        kit = root / "output" / f"basic_set_{mounting}"
        leaf = navigation
        for level in range(1, 10):
            segment = record[f"taxonomy_{level}"]
            branches.setdefault(leaf, set()).add(segment)
            leaf = leaf / segment
        leaf.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(canonical / "3dpr.stl", leaf / "3dpr.stl")
        if not cmp(canonical / "3dpr.stl", leaf / "3dpr.stl", shallow=False):
            raise OSError(f"Navigation STL differs for {title}")
        write_page(leaf / "oomp_id.txt", [record["oomp_id"]])
        for folder in (canonical, leaf):

            def ref(path):
                return link(folder, path)

            view = root / "parts" / adapter["oomp_id"] / "installation.png"
            lines = [
                f"# {title}",
                "",
                f"![Opposite faces of the printed part]({ref(canonical / 'studio.png')})",
                "",
                f"Outside diameter **{d['diameter']:g} mm** · overall height **{d['depth']:g} mm**.",
                "",
                f"[Print this {kind}](3dpr.stl) · [Matching {mate['taxonomy_4']}]({ref(root / 'parts' / mate['oomp_id'])}) · [40-piece print set]({ref(kit / 'working.3mf')})",
                "",
                "## Assembly",
                "",
            ]
            steps = assembly_steps(details=adapter["oobb_details"], example=example)
            lines.extend(f"{i}. {step}" for i, step in enumerate(steps, 1))
            if d["fastener_type"] == "countersunk":
                lines.extend(["", f"[Print the flat M3 backing adapter]({ref(backing_folder / '3dpr.stl')})."])
            if "bolt_head_seat" in example:
                lines.extend([
                    "", "## Using an M6 hex-head bolt", "", example["bolt_head_seat"], "",
                    f"![M6 bolt head above and seated in the nut adapter]({ref(view.with_name('bolt_head.png'))})",
                ])
            lines.extend(
                [
                    "",
                    f"![Exploded installation with full-detail {example['label']} hardware]({ref(view)})",
                    "",
                    "The black flange rests on the teal plate. The yellow cap covers the exposed flange. "
                    "The same fastener takes the same cap in either mounting version.",
                    "",
                    f"[Hardware record]({hardware_link(example['hardware'])}) · [Set guide]({ref(kit)}) · [Canonical part]({ref(canonical)})",
                    "",
                    NOTICE + " Physical fit has not been tested.",
                    "",
                    f"OOMP ID `{record['oomp_id']}`",
                ]
            )
            write_page(folder / "README.md", lines)

    for branch, children in branches.items():
        crumbs = branch.relative_to(navigation).parts
        path_label = " / ".join(taxonomy_label(word) for word in crumbs)
        lines = [f"# {path_label or PROJECT_TITLE}", "", "Choose a category to see the available parts.", ""]
        if crumbs[-2:] == ("m6", "nut"):
            lines.extend(["This pocket accepts an M6 hex nut or an M6 hex-head bolt measuring 10 mm across the flats. The same cap covers either.", ""])
        for child in sorted(children):
            lines.append(f"- [{taxonomy_label(child)}]({child}/)")
        if crumbs:
            lines.extend(["", "[Up one category](../)"])
        lines.extend(["", f"[Project and print sets]({link(branch, root)})"])
        write_page(branch / "README.md", lines)

    root_lines = [
        "# " + PROJECT_TITLE,
        "",
        "These printable adapters seat a countersunk screw, wood screw or hex nut on an OOBB part. "
        "A plain 14 mm cap covers the fastener and follows the width of a single OOBB strip.",
        "",
        f"Project repository: [{PROJECT_ID}](https://github.com/oomlout/{PROJECT_ID}).",
        "",
        "Adapted from [Oomlout’s original hardware screw and nut adapters](https://github.com/oomlout/oomlout_oobb_hardware_screw_nut_adapter).",
        "",
        "This is an entirely AI-generated coding project. The source is largely unreadable by humans. "
        "Usable generated files are included so others can use their own AI tools to modify and regenerate the design.",
        "",
        NOTICE + " Physical fit has not been tested.",
        "",
        "## Choose a print set",
        "",
        "Each editable Bambu Studio project contains five of each of the four adapters and five matching caps per style. "
        "Both use the default P1S 0.4 mm profile and black filament in slot 1. The illustrations use colour to distinguish the parts.",
        "",
        "| Mounting | When to use it | Files |",
        "| --- | --- | --- |",
    ]
    for mounting, spec in mountings.items():
        kit = root / "output" / f"basic_set_{mounting}"
        route = link(root, kit)
        root_lines.append(
            f"| [![{spec['title']} installation]({route}assembled.png)]({route}) **[{spec['title']}]({route})** "
            f"| {spec['description']} | [P1S plate]({route}working.3mf) · [Illustrated guide]({route}#assembly) · "
            f"[Offline HTML]({route}assembly/assembly_instructions.html) · [PDF]({route}assembly/assembly_instructions.pdf) |"
        )
        lines = [
            f"# {spec['title']} · basic set",
            "",
            spec["description"],
            "",
            f"![Covered joint, seated screw and M6 nut on a teal 3 × 3 OOBB plate](assembled.png)",
            "",
            "![Exploded screw and bolt assemblies](exploded.png)",
            "",
            "Left: M3 countersunk screw with a second black adapter holding the M3 nut behind the plate. Right: M6 nut seated in its adapter, with the bolt entering from below.",
            "",
            "[Open the 40-piece P1S project](working.3mf) · [Assembly booklet (PDF)](assembly/assembly_instructions.pdf) · "
            "[Standalone HTML guide](assembly/assembly_instructions.html)",
            "",
            "The plate contains five adapters and five caps for each row below. To recolour one piece in Bambu Studio, open **Prepare → Objects**, select its numbered copy and choose a slot in the filament column. "
            "Diameters are 12 mm for the flange and 14 mm for the cap. "
            "Adapter height includes any locating sleeve. Cap height includes the 1 mm roof.",
            "",
            "| Fastener | Adapter height | Cap height |",
            "| --- | ---: | ---: |",
        ]
        for (size, fastener), example in examples.items():
            pair = pairs[mounting, size, fastener]
            columns = []
            for kind in ("adapter", "cap"):
                r = pair[kind]
                columns.append(f"[{r['oobb_details']['depth']:g} mm]({link(kit,root/'parts'/r['oomp_id'])})")
            fastener_label = "M6 hex nut or hex-head bolt" if "bolt_head_seat" in example else example["label"]
            lines.append(f"| {fastener_label} | " + " | ".join(columns) + " |")
        lines.extend(
            [
                "",
                "## Assembly",
                "",
                "The worked example uses an M3 × 10 mm countersunk screw and a nut captured in a flat M3 nut adapter behind a 3 mm plate.",
                "",
            ]
        )
        backing_note = ("Use one from this set." if mounting == "to_flat" else
                        "Print this extra flat adapter for the back. Two opposed locating sleeves would meet inside the 3 mm plate.")
        lines.extend([f"[Flat M3 nut adapter STL]({link(kit, backing_folder / '3dpr.stl')}). {backing_note}", ""])
        for n, (heading, action) in enumerate(example_steps(mounting=mounting), 1):
            lines.extend([f"**{n}. {heading}.** {action}", "", f"![{heading}](assembly/step_{n}.png)", ""])
        lines.extend(["## Other fasteners", ""])
        for (size, fastener), example in examples.items():
            if fastener != "countersunk":
                r = pairs[mounting, size, fastener]["adapter"]
                target = root / "parts" / r["oomp_id"]
                lines.extend(
                    [
                        f"### {example['label']}",
                        "",
                        example["seat"],
                        "",
                        f"[![{example['label']} installation]({link(kit,target/'installation.png')})]({link(kit,target)})",
                        "",
                    ]
                )
                if "bolt_head_seat" in example:
                    lines.extend([
                        "#### Capturing the bolt head", "", example["bolt_head_seat"], "",
                        f"![M6 hex-head bolt exploded and seated]({link(kit, target/'bolt_head.png')})", "",
                    ])
        lines.extend(
            [
                "## Print and fit",
                "",
                "Print the supplied orientations. The cap prints closed face down. Where an adapter has a sleeve, the flange prints against the bed and the sleeve points up.",
                "",
                "The cap cavity tapers from 12.15 mm at the mouth to 11.85 mm below the roof. Try one pair with your filament before printing the whole plate. "
                "The M6 nut pocket leaves about 0.09 mm of plastic at its six corners. Inspect these points after printing.",
                "",
                NOTICE + " Physical fit has not been tested.",
                "",
                f"[Project catalogue]({link(kit,root)})",
            ]
        )
        write_page(kit / "README.md", lines)

    root_lines.extend(
        [
            "",
            "## Assembly",
            "",
            "1. Choose the fastener and mounting version. Centre the flat flange over the hole, or insert the M6 locating sleeve.",
            "2. Seat the fastener. For a nut, align its flats and insert the mating screw from the reverse side. For a wood screw, provide a timber backing.",
            "3. Tighten the joint and check the exposed height. Press the matching cap over the flange.",
            "",
            "![Exploded screw and bolt joints on a teal 3 × 3 plate](output/basic_set_to_m6/exploded.png)",
            "",
            f"The left joint uses an M3 countersunk screw and a [flat M3 nut adapter]({link(root, backing_folder)}) on the back of the plate. The right joint captures the M6 nut.",
            "",
            "### Using the M6 nut adapter for a bolt head",
            "",
            examples["m6", "nut"]["bolt_head_seat"],
            "",
            f"![Exploded and seated M6 bolt heads in the same adapter]({link(root, root/'parts'/pairs['to_flat', 'm6', 'nut']['adapter']['oomp_id']/'bolt_head.png')})",
            "",
            "[Browse individual printable parts by taxonomy](navigation_oobb/oobb/part/cosmetic/) · [Full-detail CAD sources](source_file/README.md)",
            "",
            "## Regeneration",
            "",
            "Install Python 3.10 or newer, OpenSCAD and Blender 5.2. Put both applications on PATH. From the project folder run:",
            "",
            "```powershell",
            "python -m pip install -r requirements.txt",
            "python action_make_all.py",
            "```",
            "",
            "On Windows, `.\\make_all.bat` runs the same build. Edit the dimensions and assembly text in "
            "[working_oomp_populate.py](working_oomp_populate.py). The P1S template, hardware meshes and plate geometry are included for offline regeneration.",
        ]
    )
    write_page(root / "README.md", root_lines)
