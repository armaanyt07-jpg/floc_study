// Builds deliverables/Floc_Size_Prediction_Slides.pptx
// Run: node deliverables/source/build_slides.js [theme-helper.js]
// Requires pptxgenjs (npm install pptxgenjs). The optional helper writes the colour theme into the file.
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(ROOT, "deliverables", "Floc_Size_Prediction_Slides.pptx");
const FIG = path.join(ROOT, "outputs", "figures");
const APPLY_THEME = process.argv[2];

const THEME = {
  name: "Estuary",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2A33", lt1: "FFFFFF", dk2: "1F4E5F", lt2: "EEF3F4",
    accent1: "1F4E5F", accent2: "B8732A", accent3: "6B8F71", accent4: "8A6E5A",
    accent5: "5C7A89", accent6: "A23B3B", hlink: "1F4E5F", folHlink: "5C7A89",
  },
};
// hex copies for hex-only options (chart grid lines etc.)
const HEX = { text: "1B2A33", teal: "1F4E5F", ochre: "B8732A", line: "D3DDE0", muted: "5E6B72", sage: "6B8F71" };

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Predicting floc size in South San Francisco Bay";
pres.author = "ML Mini Project, Team 7";
const C = pres.SchemeColor;

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 1.35, w: 8.8, h: 1.5,
      fontFace: THEME.headFontFace, fontSize: 36, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 },
      text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 3.05, w: 8.8, h: 1.2,
      fontFace: THEME.bodyFontFace, fontSize: 18, color: C.background2, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.75,
      fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.text2, valign: "middle", align: "left", margin: 0 },
      text: "" } },
  ],
  slideNumber: { x: 9.0, y: 5.2, w: 0.5, h: 0.3, fontFace: THEME.bodyFontFace, fontSize: 10, color: C.accent5, align: "right" },
});
pres.defineSlideMaster({
  title: "CLOSING_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.75,
      fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.background1, valign: "middle", align: "left", margin: 0 },
      text: "" } },
  ],
  slideNumber: { x: 9.0, y: 5.2, w: 0.5, h: 0.3, fontFace: THEME.bodyFontFace, fontSize: 10, color: C.background2, align: "right" },
});

// ---------------------------------------------------------------- helpers
function card(slide, x, y, w, h, name) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, rectRadius: 0.08, fill: { color: C.background1 },
    line: { color: HEX.line, width: 1 }, objectName: name,
  });
}
function badge(slide, x, y, label, name, color) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: 0.42, h: 0.42, fill: { color: color || C.accent2 },
    line: { color: color || C.accent2, width: 0 }, objectName: name });
  slide.addText(label, { x, y, w: 0.42, h: 0.42, isTextBox: true, align: "center", valign: "middle",
    fontSize: 14, bold: true, color: C.background1, margin: 0, objectName: name + " label" });
}
function text(slide, runs, opts) {
  slide.addText(runs, Object.assign({ isTextBox: true, fontSize: 14, color: C.text1, valign: "top",
    margin: 0, paraSpaceAfter: 4 }, opts));
}
function bullets(items, size) {
  return items.map((t, i) => ({ text: t, options: { bullet: { indent: 14 }, fontSize: size || 14,
    breakLine: i < items.length - 1, paraSpaceAfter: 6 } }));
}

function barChart(slide, o) {
  // Shape-drawn horizontal bars: render the same in PowerPoint, Keynote and Google Slides.
  // o: {x, y, w, h, items:[[label, value]], min, max, color, colors, title, labelW, fmt, name}
  const labelW = o.labelW, valW = 0.55, top = o.y + 0.4;
  const plotX = o.x + labelW + 0.1, plotW = o.w - labelW - 0.1 - valW;
  const rowH = (o.h - 0.4) / o.items.length;
  const sx = (v) => plotX + (v - o.min) / (o.max - o.min) * plotW;
  text(slide, o.title, { x: o.x, y: o.y, w: o.w, h: 0.3, fontSize: 12, bold: true, color: C.text2 });
  slide.addShape(pres.shapes.LINE, { x: sx(0), y: top, w: 0, h: rowH * o.items.length,
    line: { color: HEX.muted, width: 1 }, objectName: o.name + " zero line" });
  o.items.forEach(([lab, v], i) => {
    const y = top + i * rowH, bh = Math.min(0.36, rowH * 0.6), by = y + (rowH - bh) / 2;
    text(slide, lab, { x: o.x, y: y, w: labelW, h: rowH, fontSize: 12, valign: "middle", align: "right" });
    const x0 = Math.min(sx(0), sx(v)), bw = Math.max(Math.abs(sx(v) - sx(0)), 0.02);
    const col = (o.colors && o.colors[i]) || o.color;
    slide.addShape(pres.shapes.RECTANGLE, { x: x0, y: by, w: bw, h: bh, fill: { color: col },
      line: { color: col, width: 0 }, objectName: `${o.name} bar ${i + 1}` });
    const vx = v >= 0 ? sx(v) + 0.06 : sx(0) + 0.06;
    text(slide, o.fmt(v), { x: vx, y: y, w: valW, h: rowH, fontSize: 12, bold: true, valign: "middle" });
  });
}
function content(title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}

// ================================================================ 1. Title
pres.addSection({ title: "Introduction" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Introduction" });
s.addText("Predicting Floc Size in South San Francisco Bay", { placeholder: "title" });
s.addText([
  { text: "Can waves and currents alone tell us how big suspended mud particles are?", options: { breakLine: true } },
  { text: "A physics-only replication of Egan et al. (2022) and Egan's CS229 study", options: { fontSize: 14, breakLine: true } },
  { text: "ML Mini Project, Team 7", options: { fontSize: 14, bold: true } },
], { placeholder: "body" });

// ================================================================ 2. Problem statement
s = content("Problem statement", "Introduction");
card(s, 0.5, 1.3, 4.1, 3.7, "Question card");
text(s, [
  { text: "The question", options: { fontSize: 13, bold: true, color: C.accent2, breakLine: true } },
  { text: "Can we predict the size of suspended mud flocs from wave and current measurements alone?",
    options: { fontFace: THEME.headFontFace, fontSize: 22, color: C.text2 } },
], { x: 0.8, y: 1.6, w: 3.5, h: 2.2 });
text(s, "Why physics only: biology sensors are costly, need frequent cleaning, and are not in the public dataset.",
  { x: 0.8, y: 3.95, w: 3.5, h: 0.9, fontSize: 13, color: HEX.muted });
const prob = [
  ["Input", "Hourly measurements of waves, tidal current, turbulence, temperature and salinity."],
  ["Output", "Mean floc diameter d (micrometres), measured by a laser particle sizer (LISST)."],
  ["Test", "Does the model still work on days, and seasons, it has never seen?"],
];
prob.forEach(([h, b], i) => {
  const y = 1.35 + i * 1.22;
  badge(s, 5.0, y, String(i + 1), "Problem badge " + (i + 1));
  text(s, [{ text: h, options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
           { text: b, options: { fontSize: 14 } }], { x: 5.6, y: y - 0.02, w: 3.9, h: 1.05 });
});

// ================================================================ 3. Motivation
pres.addSection({ title: "Background" });
s = content("Why floc size matters", "Background");
const mot = [
  ["Settling speed", "Bigger flocs sink faster. Speed grows with diameter squared, so a 2x error in size is a 4x error in settling speed."],
  ["Coasts and ports", "Sediment models guide dredging, marsh restoration and sea-level defences. They need a settling speed that is rarely measured."],
  ["Pollutants and ecology", "Contaminants and algae travel on flocs, so floc size decides where they end up."],
];
mot.forEach(([h, b], i) => {
  const x = 0.5 + i * 3.07;
  card(s, x, 1.3, 2.86, 2.75, "Motivation card " + (i + 1));
  badge(s, x + 0.25, 1.52, String(i + 1), "Motivation badge " + (i + 1));
  text(s, [{ text: h, options: { bold: true, fontSize: 16, color: C.text2, breakLine: true } },
           { text: b, options: { fontSize: 14 } }], { x: x + 0.25, y: 2.08, w: 2.4, h: 1.9 });
});
text(s, [{ text: "The problem: ", options: { bold: true, color: C.accent2 } },
  { text: "most models assume one fixed floc size, yet our data shows it changes by about 3x within a single season." }],
  { x: 0.5, y: 4.3, w: 9.0, h: 0.6, fontSize: 15 });

// ================================================================ 4. Theory
s = content("How flocs grow and break", "Background");
const th = [
  ["Grow", "Particles collide and stick, helped by sticky biological 'glue' from algae. Calm water lets flocs grow.", C.accent3],
  ["Break", "Wave motion near the bed shears flocs apart. Stronger waves mean smaller flocs.", C.accent6],
  ["Arrive", "The tide carries flocs formed elsewhere. Here, water from upstream arrives about 4 hours later.", C.accent1],
];
th.forEach(([h, b, col], i) => {
  const y = 1.3 + i * 1.22;
  card(s, 0.5, y, 5.0, 1.08, "Theory card " + (i + 1));
  s.addShape(pres.shapes.OVAL, { x: 0.72, y: y + 0.3, w: 0.48, h: 0.48, fill: { color: col }, line: { color: col, width: 0 }, objectName: "Theory dot " + (i + 1) });
  text(s, [{ text: h, options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } },
           { text: b, options: { fontSize: 13 } }], { x: 1.42, y: y + 0.12, w: 3.9, h: 0.9 });
});
card(s, 5.8, 1.3, 3.7, 3.54, "Stokes card");
text(s, [{ text: "Settling speed (Stokes law)", options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } }],
  { x: 6.05, y: 1.5, w: 3.3, h: 0.4 });
text(s, [
  { text: "w", options: { fontSize: 22, fontFace: THEME.headFontFace } },
  { text: "s", options: { fontSize: 22, fontFace: THEME.headFontFace, subscript: true } },
  { text: " = (ρ", options: { fontSize: 22, fontFace: THEME.headFontFace } },
  { text: "f", options: { fontSize: 22, fontFace: THEME.headFontFace, subscript: true } },
  { text: " - ρ", options: { fontSize: 22, fontFace: THEME.headFontFace } },
  { text: "0", options: { fontSize: 22, fontFace: THEME.headFontFace, subscript: true } },
  { text: ") g d", options: { fontSize: 22, fontFace: THEME.headFontFace } },
  { text: "2", options: { fontSize: 22, fontFace: THEME.headFontFace, superscript: true } },
  { text: " / 18μ", options: { fontSize: 22, fontFace: THEME.headFontFace } },
], { x: 6.05, y: 2.0, w: 3.3, h: 0.55, color: C.text2 });
text(s, bullets([
  "d: floc diameter (what we predict)",
  "ρf, ρ0: floc and water density",
  "g: gravity,  μ: water viscosity",
  "Double d at the same density and it sinks 4x faster",
], 12), { x: 6.05, y: 2.75, w: 3.3, h: 1.9 });
text(s, "What theory predicts: strong waves give smaller flocs; strong tide 4 hours earlier brings larger ones.",
  { x: 0.5, y: 4.95, w: 8.3, h: 0.35, fontSize: 12, color: HEX.muted, italic: true });

// ================================================================ 5. Dataset
pres.addSection({ title: "Approach" });
s = content("The data: Stanford Digital Repository", "Approach");
text(s, bullets([
  "NSF OCE-1736668 field campaign on the shallow shoals (about 2 m deep) of South San Francisco Bay",
  "Three deployments of about four weeks: Summer 2018, Winter 2019, Spring 2019",
  "2.5 GB public archive; we used the laser sizer, the CTD and the 15 cm current meter at platform P2",
  "After cleaning: 1,120 hourly samples (Summer 427, Winter 406, Spring 287)",
], 14), { x: 0.5, y: 1.3, w: 3.9, h: 3.6 });
const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 }, fontSize: 12 } });
const cell = (t) => ({ text: t, options: { fontSize: 12, color: C.text1 } });
s.addTable([
  [hdr("Instrument"), hdr("What it measures"), hdr("How often")],
  [cell("LISST laser sizer, 35 cm above bed"), cell("Particle size distribution: our target d"), cell("Every 60 s")],
  [cell("ADV acoustic current meter, 15 cm"), cell("3D velocity and pressure: waves, tide, turbulence"), cell("8 per second, 14 min each hour")],
  [cell("CTD sensor"), cell("Temperature and salinity"), cell("Every 60 s")],
], { x: 4.7, y: 1.35, w: 4.8, colW: [1.55, 1.95, 1.3], border: { type: "solid", pt: 0.75, color: HEX.line },
  margin: 0.06, valign: "middle", objectName: "Instrument table" });
text(s, "Not in the archive: chlorophyll and light-absorption (biology) sensors used by both papers.",
  { x: 4.7, y: 4.35, w: 4.8, h: 0.6, fontSize: 12, color: HEX.muted, italic: true });

// ================================================================ 6. Methodology
s = content("From raw signals to a feature table", "Approach");
card(s, 0.5, 1.3, 3.3, 3.6, "Target card");
text(s, [{ text: "Target: floc size d", options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } }],
  { x: 0.72, y: 1.45, w: 2.9, h: 0.4 });
text(s, bullets([
  "Average the 1-minute laser readings over each 14-minute burst",
  "Drop readings where the optics are saturated",
  "Remove isolated spikes at the size extremes (paper's 40% rule)",
  "Take the volume-weighted mean diameter",
], 13), { x: 0.72, y: 1.9, w: 2.9, h: 2.9 });
const fh = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 }, fontSize: 12 } });
const fc = (t, o) => ({ text: t, options: Object.assign({ fontSize: 12, color: C.text1 }, o || {}) });
s.addTable([
  [fh("Feature"), fh("Plain meaning"), fh("Expected effect")],
  [fc("u_b  wave velocity", { bold: true }), fc("How hard waves shake the water at the bed"), fc("Smaller flocs")],
  [fc("ū  tidal current", { bold: true }), fc("Flood (+) or ebb (-) tide now"), fc("Weak")],
  [fc("ū₄  current 4 h ago", { bold: true }), fc("Water arriving from upstream"), fc("Larger flocs")],
  [fc("ε  turbulence", { bold: true }), fc("Small-scale stirring"), fc("Breakup")],
  [fc("T  temperature", { bold: true }), fc("Season; proxy for biology"), fc("Spring growth")],
  [fc("S  salinity", { bold: true }), fc("Season; river inflow"), fc("Weak")],
], { x: 4.1, y: 1.3, w: 5.4, colW: [1.65, 2.4, 1.35], border: { type: "solid", pt: 0.75, color: HEX.line },
  margin: 0.05, valign: "middle", objectName: "Feature table" });
text(s, "Quality control: bursts with more than 10% bad current samples are dropped. Gaps are never filled.",
  { x: 4.1, y: 4.5, w: 5.4, h: 0.45, fontSize: 12, color: HEX.muted, italic: true });

// ================================================================ 7. Workflow
s = content("Workflow and code structure", "Approach");
const steps = [
  ["Raw files", "Data/ (.mat)"],
  ["Load + QC", "src/load.py"],
  ["Features", "build_features"],
  ["Feature table", "outputs/cache"],
  ["Models", "run_random_forest"],
  ["Report", "outputs/"],
];
const bw = 1.32, gap = 0.216;
steps.forEach(([h, f], i) => {
  const x = 0.5 + i * (bw + gap);
  card(s, x, 1.45, bw, 1.25, "Step " + (i + 1));
  badge(s, x + bw / 2 - 0.21, 1.25, String(i + 1), "Step badge " + (i + 1), C.accent1);
  text(s, [{ text: h, options: { bold: true, fontSize: 13, color: C.text2, breakLine: true } },
           { text: f, options: { fontSize: 10, color: HEX.muted } }],
       { x: x + 0.08, y: 1.8, w: bw - 0.16, h: 0.8, align: "center" });
  if (i < steps.length - 1) {
    s.addShape(pres.shapes.RIGHT_ARROW, { x: x + bw + 0.03, y: 1.97, w: gap - 0.06, h: 0.2,
      fill: { color: C.accent2 }, line: { color: C.accent2, width: 0 }, objectName: "Arrow " + (i + 1) });
  }
});
card(s, 0.5, 3.0, 4.35, 1.95, "Repo card");
text(s, [{ text: "Code layout", options: { bold: true, fontSize: 14, color: C.text2, breakLine: true } }],
  { x: 0.72, y: 3.12, w: 4.0, h: 0.35 });
text(s, bullets([
  "src/  load, features, models, predict",
  "scripts/  all models, figures, diagnostics",
  "outputs/  cached table, tables, figures, report",
], 12), { x: 0.72, y: 3.5, w: 4.0, h: 1.35 });
card(s, 5.15, 3.0, 4.35, 1.95, "Demo card");
text(s, [{ text: "Live demo (two commands)", options: { bold: true, fontSize: 14, color: C.text2, breakLine: true } }],
  { x: 5.37, y: 3.12, w: 4.0, h: 0.35 });
text(s, [
  { text: "ven/bin/python build_features.py", options: { breakLine: true } },
  { text: "ven/bin/python run_random_forest.py", options: { breakLine: true } },
], { x: 5.37, y: 3.55, w: 4.0, h: 0.7, fontFace: "Courier New", fontSize: 11, color: C.text1 });
text(s, "Prints our scores next to both papers and saves a CSV.",
  { x: 5.37, y: 4.3, w: 4.0, h: 0.5, fontSize: 12, color: HEX.muted });

// ================================================================ 8. MAIN: model choice
pres.addSection({ title: "Model" });
s = content("Our model choice: Random Forest", "Model");
card(s, 0.5, 1.25, 4.35, 3.0, "Why RF card");
text(s, [{ text: "Why a Random Forest", options: { bold: true, fontSize: 15, color: C.accent2, breakLine: true } }],
  { x: 0.72, y: 1.38, w: 4.0, h: 0.35 });
text(s, bullets([
  "Same model as Egan's CS229 report, so scores compare directly (32 trees, default settings)",
  "Captures thresholds: waves only break flocs above a certain strength",
  "Built for small tables: no scaling, robust to noisy sensors",
  "Explains itself: feature importance shows which physics matters",
], 13), { x: 0.72, y: 1.78, w: 4.0, h: 2.4 });
card(s, 5.15, 1.25, 4.35, 3.0, "Data fit card");
text(s, [{ text: "How our data suits it", options: { bold: true, fontSize: 15, color: C.accent2, breakLine: true } }],
  { x: 5.37, y: 1.38, w: 4.0, h: 0.35 });
text(s, bullets([
  "Tabular: 1,120 rows x 6 features, one row per hour",
  "Mixed units (m/s, °C, PSU, W/kg) are fine for trees",
  "Features interact (tide x waves); trees learn this without hand-made terms",
  "Averaging many trees smooths the noise in field data",
], 13), { x: 5.37, y: 1.78, w: 4.0, h: 2.4 });
text(s, [
  { text: "Limitations: ", options: { bold: true, color: C.accent6 } },
  { text: "a forest cannot predict beyond the range it was trained on, and neighbouring hours are near-copies, so a random split overstates accuracy. " },
  { text: "Also run for comparison: ", options: { bold: true, color: C.text2 } },
  { text: "LASSO (journal paper) and SVR (class paper's second model)." },
], { x: 0.5, y: 4.4, w: 9.0, h: 0.75, fontSize: 13 });

// ================================================================ 9. Evaluation design
s = content("How we test: three ways to hold data out", "Model");
const N = 24;
const rows = [
  ["Random 70/30", "Test hours sit next to training hours, so it is optimistic (class paper)",
    (i) => ([2, 5, 9, 12, 16, 19, 22].includes(i) ? "test" : "train")],
  ["Time-blocked", "Whole multi-day stretches held out with a 12 h gap. Closest to real forecasting (ours)",
    (i) => (i >= 10 && i <= 15 ? "test" : (i === 9 || i === 16 ? "gap" : "train"))],
  ["Leave one season out", "Train on two seasons, predict the third. New-conditions test (ours)",
    (i) => (i >= 16 ? "test" : "train")],
];
rows.forEach(([name, desc, f], r) => {
  const y = 1.35 + r * 1.05;
  text(s, [{ text: name, options: { bold: true, fontSize: 14, color: C.text2 } }], { x: 0.5, y: y, w: 2.0, h: 0.35 });
  for (let i = 0; i < N; i++) {
    const kind = f(i);
    const sep = r === 2 ? Math.floor(i / 8) * 0.1 : 0;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5 + i * 0.165 + sep, y: y + 0.42, w: 0.13, h: 0.26,
      fill: { color: kind === "test" ? C.accent2 : (kind === "gap" ? C.background1 : C.accent1) },
      line: { color: kind === "gap" ? HEX.line : (kind === "test" ? HEX.ochre : HEX.teal), width: 0.75 },
      objectName: `Timeline ${r + 1}-${i + 1}` });
  }
  text(s, desc, { x: 4.75, y: y + 0.28, w: 4.75, h: 0.6, fontSize: 13 });
});
// legend
const ly = 4.6;
[["Training hour", C.accent1, HEX.teal], ["Test hour", C.accent2, HEX.ochre], ["Gap (unused)", C.background1, HEX.line]].forEach(([lab, fill, ln], i) => {
  const x = 0.5 + i * 1.75;
  s.addShape(pres.shapes.RECTANGLE, { x, y: ly + 0.05, w: 0.18, h: 0.18, fill: { color: fill }, line: { color: ln, width: 0.75 }, objectName: "Legend " + lab });
  text(s, lab, { x: x + 0.27, y: ly, w: 1.4, h: 0.3, fontSize: 12 });
});
text(s, [{ text: "Score r²: ", options: { bold: true } },
  { text: "1 = perfect, 0 = no better than guessing the average, below 0 = worse than that." }],
  { x: 5.75, y: ly - 0.05, w: 3.75, h: 0.55, fontSize: 12, color: HEX.muted });

// ================================================================ 10. Results: accuracy
pres.addSection({ title: "Results" });
s = content("Results: how accurate is it", "Results");
barChart(s, { x: 0.5, y: 1.25, w: 5.9, h: 3.7, min: -0.2, max: 1.0, labelW: 2.55, color: C.accent1,
  colors: [C.accent5, C.accent1, C.accent1, C.accent2, C.accent6], name: "Accuracy chart",
  title: "Share of floc-size variation explained (r²)", fmt: (v) => v.toFixed(2),
  items: [["Class paper, reported (random split)", 0.81], ["Our copy of class-paper setup", 0.60],
          ["Our features, random split", 0.64], ["Our features, held-out time blocks", 0.34],
          ["One season, held-out blocks (best)", -0.14]] });
text(s, [{ text: "0.34", options: { fontFace: THEME.headFontFace, fontSize: 48, bold: true, color: C.accent2, breakLine: true } },
  { text: "accuracy on unseen time periods, all seasons (95% interval 0.15 to 0.49)", options: { fontSize: 13 } }],
  { x: 6.6, y: 1.3, w: 2.9, h: 1.65 });
text(s, [{ text: "Below 0", options: { fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.accent6, breakLine: true } },
  { text: "when predicting a season the model never saw", options: { fontSize: 13 } }],
  { x: 6.6, y: 3.2, w: 2.9, h: 1.2 });

// ================================================================ 11. Results: drivers
s = content("Results: what drives floc size", "Results");
barChart(s, { x: 0.5, y: 1.25, w: 5.1, h: 3.5, min: 0, max: 0.2, labelW: 1.85, color: C.accent2,
  name: "Importance chart", title: "Drop in r² when the feature is shuffled", fmt: (v) => v.toFixed(2),
  items: [["ū₄  current 4 h ago", 0.155], ["u_b  wave velocity", 0.126], ["ū  current now", 0.050],
          ["S  salinity", 0.045], ["T  temperature", 0.045], ["ε  turbulence", 0.014]] });
card(s, 5.9, 1.25, 3.6, 3.55, "Agreement card");
text(s, [{ text: "Matches the journal paper", options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } }],
  { x: 6.12, y: 1.4, w: 3.2, h: 0.4 });
text(s, bullets([
  "Stronger waves give smaller flocs",
  "Stronger tide 4 h earlier brings larger flocs",
  "Turbulence adds almost nothing",
  "Salinity is weak within a season, unlike the class paper, which ranked it first",
], 13), { x: 6.12, y: 1.85, w: 3.2, h: 2.85 });
text(s, "Pooled model, all seasons. Longer bar = the model relies on it more.",
  { x: 0.5, y: 4.9, w: 5.2, h: 0.3, fontSize: 11, color: HEX.muted, italic: true });

// ================================================================ 12. Results: time series
s = content("Results: what the model gets right and wrong", "Results");
s.addImage({ path: path.join(FIG, "timeseries_rf_oof.png"), x: 0.4, y: 1.15, w: 5.85, h: 3.72,
  altText: "Measured and predicted floc size over time for each season", objectName: "Time series figure" });
text(s, "Grey: measured floc size. Colour: prediction for days the model never saw ('out-of-fold').",
  { x: 0.4, y: 4.92, w: 5.85, h: 0.35, fontSize: 11, color: HEX.muted, italic: true });
card(s, 6.5, 1.25, 3.0, 3.6, "Summary card");
text(s, [{ text: "Gets right", options: { bold: true, fontSize: 14, color: C.accent3, breakLine: true } },
  { text: "The tide-to-tide rhythm, especially late Winter and Spring.", options: { fontSize: 13, breakLine: true } },
  { text: " ", options: { fontSize: 8, breakLine: true } },
  { text: "Gets wrong", options: { bold: true, fontSize: 14, color: C.accent6, breakLine: true } },
  { text: "Multi-day shifts in the average size, such as early Winter and late Summer. These are likely driven by biology and by where the mud comes from, which we cannot measure.", options: { fontSize: 13 } }],
  { x: 6.72, y: 1.42, w: 2.6, h: 3.35 });

// ================================================================ 13. Conclusions
pres.addSection({ title: "Conclusions" });
s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Conclusions" });
s.addText("Conclusions", { placeholder: "title" });
const concl = [
  "The physics matches the published paper: waves break flocs, and the delayed tide brings larger ones.",
  "Physics alone explains about a third of floc-size variation across seasons (r² 0.34) and very little within one season.",
  "Random splits inflate accuracy: the same model scores 0.64 that way, which explains much of the class paper's 0.81.",
  "A model meant to last years needs biology and sediment sensors and more deployments, more than a new algorithm.",
];
concl.forEach((t, i) => {
  const y = 1.3 + i * 0.88;
  badge(s, 0.5, y, String(i + 1), "Conclusion badge " + (i + 1));
  text(s, t, { x: 1.1, y: y + 0.02, w: 8.4, h: 0.8, fontSize: 15, color: C.background1 });
});
text(s, "Next step: the same group's optics data on Dryad, which lists a 15 cm sizer and a particle-type index.",
  { x: 0.5, y: 4.85, w: 8.3, h: 0.35, fontSize: 12, color: C.background2, italic: true });

// ================================================================ 14. Comparison
s = content("Comparison and reasons for the difference", "Conclusions");
const th2 = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 }, fontSize: 12 } });
const tc = (t, o) => ({ text: t, options: Object.assign({ fontSize: 12, color: C.text1 }, o || {}) });
s.addTable([
  [th2(""), th2("Journal paper (2022)"), th2("Class paper (CS229)"), th2("This project")],
  [tc("Inputs", { bold: true }), tc("11: physics, biology, sediment"), tc("8: physics, biology"), tc("6: physics only")],
  [tc("Location", { bold: true }), tc("Optics platform, sizer 15 cm"), tc("Single optics platform"), tc("Platform P2, sizer 35 cm")],
  [tc("Model", { bold: true }), tc("LASSO + feature elimination"), tc("Random Forest, SVR"), tc("Random Forest (main), SVR, LASSO")],
  [tc("How scored", { bold: true }), tc("Fit on its own data"), tc("Random 70/30 split"), tc("Held-out time blocks, plus both of theirs")],
  [tc("Reported r²", { bold: true }), tc("0.15 to 0.65"), tc("0.81 (RF), 0.76 (SVR)"), tc("0.34 held-out; 0.60 / 0.53 class setup; 0.17 to 0.43 fit")],
], { x: 0.5, y: 1.2, w: 9.0, colW: [1.25, 2.4, 2.25, 3.1], rowH: [0.36, 0.42, 0.42, 0.42, 0.42, 0.55], border: { type: "solid", pt: 0.75, color: HEX.line },
  margin: 0.05, valign: "middle", objectName: "Comparison table" });
const reasons = [
  ["Missing inputs", "No particle-type or chlorophyll data. These drive spring and multi-day changes."],
  ["Scoring method", "Random splits and fits on the same data reward memorising neighbouring hours."],
  ["Different spot", "35 cm vs 15 cm above the bed, and a different platform."],
];
reasons.forEach(([h, b], i) => {
  const x = 0.5 + i * 3.07;
  badge(s, x, 4.15, String(i + 1), "Reason badge " + (i + 1));
  text(s, [{ text: h, options: { bold: true, fontSize: 13, color: C.text2, breakLine: true } },
           { text: b, options: { fontSize: 12 } }], { x: x + 0.55, y: 4.1, w: 2.4, h: 1.05 });
});

// ---------------------------------------------------------------- write
(async () => {
  await pres.writeFile({ fileName: OUT });
  if (APPLY_THEME) {
    const { applyTheme } = require(APPLY_THEME);
    await applyTheme(OUT, THEME);
  }
  console.log("wrote", OUT);
})();
