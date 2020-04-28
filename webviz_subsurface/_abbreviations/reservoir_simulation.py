import json
import pathlib
import warnings
from typing import Optional

import pandas as pd


_DATA_PATH = pathlib.Path(__file__).parent.absolute() / "abbreviation_data"

SIMULATION_VECTOR_TERMINOLOGY = json.loads(
    (_DATA_PATH / "reservoir_simulation_vectors.json").read_text()
)

RESERVOIR_SIMULATION_UNIT_TERMINOLOGY = json.loads(
    (_DATA_PATH / "reservoir_simulation_unit_terminology.json").read_text()
)


def simulation_unit_reformat(ecl_unit: str, unit_set: str = "METRIC") -> str:
    """Returns the simulation unit in a different, more human friendly, format if possible,
    otherwise returns the simulation unit.
    * `ecl_unit`: Reservoir simulation vector unit to reformat
    * `unit_set`: Currently only valid option is the default "METRIC" (defined as in Eclipse E100)
    """
    return RESERVOIR_SIMULATION_UNIT_TERMINOLOGY[unit_set].get(ecl_unit, ecl_unit)


def simulation_vector_base(vector: str) -> str:
    """Returns base name of simulation vector
    E.g. WOPR for WOPR:OP_1 and ROIP for ROIP_REG:1
    """
    return vector.split(":", 1)[0].split("_", 1)[0]


def simulation_vector_description(vector: str) -> str:
    """Returns a more human friendly description of the simulation vector if possible,
     otherwise returns the input as is.
    """
    [vector_name, node] = vector.split(":", 1) if ":" in vector else [vector, None]
    if len(vector_name) == 8:
        # Region vectors for other FIP regions than FIPNUM are written on a special form:
        # 8 signs, with the last 3 defining the region.
        # E.g.: For an array "FIPREG": ROIP is ROIP_REG, RPR is RPR__REG and ROIPL is ROIPLREG
        # Underscores _ are always used to fill
        [vector_base_name, fip] = [vector_name[0:5].rstrip("_"), vector_name[5:]]
        try:
            if SIMULATION_VECTOR_TERMINOLOGY[vector_base_name]["type"] == "region":
                vector_name = vector_base_name
            else:
                fip = None
        except KeyError:
            fip = None
    else:
        fip = None
    if vector_name in SIMULATION_VECTOR_TERMINOLOGY:
        metadata = SIMULATION_VECTOR_TERMINOLOGY[vector_name]
        description = metadata["description"]
        if node is not None:
            description += (
                f", {metadata['type'].replace('_', ' ')} {fip} {node}"
                if fip is not None
                else f", {metadata['type'].replace('_', ' ')} {node}"
            )
    else:
        description = vector_name
        warnings.warn(
            (
                f"Could not find description for vector {vector_name}. Consider adding"
                " it in the GitHub repo https://github.com/equinor/webviz-subsurface?"
            ),
            UserWarning,
        )

    return description


def historical_vector(
    vector: str,
    smry_meta: Optional[pd.DataFrame] = None,
    return_historical: Optional[bool] = True,
):
    """This function is trying to make a best guess on converting between historical and
    non-historical vector names.

    `vector`: An Eclipse-format vector string
    `smry_meta`: Note: Not activate avaiting https://github.com/equinor/libecl/issues/708
                 A pandas DataFrame with vector metadata on the format returned by
                 `load_smry_meta` in `../_datainput/fmu_input.py`. Here the field is_historical is
                 used to check if a vector is a historical vector.
    `return_historical`: If return_historical is `True`, the corresponding guessed historical
                         vector name is returned if the guessed vector is thought to be a
                         historical vector, else None is returned. If `False` the corresponding
                         non-historical vector name is returned, if the input vector is thought to
                         be a historical vector, else None is returned.
    """
    smry_meta = None  # Temp deactivation waiting on https://github.com/equinor/libecl/issues/708
    parts = vector.split(":", 1)
    if return_historical:
        parts[0] += "H"
        hist_vec = ":".join(parts)
        return (
            None
            if historical_vector(hist_vec, smry_meta=smry_meta, return_historical=False)
            is None
            else hist_vec
        )

    if smry_meta is None:
        if parts[0].endswith("H") and parts[0].startswith(("F", "G", "W")):
            parts[0] = parts[0][:-1]
            return ":".join(parts)
        return None

    try:
        is_hist = smry_meta.is_historical[vector]
    except KeyError:
        is_hist = False
    return parts[0][:-1] if is_hist else None