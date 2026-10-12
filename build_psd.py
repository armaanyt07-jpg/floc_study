"""Cache the burst-averaged LISST size distribution (all 32 bins) for every burst.

    ven/bin/python build_psd.py

Needs the LISST files in Data/ (download_data.py ... --lisst-only fetches just those)
and outputs/cache/features.parquet (for the burst start times). The LISST QC and
burst averaging are the same as in build_features.py (src/features.py), so the mean
diameter of each cached curve equals d_mean in the feature table; this is checked
at the end.

Writes outputs/cache/psd_bins.parquet (season, tstart, b00..b31 in ul/l) and
outputs/cache/psd_dias.json (bin centre diameters, um).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import features, load, models as M, psd  # noqa: E402

feat = M.load_table()
tables, dias = [], None
for season in load.SEASONS:
    lm, P, d = features.lisst_minutes(season)
    if dias is not None and not np.allclose(d, dias):
        raise ValueError(f"{season}: LISST bin diameters differ from the previous season")
    dias = np.asarray(d, float)
    lm = lm.set_index("t")
    okpsd = pd.DataFrame(P, index=lm.index)
    rows = []
    for t0 in feat.loc[feat.season == season, "tstart"]:
        win = lm[t0:t0 + features.BURST]
        good = win[win.ok]
        if len(good) >= features.MIN_LISST_PER_BURST:
            rows.append(np.nanmean(okpsd.loc[good.index].to_numpy(), 0))
        else:
            rows.append(np.full(len(dias), np.nan))
    t = pd.DataFrame(np.vstack(rows), columns=psd.bin_cols(len(dias)))
    t.insert(0, "tstart", feat.loc[feat.season == season, "tstart"].to_numpy())
    t.insert(0, "season", season)
    tables.append(t)
    print(f"[{season}] {t[psd.bin_cols(len(dias))].notna().any(axis=1).sum()} / {len(t)} "
          "bursts with a size curve")

table = pd.concat(tables, ignore_index=True)
psd.save_psd(table, dias)

# Consistency check against the feature table
chk = feat.merge(table, on=["season", "tstart"]).dropna(subset=["d_mean"])
F = psd.volume_fractions(chk[psd.bin_cols(len(dias))].to_numpy())
err = np.abs(psd.mean_diameter(F, dias) - chk.d_mean.to_numpy())
print(f"\nBin diameters: {dias[0]:.2f} to {dias[-1]:.1f} um ({len(dias)} bins)")
print(f"Mean diameter from cached curves vs d_mean in features.parquet: "
      f"max difference {err.max():.2e} um over {len(chk)} bursts")
if err.max() > 1e-6:
    raise SystemExit("Mismatch with features.parquet: rebuild it with build_features.py")
print(f"Saved -> {psd.PSD_CACHE.relative_to(load.ROOT)} and "
      f"{psd.DIAS_CACHE.relative_to(load.ROOT)}")
