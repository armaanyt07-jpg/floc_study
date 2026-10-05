"""Tasks 2-4: build the one-row-per-burst feature table and cache it."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import features, load  # noqa: E402

OUT = load.ROOT / "outputs"
(OUT / "cache").mkdir(parents=True, exist_ok=True)
(OUT / "tables").mkdir(parents=True, exist_ok=True)

df = pd.concat([features.build_season(s) for s in load.SEASONS], ignore_index=True)
df.to_parquet(OUT / "cache" / "features.parquet")
df.to_csv(OUT / "cache" / "features.csv", index=False)

qc = features.qc_table(df)
qc.to_csv(OUT / "tables" / "qc_counts.csv", index=False)
pd.set_option("display.width", 200, "display.max_columns", 40)
print("\nQC row counts per step:\n", qc.to_string(index=False))

ok = df[(df.qc_adv == "ok") & df.d_mean.notna()]
cols = ["d_mean", "d50", "sigma2", "u_b", "u_b_lwt", "u_bar", "u_bar_4", "epsilon",
        "eps_slope", "T", "T_P1", "S", "beam_c", "ampmean", "fp", "n_spikes"]
print("\nPer-season medians (QC'd rows):\n",
      ok.groupby("season", sort=False)[cols].median().T.round(4).to_string())

print("\nChecks:")
for s, g in ok.groupby("season", sort=False):
    r_lwt = g[["u_b", "u_b_lwt"]].corr().iloc[0, 1]
    ratio = (g.u_b_lwt / g.u_b).median()
    # flood sign: depth rising <=> u_bar > 0 expected
    dh = g.set_index("hour").depth_P1.diff().reindex(g.hour).to_numpy()
    r_flood = pd.Series(dh).corr(pd.Series(g.u_bar.to_numpy()))
    r_ub_d = g[["u_b", "d_mean"]].corr().iloc[0, 1]
    r_u4_d = g[["u_bar_4", "d_mean"]].corr().iloc[0, 1]
    eps_ok = g.eps_slope.between(-2.2, -1.1).mean()
    r_T = g[["T", "T_P1"]].corr().iloc[0, 1]
    print(f"  {s}: u_b vs LWT r={r_lwt:.3f}, median LWT/spectral={ratio:.2f} | "
          f"corr(dh/dt, u_bar)={r_flood:.2f} | corr(u_b,d)={r_ub_d:.2f}, "
          f"corr(u_bar_4,d)={r_u4_d:.2f} | eps slope in [-2.2,-1.1]: {eps_ok:.0%} | "
          f"corr(T_P2,T_P1)={r_T:.2f}")
print(f"\nSaved {len(df)} rows -> outputs/cache/features.parquet (+ .csv)")
