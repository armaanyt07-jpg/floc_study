"""Builds deliverables/Floc_Size_Prediction_Writeup.pdf (two pages, A4).

Run: ven/bin/python deliverables/source/build_writeup.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "deliverables" / "Floc_Size_Prediction_Writeup.pdf"

TEAL = colors.HexColor("#1F4E5F")
OCHRE = colors.HexColor("#B8732A")
INK = colors.HexColor("#1B2A33")
MUTED = colors.HexColor("#5E6B72")
LINE = colors.HexColor("#D3DDE0")

ss = getSampleStyleSheet()
H_TITLE = ParagraphStyle("t", parent=ss["Title"], fontName="Times-Bold", fontSize=17, leading=21,
                         textColor=TEAL, alignment=TA_LEFT, spaceAfter=2)
SUB = ParagraphStyle("s", fontName="Helvetica", fontSize=9.5, leading=12, textColor=MUTED, spaceAfter=6)
H = ParagraphStyle("h", fontName="Times-Bold", fontSize=13, leading=15, textColor=TEAL,
                   spaceBefore=8, spaceAfter=3)
B = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=13.2, textColor=INK, spaceAfter=3)
BUL = ParagraphStyle("bul", parent=B, leftIndent=10, bulletIndent=0, spaceAfter=1.5)
CELL = ParagraphStyle("c", fontName="Helvetica", fontSize=9, leading=11, textColor=INK)
CELLB = ParagraphStyle("cb", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
CODE = ParagraphStyle("code", fontName="Courier", fontSize=8.4, leading=10.5, textColor=INK,
                      leftIndent=10, spaceAfter=3)


def p(t, st=B):
    return Paragraph(t, st)


def bullets(items):
    return [Paragraph(t, BUL, bulletText="•") for t in items]


def table(rows, widths, head=True):
    data = [[Paragraph(c, CELLB if (head and i == 0) else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), TEAL))
    t.setStyle(TableStyle(style))
    return t


story = [
    p("Predicting Floc Size in South San Francisco Bay from Waves and Currents", H_TITLE),
    p("ML Mini Project write-up. A physics-only replication of Egan et al. (2022, JGR Oceans) and "
      "Egan's CS229 report, built on the public Stanford Digital Repository dataset.", SUB),

    p("1. Problem statement", H),
    p("Mud in estuaries travels as <b>flocs</b>: loose clumps of fine particles and organic matter. "
      "Floc size sets how fast mud sinks (settling speed grows with diameter squared), so it controls "
      "where sediment and attached pollutants end up. Sediment models need it, but it is rarely measured "
      "and varies about threefold within a season. <b>We ask: can floc size be predicted from wave and "
      "current measurements alone, and does the prediction hold on days and seasons the model has not seen?</b> "
      "This is a supervised regression task: tabular physical inputs, one continuous output (mean floc "
      "diameter in micrometres)."),

    p("2. Dataset", H),
    p("NSF OCE-1736668 field campaign (Stanford Digital Repository, purl wv787xr0534): three deployments "
      "of about four weeks (Summer 2018, Winter 2019, Spring 2019) on 2 m deep shoals. From the 2.5 GB "
      "archive we extracted only what was needed, using HTTP range requests."),
    table([
        ["Instrument", "Measures", "Rate", "Used for"],
        ["LISST laser sizer (P2, 35 cm above bed)", "Particle size distribution, 32 bins", "60 s", "Target d"],
        ["ADV current meter (P2, 15 cm)", "3D velocity, pressure", "8 Hz, 14 min/h", "Waves, tide, turbulence"],
        ["CTD sensors (P2, P1)", "Temperature, salinity", "60 s", "T, S"],
    ], [52 * mm, 48 * mm, 26 * mm, 42 * mm]),
    Spacer(1, 3),
    p("After quality control: <b>1,120 hourly samples</b> (Summer 427, Winter 406, Spring 287) from 1,666 "
      "bursts. Not available in this archive: the chlorophyll and light-absorption (biology) sensors both "
      "papers used. Data issues we found and documented: the ADV pressure is not in the units the README "
      "states, P2 salinity is unusable (P1 used instead), and low-quality ADV samples are NaN rather than "
      "interpolated."),

    p("3. Approach", H),
    *bullets([
        "<b>Target.</b> Average the 1-minute laser readings over each 14-minute ADV burst, drop saturated "
        "optics (transmission below 0.1), remove isolated edge-bin spikes (the paper's 40% rule) and take the "
        "volume-weighted mean diameter. Resulting medians (83, 62, 106 micrometres) match the paper's Fig. 1.",
        "<b>Features (6).</b> Wave orbital velocity u_b (from the velocity spectrum, cross-checked against "
        "linear wave theory, r = 0.95), tidal current now and 4 hours earlier, turbulence dissipation, "
        "temperature, salinity. Gaps are never filled; bad bursts are dropped.",
        "<b>Model.</b> A <b>Random Forest</b>, the model of the internal CS229 study, so results compare directly. "
        "It suits small, noisy, non-linear tabular data with mixed units, needs no scaling and reports feature "
        "importance. LASSO with recursive feature elimination (journal paper) and SVR (CS229) are run for comparison.",
        "<b>Evaluation.</b> Hourly floc size is strongly autocorrelated, so a random split lets the model see the "
        "neighbours of every test hour. We therefore report <b>time-blocked</b> cross-validation (contiguous "
        "multi-day blocks, 12 h gap) and <b>leave-one-season-out</b>, alongside each paper's own protocol. "
        "Metric: r² (1 = perfect, 0 = no better than the mean) with day-level bootstrap intervals and RMSE.",
    ]),
]

story_p2 = [
    p("4. Implementation overview", H),
    p("Python 3.12 with numpy, scipy, pandas, scikit-learn and matplotlib, in a project virtual environment. "
      "Raw MATLAB files are read with scipy.io.loadmat; the feature table is cached as Parquet so models run in "
      "seconds. Random seeds are fixed, so every number in this write-up is reproducible."),
    KeepTogether(table([
        ["File", "Role"],
        ["build_features.py", "Builds the one-row-per-burst feature table from the raw files (about 30 s)"],
        ["run_random_forest.py", "Main demo: trains the Random Forest and prints our scores next to both papers"],
        ["src/load.py, features.py", "Loading, time conversion, QC, spectra, despiking, target and features"],
        ["src/models.py, predict.py", "Time-blocked splits, LASSO/RF/SVR, scoring; single-row prediction with range checks"],
        ["scripts/", "All-model runs, figures, diagnostics; outputs/ holds tables, figures and the full report"],
    ], [48 * mm, 120 * mm])),
    Spacer(1, 3),
    p("Live demonstration (two commands):"),
    p("ven/bin/python build_features.py<br/>ven/bin/python run_random_forest.py", CODE),

    p("5. Results", H),
    table([
        ["Setup", "r² (ours)", "Reference"],
        ["Class-paper setup: all seasons, random 70/30, RF 32 trees, d50", "0.60", "CS229 reported 0.81"],
        ["Class-paper SVR (C = 2048, epsilon = 4), d50", "0.53", "CS229 reported 0.76"],
        ["Our 6 features, all seasons, random split", "0.64", "optimistic protocol"],
        ["Our 6 features, all seasons, held-out time blocks", "<b>0.34</b> (95% CI 0.15 to 0.49)", "honest estimate"],
        ["One season at a time, held-out time blocks", "below 0 (best -0.14)", "no skill within a season"],
        ["Predict an unseen season (leave-one-season-out)", "-0.1 to -4.6", "fails on new conditions"],
        ["LASSO fitted on its own data (journal protocol)", "0.17 to 0.29 per season, 0.43 pooled", "journal 0.15 to 0.65"],
    ], [86 * mm, 44 * mm, 38 * mm]),
    Spacer(1, 3),
    p("<b>What drives floc size.</b> Permutation importance ranks the tidal current 4 hours earlier first "
      "(positive effect) and wave velocity second (negative effect), matching the journal paper. Turbulence adds "
      "almost nothing and salinity is weak within a season, contrary to the CS229 report, which ranked salinity "
      "first. The model follows the tide-to-tide rhythm of floc size but misses multi-day shifts in the average."),
    Image(str(ROOT / "outputs" / "figures" / "rf_importance.png"), width=178 * mm, height=178 * mm * 450 / 1650),
    p("Figure: Random Forest permutation importance per season (drop in held-out r\u00b2 when a feature is "
      "shuffled; + / - shows the direction of its effect on floc size).", SUB),

    p("6. Conclusions", H),
    *bullets([
        "The physical relationships reported in the journal paper reproduce on independent public data: "
        "waves break flocs and the delayed tide brings larger ones.",
        "Physics alone explains about a third of floc-size variation across seasons (r² = 0.34) and little "
        "within a season. Measured the way each paper measured it, our scores sit close to theirs (0.60 vs 0.81; "
        "0.17 to 0.43 vs 0.15 to 0.65).",
        "The remaining gap has three causes: missing biology inputs (particle type, chlorophyll), the scoring "
        "method (random splits and in-sample fits reward memorising neighbouring hours) and the measurement "
        "location (35 cm at P2 vs 15 cm on the optics platform).",
        "For a model that lasts years, new data matters more than a new algorithm: biology and sediment sensors, "
        "more deployments, and occasional direct size measurements to re-anchor predictions. A next step is the "
        "same team's Dryad optics dataset, which adds the particle-type index at the same site.",
    ]),
]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(A4[0] - 16 * mm, 10 * mm, f"Page {doc.page} of 2")
    canvas.restoreState()


doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                        topMargin=14 * mm, bottomMargin=16 * mm,
                        title="Predicting floc size in South San Francisco Bay", author="ML Mini Project")
doc.build(story + story_p2, onFirstPage=footer, onLaterPages=footer)
print("wrote", OUT)
