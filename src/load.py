"""Loaders for the NSF OCE-1736668 South SF Bay dataset (NonVectrinoData subset).

All times are converted from MATLAB datenum to pandas Timestamps (naive; the
README does not state a time zone, so none is assumed).
"""
from pathlib import Path
import re

import numpy as np
import pandas as pd
import scipy.io as sio

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "Data" / "NonVectrinoData"
SEASONS = ("Summer", "Winter", "Spring")
CTD_PLATFORMS = {"Summer": ("P1", "P2", "P3", "P4a"),
                 "Winter": ("P1", "P2", "P3", "P4b"),
                 "Spring": ("P1", "P2", "P3", "P4b")}

# MATLAB datenum 719529 == 1970-01-01
MATLAB_UNIX_EPOCH = 719529.0


def datenum_to_datetime(dn):
    dn = np.asarray(dn, dtype=float)
    return pd.to_datetime((dn - MATLAB_UNIX_EPOCH) * 86400.0, unit="s")


def loadmat(path):
    """scipy.io.loadmat, falling back to h5py for v7.3 files. Drops __meta__ keys."""
    try:
        d = sio.loadmat(path, squeeze_me=True)
        return {k: v for k, v in d.items() if not k.startswith("__")}
    except NotImplementedError:  # v7.3 (HDF5)
        import h5py
        with h5py.File(path, "r") as f:
            return {k: np.array(f[k]).T.squeeze() for k in f.keys()}


def lisst_path(season):
    return DATA / "LISST" / season / "P2" / "lisst.mat"


def ctd_path(season, platform):
    return DATA / "CTD" / season / platform / "ctd.mat"


def adv_files(season, platform="P2", height=15):
    """All burst files for a season, sorted by integer index (index is NOT time)."""
    d = DATA / "ADV" / season / platform
    pat = re.compile(rf"adv{height}_(\d+)\.mat$")
    files = [(int(m.group(1)), p) for p in d.glob(f"adv{height}_*.mat")
             if (m := pat.search(p.name))]
    return [p for _, p in sorted(files)]


def load_lisst(season):
    d = loadmat(lisst_path(season))
    d["datetime"] = datenum_to_datetime(d["time"])
    return d


def load_ctd(season, platform):
    d = loadmat(ctd_path(season, platform))
    d["datetime"] = datenum_to_datetime(d["time"])
    return d


def load_adv_burst(path):
    d = loadmat(path)
    d["tstart_dt"] = datenum_to_datetime(d["tstart"])
    return d
