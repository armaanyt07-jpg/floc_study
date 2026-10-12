"""Inspect one file of each type: keys, shapes, time ranges, NaN fractions and overlap."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import load  # noqa: E402


def describe(d, skip=("datetime", "tstart_dt")):
    for k, v in d.items():
        if k in skip:
            continue
        a = np.asarray(v)
        line = f"    {k:10s} shape={str(a.shape):14s} dtype={str(a.dtype):8s}"
        if np.issubdtype(a.dtype, np.number) and a.size:
            af = a.astype(float)
            nan = np.isnan(af).mean()
            fin = af[np.isfinite(af)]
            rng = f"[{fin.min():.4g}, {fin.max():.4g}]" if fin.size else "[all NaN]"
            line += f" NaN={nan:6.2%} range={rng}"
        print(line)


def section(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


ranges = {}

section("LISST (P2, 35 cmab)")
for s in load.SEASONS:
    d = load.load_lisst(s)
    dt = d["datetime"]
    dts = np.diff(d["time"]) * 86400
    print(f"\n  {s}: {load.lisst_path(s).relative_to(load.ROOT)}")
    describe(d)
    print(f"    time: {dt.min()} -> {dt.max()}  n={len(dt)}  "
          f"median dt={np.median(dts):.1f}s  gaps>5min={np.sum(dts > 300)}")
    ranges[(s, "LISST")] = (dt.min(), dt.max())
    if s == "Summer":
        print(f"    dias (um): {np.array2string(d['dias'], precision=2, max_line_width=120)}")

section("CTD (all platforms)")
for s in load.SEASONS:
    for p in load.CTD_PLATFORMS[s]:
        d = load.load_ctd(s, p)
        dt = d["datetime"]
        print(f"\n  {s} {p}:")
        describe(d)
        print(f"    time: {dt.min()} -> {dt.max()}  n={len(dt)}  "
              f"median dt={np.median(np.diff(d['time'])) * 86400:.1f}s")
        ranges[(s, f"CTD {p}")] = (dt.min(), dt.max())

section("ADV 15 cmab, P2")
for s in load.SEASONS:
    files = load.adv_files(s)
    first = load.load_adv_burst(files[0])
    if s == "Summer":
        print(f"\n  Example burst {files[0].relative_to(load.ROOT)}:")
        describe(first)
        n = len(np.atleast_1d(first["velmaj"]))
        print(f"    samples/burst={n}  -> {n / 8 / 60:.2f} min at 8 Hz")
    # scan tstart of every burst (index != time)
    rows = []
    for f in files:
        b = load.load_adv_burst(f)
        vm = np.asarray(b["velmaj"], float)
        corr = np.vstack([np.asarray(b[f"corr{i}"], float) for i in (1, 2, 3)])
        rows.append(dict(file=f.name, tstart=float(b["tstart"]), n=vm.size,
                         nan_vel=np.isnan(vm).mean(),
                         frac_corr_lt30=(corr.min(0) < 30).mean(),
                         theta=float(b["theta"])))
    df = pd.DataFrame(rows)
    df["t"] = load.datenum_to_datetime(df["tstart"])
    df = df.sort_values("t")
    dts = df["t"].diff().dt.total_seconds() / 60
    print(f"\n  {s}: {len(df)} bursts  {df.t.min()} -> {df.t.max()}")
    print(f"    tstart minute-of-hour: {df.t.dt.minute.value_counts().head(5).to_dict()}")
    print(f"    samples/burst: {df.n.value_counts().head(3).to_dict()}")
    print(f"    burst spacing (min): median={dts.median():.1f}, >61 min gaps={int((dts > 61).sum())}, "
          f"duplicates={int((dts == 0).sum())}")
    print(f"    file index monotonic in time? {df.file.str.extract(r'_(\d+)')[0].astype(int).is_monotonic_increasing}")
    print(f"    velmaj NaN frac: mean={df.nan_vel.mean():.3%} max={df.nan_vel.max():.3%}")
    print(f"    frac samples with min(corr)<30: mean={df.frac_corr_lt30.mean():.3%} "
          f"max={df.frac_corr_lt30.max():.3%}  bursts>10%: {int((df.frac_corr_lt30 > .1).sum())}")
    print(f"    theta (deg): unique={np.unique(df.theta.round(2))[:5]}")
    ranges[(s, "ADV P2")] = (df.t.min(), df.t.max() + pd.Timedelta(minutes=14))

section("Time-range overlap per season")
for s in load.SEASONS:
    keys = [k for k in ranges if k[0] == s]
    lo = max(ranges[k][0] for k in keys if k[1] in ("LISST", "ADV P2", "CTD P1", "CTD P2"))
    hi = min(ranges[k][1] for k in keys if k[1] in ("LISST", "ADV P2", "CTD P1", "CTD P2"))
    print(f"\n  {s}:")
    for k in keys:
        print(f"    {k[1]:8s} {ranges[k][0]} -> {ranges[k][1]}")
    print(f"    COMMON (LISST, ADV P2, CTD P1, CTD P2): {lo} -> {hi}  "
          f"({(hi - lo).total_seconds() / 86400:.1f} days)")
