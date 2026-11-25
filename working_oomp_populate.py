"""Editable dimensions for the cosmetic adapters and their over-caps, in millimetres."""


def get_fasteners(**kwargs):
    # Dimensions from the original 12 mm, flat, 3dpr models.
    fasteners = []
    fasteners.append({
        "size": "m3",
        "fastener_type": "countersunk",
        "seat_depth": 1.9,
        "seat_radius": 3.6,
        "bore_radius": 1.8,
        "base_depth": 0,
    })
    fasteners.append({
        "size": "m3",
        "fastener_type": "nut",
        "seat_depth": 2.5,
        "seat_radius": 3.462,
        "bore_radius": 1.8,
        "base_depth": 2,
    })
    fasteners.append({
        "size": "m6",
        "fastener_type": "nut",
        "seat_depth": 5,
        "seat_radius": 5.91425,
        "bore_radius": 3.25,
        "base_depth": 2,
    })
    fasteners.append({
        "size": "m3_5",
        "fastener_type": "screw_wood",
        "seat_depth": 4.2,
        "seat_radius": 4.5,
        "bore_radius": 2.375,
        "base_depth": 0,
    })
    return fasteners


def main(**kwargs):
    adapter_diameter = kwargs.get("adapter_diameter", 12)
    wall_thickness = kwargs.get("wall_thickness", 1)
    roof_thickness = kwargs.get("roof_thickness", 1)
    fit_taper = kwargs.get("fit_taper", 0.075)

    sleeve_diameter = kwargs.get("sleeve_diameter", 5.75)
    parts = []
    for mounting in ("to_flat", "to_m6"):
        for fastener in get_fasteners(**kwargs):
            body_depth = fastener["seat_depth"] + fastener["base_depth"]
            sleeve_depth = 0
            if mounting == "to_m6" and 2 * fastener["bore_radius"] < sleeve_diameter:
                sleeve_depth = 1.5 if fastener["fastener_type"] == "nut" else 3
            adapter = {
                **fastener,
                "mounting": mounting,
                "oobb_type": "adapter",
                "diameter": adapter_diameter,
                "body_depth": body_depth,
                "sleeve_depth": sleeve_depth,
                "sleeve_diameter": sleeve_diameter,
                "depth": body_depth + sleeve_depth,
            }
            parts.append(adapter)

            cap = {
                "size": fastener["size"],
                "fastener_type": fastener["fastener_type"],
                "mounting": mounting,
                "oobb_type": "cap",
                "diameter": adapter_diameter + 2 * wall_thickness,
                "depth": body_depth + roof_thickness,
                "wall_thickness": wall_thickness,
                "roof_thickness": roof_thickness,
                "fit_taper": fit_taper,
            }
            parts.append(cap)
    return parts


def get_usage(**kwargs):
    """The selected OOMP full-detail examples and instructions for each pocket."""
    examples = {}
    examples[("m3", "countersunk")] = {
        "label": "M3 countersunk screw",
        "hardware": "hardware_screw_countersunk_pozidriv_bright_zinc_plated_m3_diameter_8_mm_length",
        "counterpart": "hardware_nut_m3",
        "seat": "Pass the countersunk screw through the conical seat. Back the plate’s clearance hole with a wide M3 washer and nut. Tighten until the head sits below the rim.",
    }
    examples[("m3", "nut")] = {
        "label": "M3 hex nut",
        "hardware": "hardware_nut_m3",
        "counterpart": "hardware_set_screw_m3_8_mm_length",
        "seat": "Align the nut flats with the pocket and press the nut onto its floor. Thread an M3 screw in from the reverse side. The illustrated 8 mm screw uses a 9 mm OD, 0.8 mm thick washer under its head on a 3 mm plate.",
    }
    examples[("m6", "nut")] = {
        "label": "M6 hex nut",
        "hardware": "hardware_nut_m6",
        "counterpart": "hardware_set_screw_m6_8_mm_length",
        "seat": "Seat the hex nut in the pocket and thread an M6 screw in from below. The pocket is 5 mm deep. The 5.2 mm example nut stands 0.2 mm proud and lifts the cap by that amount.",
    }
    examples[("m3_5", "screw_wood")] = {
        "label": "3.5 mm wood screw",
        "hardware": "hardware_screw_wood_pozidriv_net_coat_yellow_plated_m3_5_diameter_16_mm_length_screwtite_419fy",
        "counterpart": None,
        "seat": "Align the plate with a pilot hole in the timber. Drive the wood screw through the adapter into the timber until its head seats below the rim. Select the screw length for your backing.",
    }
    return examples


def assembly_steps(**kwargs):
    details = kwargs["details"]
    example = kwargs["example"]
    steps = []
    steps.append("Choose the adapter and cap for the same fastener. Check the screw length against the plate, adapter and available thread or backing.")
    if details["sleeve_depth"]:
        steps.append(f"Insert the {details['sleeve_diameter']:g} mm locating sleeve into the clearance hole until the flange touches the plate.")
    elif details["mounting"] == "to_m6":
        steps.append("Centre the adapter over the M6 clearance hole. On this nut seat the 6.5 mm through-bore leaves a flat underside.")
    else:
        steps.append("Centre the flat underside of the adapter over the hole, with the fastener pocket facing out.")
    steps.append(example["seat"])
    steps.append("Check that the fastener clears the underside of the cap roof. Press the cap over the flange with its open end toward the plate.")
    return steps


def get_mountings(**kwargs):
    mountings = {}
    mountings["to_flat"] = {
        "title": "To flat",
        "description": "A flat underside bears directly on the mounting surface. Centre the adapter by hand before tightening the fastener.",
        "locate": "Centre the adapter over the clearance hole with the conical seat facing up.",
    }
    mountings["to_m6"] = {
        "title": "To M6",
        "description": "A 5.75 mm locating sleeve enters an M6 clearance hole. It projects 3 mm on the two screw adapters and 1.5 mm on the M3 nut adapter. The M6 nut adapter has a flat underside because its 6.5 mm bore is wider than the sleeve.",
        "locate": "Lower the 3 mm sleeve into the M6 clearance hole until the flange rests on the plate.",
    }
    return mountings


def example_steps(**kwargs):
    mounting = kwargs["mounting"]
    steps = []
    steps.append(("Back the clearance hole", "Hold the 9 mm outside-diameter M3 washer and M3 nut under the centre hole of the plate."))
    steps.append(("Locate the adapter", get_mountings()[mounting]["locate"]))
    steps.append(("Seat the screw", "Pass the M3 x 8 mm countersunk screw through the adapter and washer. Engage the nut and tighten until the head is recessed."))
    steps.append(("Fit the cap", "Press the open end of the matching cap over the flange until its rim meets the plate."))
    return steps
