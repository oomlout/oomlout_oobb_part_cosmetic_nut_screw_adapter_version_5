"""Regenerate the complete catalogue from the editable populate definitions."""

from pathlib import Path

import working_navigation
import working_basic_set
import working_oomp
import working_oomp_populate
import working_scad
import working_render
import working_manual
import working_validate


def main(**kwargs):
    kwargs.setdefault("root", Path(__file__).resolve().parent)

    options = working_oomp_populate.main(**kwargs)
    records = working_oomp.main(options=options, **kwargs)
    working_scad.main(records=records, **kwargs)
    for mounting in ("to_flat", "to_m6"):
        working_basic_set.main(records=records, mounting=mounting, **kwargs)
    working_render.main(records=records, **kwargs)
    working_manual.main(records=records, **kwargs)
    working_navigation.main(records=records, **kwargs)
    working_validate.main(records=records, **kwargs)
    print(f"Validated {len(records)} catalogue entries, both P1S plates and both assembly guides.")


if __name__ == "__main__":
    main()
