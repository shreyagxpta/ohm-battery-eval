"""Turn raw NASA .mat files into one tidy table: one row per discharge step.
Robust to file ordering: we sort by timestamp, we don't trust the file's order."""
import numpy as np
import pandas as pd
from scipy.io import loadmat


def _timestamp(cyc):
    """Pull a step's wall-clock start time as a comparable Timestamp."""
    y, mo, d, h, mi, s = np.ravel(cyc["time"])[:6]
    return pd.Timestamp(int(y), int(mo), int(d), int(h), int(mi), int(s))


def load_cells(paths):
    """
    paths: dict of {cell_id: path_to_mat}
    returns: DataFrame, one row per discharge step across all cells.
    """
    rows = []
    for cell_id, path in paths.items():
        mat = loadmat(path, simplify_cells=True)
        cycles = mat[cell_id]["cycle"]

        # Keep only discharge steps, each paired with its timestamp, then sort by time.
        # Now we depend on the timestamp, not on the file's storage order.
        discharge = [(_timestamp(c), c) for c in cycles if c["type"] == "discharge"]
        discharge.sort(key=lambda pair: pair[0])

        nominal = None
        for step_num, (ts, cyc) in enumerate(discharge, start=1):   # NEW: step_num from enumerate
            data = cyc["data"]

            capacity = float(np.ravel(data["Capacity"])[0])
            if nominal is None:                 # first = earliest, now guaranteed by the sort
                nominal = capacity

            v = np.ravel(data["Voltage_measured"]).astype(float)
            t = np.ravel(data["Temperature_measured"]).astype(float)

            rows.append({
                "cell_id": cell_id,
                "cycle": step_num,
                "timestamp": ts,                # useful later for time-ordered splits
                "capacity_ah": capacity,
                "nominal_capacity": nominal,
                "v_mean": v.mean(),
                "v_min": v.min(),
                "temp_max": t.max(),
            })

    df = pd.DataFrame(rows)
    df["soh"] = df["capacity_ah"] / df["nominal_capacity"]
    return df