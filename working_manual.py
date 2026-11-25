"""Build the two assembly books and their offline page viewers from the same CAD."""

import base64
import csv
import hashlib
import json
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET

import fitz
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen.canvas import Canvas

from working_oomp_populate import PROJECT_ID, PROJECT_TITLE, example_steps, get_mountings, get_usage
from working_navigation import hardware_link, write_page


def source_catalogue(**kwargs):
    root = kwargs["root"]
    source = root / "source_file"
    files = sorted(source.glob("*/parts/*/three_d_model/model_full.glb"))
    files.extend(source.glob("*/parts/*/3dpr_solidcraft.stl"))
    lines = [
        "# Source models",
        "",
        "The illustrations use the full-detail GLBs from the OOMP screw and bolt catalogues, including the modelled threads and drive recesses. "
        "The mounting plate is the production 3 × 3 × 3 mm-depth OOBB plate. The wood-screw view includes an illustrative timber block.",
        "",
        "| Catalogue record | Retained source | SHA-256 |",
        "| --- | --- | --- |",
    ]
    for file in files:
        path = file.relative_to(source)
        repo, _, identity = path.parts[:3]
        url = f"https://github.com/oomlout/{repo}/tree/main/parts/{identity}"
        lines.append(
            f"| [{identity}]({url}) | [{file.name}]({path.as_posix()}) | `{hashlib.sha256(file.read_bytes()).hexdigest()}` |"
        )
    for filename, provenance in [
        ("default.3mf", "three_d_printing_base/default.3mf"),
        (
            "assembly_page_viewer.html",
            "Adapted from oomlout_oobb_version_5/presentation/templates/assembly_page_viewer.html",
        ),
        (
            "oomlout-LOGO-unshaded-vector.svg",
            "oomlout_media/logos/logo_vector_unshaded/oomlout-LOGO-unshaded-vector.svg",
        ),
    ]:
        lines.append(
            f"| {provenance} | [{filename}]({filename}) | `{hashlib.sha256((source/filename).read_bytes()).hexdigest()}` |"
        )
    write_page(source / "README.md", lines)


def short_code(identity):
    number = int(hashlib.md5(identity.encode()).hexdigest()[:6], 16)
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = ""
    while number:
        number, remainder = divmod(number, 36)
        result = digits[remainder] + result
    return result or "0"


def book(**kwargs):
    root = kwargs["root"]
    records = kwargs["records"]
    mounting = kwargs["mounting"]
    title = get_mountings()[mounting]["title"]
    kit = root / "output" / ("basic_set_" + mounting)
    folder = kit / "assembly"
    pdf = folder / "assembly_instructions.pdf"
    width, height = landscape(A4)
    c = Canvas(str(pdf), pagesize=(width, height), invariant=True)
    c.setTitle(f"{PROJECT_TITLE} | {title}")
    c.setAuthor("Oomlout")
    examples = get_usage()
    selected = [r for r in records if r["taxonomy_9"] == mounting]
    folders = {
        (r["taxonomy_5"], r["taxonomy_6"], r["taxonomy_4"]): root / "parts" / r["oomp_id"] for r in selected
    }
    backing = next(
        root / "parts" / record["oomp_id"]
        for record in records
        if (record["taxonomy_9"], record["taxonomy_5"], record["taxonomy_6"], record["taxonomy_4"])
        == ("to_flat", "m3", "nut", "adapter")
    )
    source = root / "source_file"
    logo = ET.parse(source / "oomlout-LOGO-unshaded-vector.svg").getroot()
    path = logo.find(".//{*}path").get("d")
    symbol = "z".join(path.split("z", 3)[:3]) + "z"
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 17.5 10" width="175" height="100"><path fill="black" fill-rule="evenodd" d="{symbol}"/></svg>'
    with fitz.open(stream=svg.encode(), filetype="svg") as doc:
        badge = ImageReader(BytesIO(doc[0].get_pixmap(alpha=True).tobytes("png")))

    def image(file, x, y, w, h):
        c.drawImage(str(file), x, y, w, h, preserveAspectRatio=True, anchor="c")

    def type_line(text, x, y, font="Helvetica", size=13):
        c.setFont(font, size)
        c.drawString(x, y, text)

    def paragraph(text, x, y, w, size=13, leading=18):
        for line in simpleSplit(text, "Helvetica", size, w):
            type_line(line, x, y, size=size)
            y -= leading
        return y

    def header(name, page):
        c.setLineWidth(1)
        c.line(28, height - 61, width - 28, height - 61)
        type_line(name, 30, height - 47, "Helvetica-Bold", 24)
        type_line(f"{title}  /  {page:02}", width - 120, height - 44, "Courier", 11)

    def cover_border():
        c.setLineWidth(3)
        c.rect(19, 19, width - 38, height - 38)
        c.drawImage(badge, 40, height - 77, 60, 35, mask="auto")

    cover_border()
    type_line(PROJECT_TITLE, 39, height - 135, "Helvetica-Bold", 30)
    type_line(f"{title} mounting   /   Four fastener styles", 41, height - 168, size=20)
    image(kit / "assembled.png", 40, 84, width - 80, height - 270)
    type_line(PROJECT_ID, 40, 57, "Courier", 10)
    c.linkURL(f"https://github.com/oomlout/{PROJECT_ID}", (40, 55, 40 + len(PROJECT_ID) * 6, 67))
    type_line("Assembly booklet   /   editable P1S print set", 40, 39, size=10)
    c.showPage()

    header("Parts and preparation", 2)
    y = height - 101
    for heading, text in [
        ("Choose the mounting", get_mountings()[mounting]["description"]),
        (
            "Print the set",
            "Print caps closed face down and sleeved adapters sleeve up. " +
            ("Print one extra To flat M3 nut adapter for the back of the 3 mm plate. Opposed sleeves would meet inside the hole."
             if mounting == "to_m6" else "Use a flat M3 nut adapter from the set to hold the backing nut."),
        ),
        (
            "Check the joint",
            "The flange is 12 mm across and the cap is 14 mm across. Try one cap on a printed flange before printing the set. Check screw engagement, timber thickness where applicable and clearance under the closed cap.",
        ),
        (
            "Read the illustrations",
            "Teal identifies the 3 × 3 plate, black the adapter and yellow the cap. The P1S plate uses black filament. Metal threads and drive recesses come from full-detail OOMP hardware models.",
        ),
    ]:
        type_line(heading, 32, y, "Helvetica-Bold", 17)
        y = paragraph(text, 32, y - 21, 393, size=11.5, leading=15) - 18
    image(kit / "exploded.png", 441, 93, width - 472, height - 167)
    paragraph("Left: M3 screw with nut and backing adapter. Right: M6 nut with hex-head bolt.", 449, 77, width - 490, 10, 12)
    paragraph(
        "AI-generated CAD images and instructions. Errors possible. Physical fit has not been tested.",
        32,
        48,
        width - 70,
        10,
    )
    c.showPage()

    header("M3 countersunk assembly", 3)
    steps = example_steps(mounting=mounting)
    screw_id = examples["m3", "countersunk"]["hardware"]
    additions = [
        [
            (source / "previews/plate.png", "OOBB plate"),
            (backing / "studio.png", "M3 nut adapter"),
            (source / "previews/hardware_nut_m3.png", "hardware_nut_m3"),
        ],
        [(folders["m3", "countersunk", "adapter"] / "studio.png", "Adapter")],
        [(source / "previews" / (screw_id + ".png"), screw_id)],
        [(folders["m3", "countersunk", "cap"] / "studio.png", "Cap")],
    ]
    panel_w, panel_h = (width - 64) / 2, (height - 94) / 2
    for i, (heading, action) in enumerate(steps):
        x = 28 + (i % 2) * (panel_w + 8)
        y = 20 + (1 - i // 2) * (panel_h + 7)
        c.rect(x, y, panel_w, panel_h)
        type_line(str(i + 1), x + 11, y + panel_h - 25, "Helvetica-Bold", 20)
        type_line(heading, x + 38, y + panel_h - 23, "Helvetica-Bold", 14)
        image(folder / f"step_{i+1}.png", x + 7, y + 48, panel_w - 85, panel_h - 80)
        for j, (thumb, identity) in enumerate(additions[i]):
            rail_x, rail_y = x + panel_w - 74, y + panel_h - 82 - j * 50
            image(thumb, rail_x, rail_y, 64, 39)
            purchased = identity.startswith("hardware_")
            label = "oom.lt/a/" + short_code(identity) if purchased else identity
            type_line(label, rail_x, rail_y - 8, "Courier", 7.4)
            if purchased:
                c.linkURL("https://" + label, (rail_x, rail_y - 10, rail_x + 65, rail_y))
        paragraph(action, x + 10, y + 34, panel_w - 20, 10, 12)
    c.showPage()

    for page, category, choices in [
        (4, "Hex nut seats", [("m3", "nut"), ("m6", "nut")]),
        (6, "Countersunk seats", [("m3", "countersunk"), ("m3_5", "screw_wood")]),
    ]:
        header(category, page)
        for i, key in enumerate(choices):
            example = examples[key]
            x = 29 + i * (width - 48) / 2
            w = (width - 74) / 2
            type_line(example["label"], x, height - 94, "Helvetica-Bold", 18)
            image(folders[(*key, "adapter")] / "installation.png", x, 169, w, height - 286)
            paragraph(example["seat"], x, 146, w, 12, 16)
            identity = example["hardware"]
            label = "oom.lt/a/" + short_code(identity)
            type_line(label, x, 43, "Courier", 11)
            c.linkURL("https://" + label, (x, 39, x + 125, 56))
        c.showPage()
        if page == 4:
            example = examples["m6", "nut"]
            header("Capture an M6 bolt head", 5)
            image(folders["m6", "nut", "adapter"] / "bolt_head.png", 30, 43, 415, height - 123)
            type_line("Bolt head in the pocket", 467, height - 126, "Helvetica-Bold", 19)
            y = paragraph(example["bolt_head_seat"], 467, height - 157, 325)
            y = paragraph("The full-detail example uses an M6 × 12 mm hex-head bolt on a 3 mm plate. Its 4 mm head sits inside the 5 mm pocket.", 467, y - 21, 325)
            type_line("Full-detail M6 bolt model", 467, y - 22, "Helvetica", 11)
            c.linkURL(hardware_link(example["bolt_head_example"]), (467, y - 26, 590, y - 10))
            c.showPage()

    header("Completed assembly", 7)
    image(folder / "finished.png", 40, 75, width - 80, height - 160)
    paragraph(
        "The cap covers the screw head. The flat M3 nut adapter holds the nut on the reverse side.",
        32,
        42,
        width - 68,
        12,
    )
    c.showPage()

    header("One M3 countersunk joint", 8)
    inventory = []

    def item(label, identity, thumb, purchased):
        row = {
            "name": label,
            "quantity": 1,
            "id": identity,
            "md5_6_alpha": short_code(identity) if purchased else "",
            "source": hardware_link(identity) if purchased else "",
        }
        inventory.append(row)
        return thumb

    thumbnails = []
    for kind in ("adapter", "cap"):
        part = folders["m3", "countersunk", kind]
        thumbnails.append(item("M3 countersunk " + kind, part.name, part / "studio.png", False))
    thumbnails.append(item("To flat M3 nut adapter", backing.name, backing / "studio.png", False))
    thumbnails.append(
        item(
            "3 x 3 OOBB plate, 3 mm",
            "oobb_part_plate_basic_3_width_3_height_3_depth",
            source / "previews/plate.png",
            False,
        )
    )
    for label, identity in [
        ("M3 x 10 mm countersunk PZ", examples["m3", "countersunk"]["hardware"]),
        ("M3 hex nut", "hardware_nut_m3"),
    ]:
        thumbnails.append(item(label, identity, source / "previews" / (identity + ".png"), True))
    for group, label in enumerate(("Printed parts and mounting plate", "Purchased hardware")):
        y = 294 if group == 0 else 47
        c.rect(29, y, width - 58, 220)
        type_line(label, 40, y + 194, "Helvetica-Bold", 15)
        indices = range(4) if group == 0 else range(4, len(inventory))
        for j, i in enumerate(indices):
            x = 40 + j * (width - 82) / len(indices)
            image(thumbnails[i], x, y + 50, (width - 112) / len(indices), 133)
            row = inventory[i]
            type_line(row["name"], x, y + 32, "Helvetica-Bold", 12)
            if row["md5_6_alpha"]:
                label_url = "oom.lt/a/" + row["md5_6_alpha"]
                type_line(label_url, x, y + 13, "Courier", 10)
                c.linkURL("https://" + label_url, (x, y + 9, x + 105, y + 24))
    c.showPage()
    cover_border()
    c.showPage()
    c.save()
    with (folder / "parts.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=inventory[0].keys())
        writer.writeheader()
        writer.writerows(inventory)

    images = {}
    slides = []
    labels = [
        "Cover",
        "Preparation",
        "Steps 1-4",
        "Hex nut seats",
        "M6 bolt head",
        "Countersunk seats",
        "Completed assembly",
        "Parts list",
        "Back cover",
    ]
    kinds = ["cover", "details", "instructions", "details", "details", "details", "summary", "parts", "back"]
    with fitz.open(pdf) as doc:
        for i, page in enumerate(doc):
            key = f"page-{i+1:02d}"
            pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6))
            images[key] = (
                "data:image/jpeg;base64," + base64.b64encode(pix.tobytes("jpeg", jpg_quality=89)).decode()
            )
            links = []
            for annotation in page.get_links():
                if annotation.get("uri"):
                    r = annotation["from"]
                    links.append(
                        {
                            "url": annotation["uri"],
                            "rect": [r.x0 / width, r.y0 / height, r.width / width, r.height / height],
                        }
                    )
            slides.append(
                {
                    "id": key,
                    "label": labels[i],
                    "number": i + 1,
                    "image": key,
                    "kind": kinds[i],
                    "steps": [1, 2, 3, 4] if i == 2 else [],
                    "links": links,
                }
            )
    payload = {
        "slides": slides,
        "images": images,
        "start": "page-03",
        "layout": "a4-landscape-four-step",
        "paper_mm": [297, 210],
        "step_count": 4,
    }
    template = (source / "assembly_page_viewer.html").read_text(encoding="utf-8")
    html = template.replace("__TITLE__", f"{title} | {PROJECT_TITLE}").replace(
        "__PROJECT_URL__", "../README.md"
    )
    (folder / "assembly_instructions.html").write_text(
        html.replace("__DATA__", json.dumps(payload)), encoding="utf-8"
    )


def main(**kwargs):
    root = Path(kwargs.get("root", Path(__file__).resolve().parent))
    source_catalogue(root=root)
    for mounting in get_mountings():
        book(root=root, records=kwargs["records"], mounting=mounting)
