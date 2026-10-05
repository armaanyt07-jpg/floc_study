"""Target and feature construction, one row per 15-cmab ADV burst at P2.

Method notes (see Egan et al. 2022, JGR Oceans, "EGAN22"):
- Target d_f: volume-weighted mean diameter of the LISST PSD after removing
  scintillation spikes (>=40% jump between consecutive bins within the five
  smallest / five largest bins), EGAN22 Sec. 2.2.
- u_bar: burst mean of velmaj (principal tidal axis), positive = flood,
  EGAN22 Sec. 3.2 / Fig. 2. u_bar_4: u_bar of the burst 4 h earlier.
- u_b: EGAN22 defers to earlier papers; here u_b = sqrt(2 * wave-band variance
  of the horizontal velocity), wave band set from the ADV pressure spectrum.
- epsilon: inertial-subrange fit of the vertical-velocity spectrum
  (simplified Feddersen et al. 2007, see eps_inertial()).
- Regime: EGAN22 Sec. 3.2 (forward-looking 12-h windows, 1.2x r^2 ratio).
"""
import numpy as np
import pandas as pd
from scipy import signal

from . import load

FS = 8.0                  # ADV sampling rate (Hz)
BURST = pd.Timedelta(minutes=14)
TAU_MIN = 0.10            # LISST optical transmission threshold (user decision)
TAU_FLAG = 0.30           # flag (not drop) 0.10 <= tau < 0.30
ADV_MAX_NAN = 0.10        # drop bursts with >10% NaN (corr<30) samples
MIN_LISST_PER_BURST = 7   # of ~14 one-minute LISST samples in the burst window
CLEANING = pd.to_datetime(["2018-07-25", "2018-08-01", "2019-01-24",
                           "2019-04-29", "2019-05-07"])
FOUL_DAYS = 3.0           # flag bursts within 3 days before a cleaning (assumption)
G = 9.81


# --------------------------------------------------------------------------
# LISST target
# --------------------------------------------------------------------------
def remove_scintillation(psd, frac=0.40, nedge=5):
    """NaN out isolated spike bins at the PSD edges (EGAN22 Sec. 2.2).

    A "spike" is read as an isolated jump: a bin within the 5 smallest or
    5 largest bins that is >=40% larger than BOTH neighbours. The outermost
    bin (one neighbour) is a spike if it is >=40% larger than its neighbour
    while that neighbour is NOT itself rising by >=40% (an abrupt kink, not
    a smoothly rising tail). Only the spiking bin is removed.

    (v1 removed the spiking bin and the whole tail beyond it; that clipped
    real coarse flocs in 39%/65% of Summer/Spring minutes and gave medians
    far below EGAN22 Fig. 1, so it was replaced. v1 outputs are archived in
    outputs/archive_v1_tailclip/.)
    Returns cleaned copy and per-row count of removed bins.
    """
    p0 = psd
    p = psd.copy()
    nb = p.shape[1]
    k = 1 + frac
    flag = np.zeros_like(p, bool)
    edge = list(range(nedge)) + list(range(nb - nedge, nb))
    for i in edge:
        if 0 < i < nb - 1:
            flag[:, i] = (p0[:, i] >= k * p0[:, i - 1]) & (p0[:, i] >= k * p0[:, i + 1])
        elif i == nb - 1:
            flag[:, i] = (p0[:, i] >= k * p0[:, i - 1]) & ~(p0[:, i - 1] >= k * p0[:, i - 2])
        else:  # i == 0
            flag[:, i] = (p0[:, 0] >= k * p0[:, 1]) & ~(p0[:, 1] >= k * p0[:, 2])
    p[flag] = np.nan
    return p, flag.sum(1)


def psd_stats(psd, dias):
    """Volume-weighted mean diameter, d50 and variance of d, per row."""
    v = np.where(np.isnan(psd), 0.0, psd)
    vt = v.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        dmean = (v * dias).sum(1) / vt
        var = (v * (dias - dmean[:, None]) ** 2).sum(1) / vt
        cum = np.cumsum(v, 1) / vt[:, None]
    logd = np.log(dias)
    d50 = np.full(len(v), np.nan)
    for r in np.where(vt > 0)[0]:
        d50[r] = np.exp(np.interp(0.5, cum[r], logd))
    return dmean, d50, var, vt


def lisst_minutes(season):
    """Per-minute QC'd LISST table."""
    d = load.load_lisst(season)
    psd, nrem = remove_scintillation(d["psd"])
    df = pd.DataFrame({"t": d["datetime"], "tau": d["tau"], "beam_c": d["beam_c"],
                       "n_scint_bins": nrem})
    df["ok"] = (df.tau >= TAU_MIN) & ~np.isnan(d["psd"]).all(1)
    return df, psd, d["dias"]


# --------------------------------------------------------------------------
# ADV processing
# --------------------------------------------------------------------------
def interp_nans(x):
    x = np.asarray(x, float).copy()
    bad = np.isnan(x)
    if bad.any() and (~bad).sum() > 1:
        idx = np.arange(x.size)
        x[bad] = np.interp(idx[bad], idx[~bad], x[~bad])
    return x


def goring_nikora(x, max_iter=20):
    """Phase-space thresholding despike (Goring & Nikora 2002).

    Spikes are replaced by linear interpolation. Applied to x - median.
    Returns cleaned series and number of spikes replaced.
    """
    x = np.asarray(x, float).copy()
    n = x.size
    lam = np.sqrt(2 * np.log(n))
    total = np.zeros(n, bool)
    for _ in range(max_iter):
        u = x - np.median(x)
        du = np.gradient(u)
        d2u = np.gradient(du)
        s = [1.483 * np.median(np.abs(a - np.median(a))) for a in (u, du, d2u)]
        if min(s) == 0:
            break
        su, sdu, sd2u = (lam * v for v in s)
        th = np.arctan2(np.sum(u * d2u), np.sum(u ** 2))
        # ellipse in (u, d2u) plane rotated by th (GN02 eqs. 9-10)
        c, sn = np.cos(th), np.sin(th)
        a2 = (su ** 2 * c ** 2 - sd2u ** 2 * sn ** 2) / (c ** 4 - sn ** 4)
        b2 = (sd2u ** 2 * c ** 2 - su ** 2 * sn ** 2) / (c ** 4 - sn ** 4)
        out = ((u / su) ** 2 + (du / sdu) ** 2 > 1) | ((du / sdu) ** 2 + (d2u / sd2u) ** 2 > 1)
        if a2 > 0 and b2 > 0:
            xr = u * c + d2u * sn
            yr = -u * sn + d2u * c
            out |= (xr ** 2 / a2 + yr ** 2 / b2) > 1
        new = out & ~total
        if not new.any():
            break
        total |= out
        x[out] = np.nan
        x = interp_nans(x)
    return x, int(total.sum())


def welch(x, nperseg=512):
    return signal.welch(signal.detrend(x), fs=FS, window="hann", nperseg=nperseg,
                        noverlap=nperseg // 2)


def wavenumber(omega, h):
    """Linear dispersion omega^2 = g k tanh(k h), solved by Newton iteration."""
    k = omega ** 2 / G / np.sqrt(np.tanh(omega ** 2 * h / G))  # Eckart start
    for _ in range(50):
        f = G * k * np.tanh(k * h) - omega ** 2
        df = G * np.tanh(k * h) + G * k * h / np.cosh(k * h) ** 2
        k = k - f / df
    return k


def wave_band(fp):
    return max(0.05, 0.5 * fp), min(1.2, 2.0 * fp)


def eps_inertial(f, Sww, uh, band=(1.5, 3.5)):
    """TKE dissipation from the inertial subrange of S_ww (per Hz).

    Frozen turbulence: S_ww(f) = (24/55) a_K eps^(2/3) (U/2pi)^(2/3) f^(-5/3),
    a_K = 1.5. Following the spirit of Feddersen et al. (2007), the advection
    speed is not the mean current but the full instantaneous (mean + wave)
    horizontal velocity, entering as <|u_h|^(2/3)>. This is a simplification
    of Feddersen's 3-D integral (assumption, stated in the report).
    Returns eps (W/kg) and the fitted log-log slope (quality indicator).
    """
    m = (f >= band[0]) & (f <= band[1]) & (Sww > 0)
    if m.sum() < 5:
        return np.nan, np.nan
    slope = np.polyfit(np.log(f[m]), np.log(Sww[m]), 1)[0]
    adv = np.mean(np.abs(uh) ** (2 / 3))
    coef = (24 / 55) * 1.5 * (2 * np.pi) ** (-2 / 3) * adv
    eps23 = np.median(Sww[m] * f[m] ** (5 / 3)) / coef
    return eps23 ** 1.5, slope


def adv_burst_features(path, press_cal=None):
    """Features from one ADV burst. press_cal=(slope, intercept) maps the
    ADV 'press' units to water depth (m) for the linear-wave-theory check."""
    b = load.load_adv_burst(path)
    u, v, w = (np.asarray(b[k], float) for k in ("velmaj", "velmin", "velz"))
    corr = np.vstack([np.asarray(b[f"corr{i}"], float) for i in (1, 2, 3)])
    out = dict(file=path.name, tstart=b["tstart_dt"],
               nan_frac=float(np.isnan(u).mean()),
               corr_lt30_frac=float((corr.min(0) < 30).mean()),
               upwp=float(b["upwp"]), ampmean=float(np.nanmean(b["ampmean"])))
    if out["nan_frac"] > ADV_MAX_NAN:
        out["qc_adv"] = "nan>10%"
        return out
    out["qc_adv"] = "ok"
    u, v, w = (interp_nans(a) for a in (u, v, w))
    (u, nu), (v, nv), (w, nw) = (goring_nikora(a) for a in (u, v, w))
    out["n_spikes"] = nu + nv + nw
    out["u_bar"] = u.mean()
    out["v_bar"] = v.mean()
    out["speed_bar"] = np.hypot(u.mean(), v.mean())

    p = np.asarray(b["press"], float)
    out["press_nan_frac"] = float(np.isnan(p).mean())
    if out["press_nan_frac"] > ADV_MAX_NAN:
        # wave band is set from the pressure spectrum; without it, skip waves
        out["qc_adv"] = "press nan>10%"
        return out
    p = interp_nans(p)
    f, Spp = welch(p)
    _, Suu = welch(u)
    _, Svv = welch(v)
    _, Sww = welch(w)
    df = f[1] - f[0]
    sel = (f >= 0.08) & (f <= 1.0)
    fp = f[sel][np.argmax(Spp[sel])]
    lo, hi = wave_band(fp)
    wb = (f >= lo) & (f <= hi)
    out.update(fp=fp, f_lo=lo, f_hi=hi)
    out["u_b"] = np.sqrt(2 * np.sum(Suu[wb] + Svv[wb]) * df)

    if press_cal is not None:
        a, c = press_cal
        h = a * p.mean() + c
        om = 2 * np.pi * f[wb]
        k = wavenumber(om, h)
        Shh = a ** 2 * Spp[wb]                     # head spectrum (m^2/Hz)
        # co-located pressure and velocity: depth attenuation cancels,
        # u = (g k / omega) * head (sensor-height offset neglected)
        out["u_b_lwt"] = np.sqrt(2 * np.sum((G * k / om) ** 2 * Shh) * df)
        out["h_adv"] = h

    # wave/turbulence separation for epsilon: low-pass horizontal velocity
    bl, al = signal.butter(4, hi / (FS / 2))
    uh = np.hypot(signal.filtfilt(bl, al, u), signal.filtfilt(bl, al, v))
    out["epsilon"], out["eps_slope"] = eps_inertial(f, Sww, uh)
    return out


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------
def press_calibration(season):
    """Linear fit of CTD depth vs ADV press units (P2 CTD; P1 in Spring)."""
    plat = "P1" if season == "Spring" else "P2"
    ctd = load.load_ctd(season, plat)
    dep = pd.Series(ctd["depth"], index=ctd["datetime"])
    xs, ys = [], []
    for fpath in load.adv_files(season)[::5]:
        b = load.load_adv_burst(fpath)
        t0 = b["tstart_dt"]
        dd = dep[t0:t0 + BURST].mean()
        pp = np.asarray(b["press"], float)
        if np.isfinite(dd) and np.isfinite(pp).mean() > 0.9:
            xs.append(np.nanmean(pp))
            ys.append(dd)
    a, c = np.polyfit(xs, ys, 1)
    return a, c, plat, float(np.corrcoef(xs, ys)[0, 1])


def window_mean(series, t0):
    return series[t0:t0 + BURST].mean()


def regime_labels(df, window=pd.Timedelta(hours=12), min_pts=8, ratio=1.2):
    """EGAN22 Sec. 3.2: for each burst, regress c on u_b and c on u_bar_4 over
    bursts in [t, t+12h); R if r2_ub > 1.2 r2_u4, A if r2_u4 > 1.2 r2_ub, else M."""
    lab = pd.Series(pd.NA, index=df.index, dtype="object")
    r2b = pd.Series(np.nan, index=df.index)
    r2a = pd.Series(np.nan, index=df.index)
    t = df["tstart"]
    for i in df.index:
        m = (t >= t[i]) & (t < t[i] + window)
        sub = df.loc[m, ["beam_c", "u_b", "u_bar_4"]].dropna()
        if len(sub) < min_pts:
            continue
        rb = np.corrcoef(sub.beam_c, sub.u_b)[0, 1] ** 2
        ra = np.corrcoef(sub.beam_c, sub.u_bar_4)[0, 1] ** 2
        r2b[i], r2a[i] = rb, ra
        lab[i] = "R" if rb > ratio * ra else ("A" if ra > ratio * rb else "M")
    return lab, r2b, r2a


def build_season(season, log=print):
    a, c, plat, r = press_calibration(season)
    log(f"[{season}] ADV press -> depth: depth = {a:.4f}*press + {c:.3f} (CTD {plat}, r={r:.3f})")

    rows = [adv_burst_features(fp, (a, c)) for fp in load.adv_files(season)]
    df = pd.DataFrame(rows).sort_values("tstart").reset_index(drop=True)
    df.insert(0, "season", season)
    df["hour"] = df.tstart.dt.round("h")  # burst centre (top of the hour)

    # u_bar_4: match by timestamp (burst centre 4 h earlier), not file index
    ub = df.set_index("hour")["u_bar"]
    df["u_bar_4"] = df["hour"].sub(pd.Timedelta(hours=4)).map(ub)

    # LISST, burst-window averages over QC'd minutes
    lm, psd, dias = lisst_minutes(season)
    lm = lm.set_index("t")
    okpsd = pd.DataFrame(psd, index=lm.index)
    n_all, n_ok, beam_c, tau = [], [], [], []
    dmean, d50, var, vtot, nscint = [], [], [], [], []
    for t0 in df.tstart:
        win = lm[t0:t0 + BURST]
        good = win[win.ok]
        n_all.append(len(win)); n_ok.append(len(good))
        tau.append(win.tau.mean())
        if len(good) >= MIN_LISST_PER_BURST:
            P = okpsd.loc[good.index].to_numpy()
            # average PSD over the window (bins NaN'd by despiking ignored)
            pm = np.nanmean(P, 0)[None, :]
            dm, dd, vv, vt = psd_stats(pm, dias)
            dmean.append(dm[0]); d50.append(dd[0]); var.append(vv[0]); vtot.append(vt[0])
            beam_c.append(good.beam_c.mean()); nscint.append(good.n_scint_bins.mean())
        else:
            for L in (dmean, d50, var, vtot, beam_c, nscint):
                L.append(np.nan)
    df["lisst_n"], df["lisst_n_ok"], df["tau_mean"] = n_all, n_ok, tau
    df["d_mean"], df["d50"], df["sigma2"], df["vol_conc"] = dmean, d50, var, vtot
    df["beam_c"], df["scint_bins_mean"] = beam_c, nscint
    df["tau_flag_lt0p3"] = df.tau_mean < TAU_FLAG

    # CTD: T from P2 (co-located), S from P1 (P2 salinity unusable)
    ctd2 = load.load_ctd(season, "P2")
    ctd1 = load.load_ctd(season, "P1")
    T2 = pd.Series(ctd2["temp"], index=ctd2["datetime"])
    T1 = pd.Series(ctd1["temp"], index=ctd1["datetime"])
    S1 = pd.Series(ctd1["sal"], index=ctd1["datetime"])
    h1 = pd.Series(ctd1["depth"], index=ctd1["datetime"])
    df["T"] = [window_mean(T2, t) for t in df.tstart]
    df["T_P1"] = [window_mean(T1, t) for t in df.tstart]
    df["S"] = [window_mean(S1, t) for t in df.tstart]
    df["depth_P1"] = [window_mean(h1, t) for t in df.tstart]

    # biofouling: days until next cleaning
    nxt = [CLEANING[CLEANING > t] for t in df.tstart]
    df["days_to_cleaning"] = [((n[0] - t).total_seconds() / 86400) if len(n) else np.nan
                              for n, t in zip(nxt, df.tstart)]
    df["biofoul_flag"] = df.days_to_cleaning <= FOUL_DAYS

    lab, r2b, r2a = regime_labels(df)
    df["regime"], df["r2_c_ub"], df["r2_c_u4"] = lab, r2b, r2a
    return df


def qc_table(df):
    """Row counts at each QC step, per season."""
    steps = []
    for s, g in df.groupby("season", sort=False):
        n0 = len(g)
        g1 = g[g.qc_adv == "ok"]
        g2 = g1[g1.d_mean.notna()]
        g3 = g2[g2["T"].notna() & g2["S"].notna()]
        g4 = g3[g3.u_bar_4.notna()]
        steps.append(dict(season=s, bursts=n0, adv_ok=len(g1), lisst_ok=len(g2),
                          ctd_ok=len(g3), u_bar_4_ok=len(g4),
                          biofoul_flagged=int(g4.biofoul_flag.sum()),
                          tau_lt0p3_flagged=int(g4.tau_flag_lt0p3.sum()),
                          regime_R=int((g4.regime == "R").sum()),
                          regime_A=int((g4.regime == "A").sum()),
                          regime_M=int((g4.regime == "M").sum()),
                          regime_na=int(g4.regime.isna().sum())))
    return pd.DataFrame(steps)
