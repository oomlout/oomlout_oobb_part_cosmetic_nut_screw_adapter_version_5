"""Materialize the populated options as OOMP records for downstream stages."""

from pathlib import Path

import yaml


def main(**kwargs):
    root = Path(kwargs.get("root", Path(__file__).parent))
    options = kwargs["options"]

    records = []
    for option in options:
        diameter = format(option["diameter"], "g").replace(".", "_")
        depth = format(option["depth"], "g").replace(".", "_")
        taxonomy = {
            "taxonomy_1": "oobb",
            "taxonomy_2": "part",
            "taxonomy_3": "cosmetic",
            "taxonomy_4": option["oobb_type"],
            "taxonomy_5": option["size"],
            "taxonomy_6": option["fastener_type"],
            "taxonomy_7": f"{diameter}_mm_diameter",
            "taxonomy_8": f"{depth}_mm_depth",
            "taxonomy_9": option["mounting"],
        }
        record = {
            **taxonomy,
            "oomp_id": "_".join(taxonomy.values()),
            "oobb_details": option,
        }
        for directory in ("parts_source", "parts"):
            folder = root / directory / record["oomp_id"]
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "working.yaml").write_text(
                yaml.safe_dump(record, sort_keys=False), encoding="utf-8", newline="\n"
            )
        records.append(record)
    return records
