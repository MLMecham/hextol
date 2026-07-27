# Comparison explorer

The same tool as `hextol-gui`, running in your browser. Two tabs, one per form
of sample `is_match` accepts: a single **color**, or a whole **region** of
pixels. They share the tolerance slider, so a value you settle on in one
carries into the other.

The **Screen** buttons use the browser EyeDropper API to sample any pixel on
your screen (Chrome and Edge; other browsers can use the color picker).
**Capture screen** on the Region tab uses screen sharing to grab one frame.
Loading, capturing, and the demo image all do the same thing: they put an image
in the region buffer. **Sample** is the separate step that opens that image
full size so you can drag a box out of it, and it always cuts from the original,
so you can resample as often as you like without ever sampling a sample.

<div id="hx-demo">
<div class="hx-tabs">
<button class="hx-tab hx-tab-on" id="hx-tab-color" type="button">Color</button>
<button class="hx-tab" id="hx-tab-region" type="button">Region</button>
</div>
<div class="hx-panel" id="hx-panel-color">
<div class="hx-cards">
<div class="hx-card">
<div class="hx-swatch" id="hx-swatch-A"></div>
<div class="hx-controls">
<input class="hx-hex" id="hx-hex-A" value="#3B82F6" spellcheck="false">
<input class="hx-native" id="hx-native-A" type="color" value="#3B82F6" title="Pick">
<button class="hx-btn" id="hx-eye-A" type="button">Screen</button>
</div>
</div>
<span class="hx-vs">vs</span>
<div class="hx-card">
<div class="hx-swatch" id="hx-swatch-B"></div>
<div class="hx-controls">
<input class="hx-hex" id="hx-hex-B" value="#2F7BEE" spellcheck="false">
<input class="hx-native" id="hx-native-B" type="color" value="#2F7BEE" title="Pick">
<button class="hx-btn" id="hx-eye-B" type="button">Screen</button>
</div>
</div>
</div>
<canvas id="hx-gradient" width="560" height="30"></canvas>
<div class="hx-tol-row">
<span class="hx-muted">tolerance</span>
<input class="hx-tol" id="hx-tol-c" type="range" min="0" max="100" step="0.5" value="10">
<span id="hx-tol-val-c" class="hx-accent">10.0</span>
</div>
<div class="hx-scroll">
<table class="hx-table">
<thead><tr><th>method</th><th>0-100</th><th>raw</th><th>verdict</th><th></th></tr></thead>
<tbody id="hx-rows"></tbody>
</table>
</div>
</div>
<div class="hx-panel hx-hide" id="hx-panel-region">
<div class="hx-cards">
<div class="hx-card">
<div class="hx-label">region</div>
<canvas id="hx-region" width="300" height="210" title="Drag to select part of the image"></canvas>
<div class="hx-controls hx-actions">
<button class="hx-btn" id="hx-load" type="button">Load image</button>
<button class="hx-btn" id="hx-capture" type="button">Capture screen</button>
<button class="hx-btn" id="hx-demo-image" type="button">Demo image</button>
<button class="hx-btn hx-btn-go" id="hx-sample" type="button">Sample</button>
</div>
<div class="hx-info" id="hx-region-info"></div>
</div>
<div class="hx-card">
<div class="hx-label">target color</div>
<div class="hx-swatch hx-swatch-lg" id="hx-swatch-T"></div>
<div class="hx-controls">
<input class="hx-hex" id="hx-hex-T" value="#3B82F6" spellcheck="false">
<input class="hx-native" id="hx-native-T" type="color" value="#3B82F6" title="Pick">
<button class="hx-btn" id="hx-eye-T" type="button">Screen</button>
</div>
<div class="hx-info" id="hx-target-info"></div>
</div>
</div>
<div class="hx-tol-row">
<span class="hx-muted">tolerance</span>
<input class="hx-tol" id="hx-tol-r" type="range" min="0" max="100" step="0.5" value="10">
<span id="hx-tol-val-r" class="hx-accent">10.0</span>
</div>
<div class="hx-scroll">
<table class="hx-table hx-table-region">
<thead><tr id="hx-region-head"></tr></thead>
<tbody id="hx-region-rows"></tbody>
</table>
</div>
<div class="hx-legend" id="hx-legend-num"></div>
<div class="hx-legend" id="hx-legend-agg"></div>
</div>
<div class="hx-modal hx-hide" id="hx-modal">
<canvas id="hx-modal-canvas"></canvas>
<div class="hx-modal-hint">Drag a box over the area to test. Enter uses the whole image, Esc cancels.</div>
</div>
<input id="hx-file" type="file" accept="image/*" class="hx-hide">
<div id="hx-status" class="hx-status"></div>
</div>

<style>
#hx-demo{background:#0F1526;border:1px solid #2E3854;border-radius:10px;
  padding:24px;color:#E6EAF2;font-family:"Segoe UI",system-ui,sans-serif;
  max-width:720px;margin:0 auto}
#hx-demo .hx-hide{display:none}
#hx-demo .hx-tabs{display:flex;gap:4px;margin-bottom:16px;border-bottom:1px solid #2E3854}
#hx-demo .hx-tab{background:none;border:none;border-bottom:2px solid transparent;
  color:#8B93A7;font-weight:600;font-size:.9rem;padding:6px 16px;cursor:pointer;
  font-family:inherit}
#hx-demo .hx-tab:hover{color:#E6EAF2}
#hx-demo .hx-tab-on{color:#2DD4BF;border-bottom-color:#2DD4BF}
#hx-demo .hx-cards{display:flex;align-items:flex-start;justify-content:center;gap:14px}
#hx-demo .hx-card{background:#1A2138;border:1px solid #2E3854;border-radius:8px;padding:10px}
#hx-demo .hx-swatch{width:190px;height:110px;background:#232B45;border-radius:4px}
#hx-demo .hx-swatch-lg{width:300px;height:210px}
#hx-demo #hx-region{display:block;width:300px;height:210px;background:#232B45;
  border-radius:4px;cursor:crosshair}
#hx-demo .hx-label{color:#8B93A7;font-size:.7rem;font-weight:600;text-transform:uppercase;
  letter-spacing:.05em;margin-bottom:6px}
#hx-demo .hx-info{color:#8B93A7;font-size:.75rem;margin-top:8px;min-height:1.1em}
#hx-demo .hx-controls{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:10px}
#hx-demo .hx-vs{color:#8B93A7;font-weight:600;align-self:center}
#hx-demo .hx-hex{width:86px;background:#232B45;color:#E6EAF2;border:1px solid #2E3854;
  border-radius:4px;padding:4px 6px;font-family:Consolas,monospace;text-align:center}
#hx-demo .hx-hex:focus{outline:none;border-color:#2DD4BF}
#hx-demo .hx-native{width:30px;height:30px;padding:0;border:1px solid #2E3854;
  border-radius:4px;background:#232B45;cursor:pointer}
#hx-demo .hx-btn{background:#232B45;color:#E6EAF2;border:none;border-radius:4px;
  padding:5px 10px;cursor:pointer;font-family:inherit;font-size:.85rem}
#hx-demo .hx-btn:hover{background:#2DD4BF;color:#0F1526}
#hx-demo .hx-btn:disabled{opacity:.4;cursor:not-allowed}
#hx-demo .hx-btn:disabled:hover{background:#232B45;color:#E6EAF2}
#hx-demo #hx-gradient{display:block;margin:16px auto 0;border-radius:4px;max-width:100%}
#hx-demo .hx-tol-row{display:flex;align-items:center;gap:12px;margin-top:14px}
#hx-demo .hx-tol{flex:1;accent-color:#2DD4BF}
#hx-demo .hx-muted{color:#8B93A7}
#hx-demo .hx-accent{color:#2DD4BF;font-family:Consolas,monospace;width:44px}
#hx-demo .hx-scroll{overflow-x:auto}
#hx-demo .hx-table{width:100%;margin-top:16px;border-collapse:collapse;font-size:.85rem}
#hx-demo .hx-table th{color:#8B93A7;text-align:left;font-size:.7rem;
  text-transform:uppercase;letter-spacing:.05em;padding:4px 8px;white-space:nowrap}
#hx-demo .hx-table td{padding:5px 8px;border-top:1px solid #232B45}
#hx-demo .hx-table-region{font-size:.8rem}
#hx-demo .hx-table-region th:nth-child(n+4){text-align:center}
#hx-demo .hx-table-region td:nth-child(n+4){text-align:center}
#hx-demo .hx-name{font-weight:600}
#hx-demo .hx-num{font-family:Consolas,monospace}
#hx-demo .hx-raw{font-family:Consolas,monospace;color:#8B93A7}
#hx-demo .hx-hint{color:#8B93A7;font-size:.8rem}
#hx-demo .hx-legend{color:#8B93A7;font-size:.75rem;margin-top:8px}
#hx-demo .hx-legend b{color:#B6BDCC;font-weight:600}
#hx-demo .hx-pill{display:inline-block;min-width:64px;text-align:center;
  border-radius:4px;padding:2px 8px;font-weight:600;font-size:.75rem}
#hx-demo .hx-table-region .hx-pill{min-width:52px;padding:2px 6px;font-size:.7rem}
#hx-demo .hx-match{background:#123B2E;color:#4ADE80}
#hx-demo .hx-miss{background:#3F1D25;color:#F87171}
#hx-demo .hx-empty{background:#232B45;color:#8B93A7}
#hx-demo .hx-status{color:#F87171;margin-top:10px;min-height:1.2em;font-size:.85rem}
#hx-demo .hx-actions{flex-wrap:wrap}
#hx-demo .hx-btn-go{background:#2DD4BF;color:#0F1526;font-weight:600}
#hx-demo .hx-btn-go:hover{background:#5EEAD4;color:#0F1526}
/* The sampler is a fixed overlay so a 1760px capture gets the whole viewport to
   be picked apart in, rather than the 300px preview it is parked in. */
#hx-demo .hx-modal{position:fixed;inset:0;z-index:1000;background:rgba(8,12,22,.86);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px}
#hx-demo .hx-modal.hx-hide{display:none}
#hx-demo #hx-modal-canvas{background:#232B45;border:1px solid #2E3854;border-radius:4px;
  cursor:crosshair;max-width:92vw;max-height:78vh;touch-action:none}
#hx-demo .hx-modal-hint{color:#B6BDCC;font-size:.85rem;background:#0F1526;
  border:1px solid #2E3854;border-radius:6px;padding:8px 14px;text-align:center}
</style>

<script>
(function () {
  const METHODS = {
    channel: {
      max: 255,
      raw: (a, b) => Math.max(Math.abs(a[0]-b[0]), Math.abs(a[1]-b[1]), Math.abs(a[2]-b[2])),
      hint: "strictest: the worst channel alone decides",
    },
    euclidean: {
      max: Math.sqrt(3) * 255,
      raw: (a, b) => Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]),
      hint: "straight line in RGB; general-purpose default",
    },
    weighted: {
      max: 255 * Math.sqrt(8 + 255/256),
      raw: (a, b) => {
        const rm = (a[0]+b[0]) / 2, dr = a[0]-b[0], dg = a[1]-b[1], db = a[2]-b[2];
        return Math.sqrt((2 + rm/256)*dr*dr + 4*dg*dg + (2 + (255-rm)/256)*db*db);
      },
      hint: "redmean, perceptual; best for human-picked colors",
    },
  };

  // Loosest first: "any" passes whenever "majority" does and "majority"
  // whenever "all" does, so a MATCH fills in from the left and never leaves a
  // gap. "average" sits last because it thresholds the mean instead of
  // counting pixels, which is the only way that run can break.
  const AGGREGATES = {
    any: "at least one pixel within",
    majority: "over half the pixels within",
    all: "every pixel within",
    average: "mean dist within tolerance",
  };
  const COLUMNS = {
    "% within": "share of pixels individually within tolerance",
    "mean dist": "average distance over the whole region, 0-100",
  };
  const ANALYSIS_MAX = 96;   // longest edge of the pixel grid actually judged

  const $ = (id) => document.getElementById(id);
  if (!$("hx-demo")) return;

  function hexToRgb(s) {
    let h = s.trim().replace(/^#/, "");
    if (/^[0-9a-f]{3}$/i.test(h)) h = h.split("").map((c) => c + c).join("");
    if (!/^[0-9a-f]{6}$/i.test(h)) return null;
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }
  const rgbToHex = (rgb) =>
    "#" + rgb.map((v) => v.toString(16).padStart(2, "0")).join("").toUpperCase();
  const setStatus = (text) => { $("hx-status").textContent = text || ""; };
  function pill(el, ok) {
    el.textContent = ok ? "MATCH" : "MISS";
    el.className = "hx-pill " + (ok ? "hx-match" : "hx-miss");
  }
  function clearPill(el) {
    el.textContent = "-";
    el.className = "hx-pill hx-empty";
  }

  // --- tabs, sharing one tolerance value ------------------------------------

  let tolerance = 10;

  function selectTab(which) {
    const onColor = which === "color";
    $("hx-panel-color").classList.toggle("hx-hide", !onColor);
    $("hx-panel-region").classList.toggle("hx-hide", onColor);
    $("hx-tab-color").classList.toggle("hx-tab-on", onColor);
    $("hx-tab-region").classList.toggle("hx-tab-on", !onColor);
    setStatus("");
    refreshAll();
  }
  $("hx-tab-color").addEventListener("click", () => selectTab("color"));
  $("hx-tab-region").addEventListener("click", () => selectTab("region"));

  for (const suffix of ["c", "r"]) {
    $("hx-tol-" + suffix).addEventListener("input", (e) => {
      tolerance = parseFloat(e.target.value);
      refreshAll();
    });
  }

  function syncTolerance() {
    for (const suffix of ["c", "r"]) {
      $("hx-tol-" + suffix).value = tolerance;
      $("hx-tol-val-" + suffix).textContent = tolerance.toFixed(1);
    }
  }

  // --- color inputs, shared by both panels ----------------------------------

  function setColor(side, hex) {
    $("hx-hex-" + side).value = hex.toUpperCase();
    const rgb = hexToRgb(hex);
    if (rgb) $("hx-native-" + side).value = rgbToHex(rgb).toLowerCase();
    refreshAll();
  }

  for (const side of ["A", "B", "T"]) {
    $("hx-hex-" + side).addEventListener("input", refreshAll);
    $("hx-native-" + side).addEventListener("input", (e) => setColor(side, e.target.value));
    const eye = $("hx-eye-" + side);
    if ("EyeDropper" in window) {
      eye.addEventListener("click", async () => {
        try {
          const r = await new EyeDropper().open();
          setColor(side, r.sRGBHex);
        } catch (e) { /* user cancelled */ }
      });
    } else {
      eye.disabled = true;
      eye.title = "Screen picking needs Chrome or Edge (EyeDropper API)";
    }
  }

  // --- color panel ----------------------------------------------------------

  const colorRows = {};
  for (const name of Object.keys(METHODS)) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td class="hx-name">' + name + '</td><td class="hx-num">-</td>' +
      '<td class="hx-raw">-</td><td><span class="hx-pill hx-empty">-</span></td>' +
      '<td class="hx-hint">' + METHODS[name].hint + "</td>";
    $("hx-rows").appendChild(tr);
    colorRows[name] = {
      dist: tr.children[1], raw: tr.children[2], pill: tr.children[3].firstChild,
    };
  }

  function refreshColor() {
    const a = hexToRgb($("hx-hex-A").value), b = hexToRgb($("hx-hex-B").value);
    if (!a || !b) {
      if (!$("hx-panel-color").classList.contains("hx-hide")) {
        setStatus("Invalid color: enter hex like #3B82F6");
      }
      for (const r of Object.values(colorRows)) {
        r.dist.textContent = "-";
        r.raw.textContent = "-";
        clearPill(r.pill);
      }
      return;
    }
    $("hx-swatch-A").style.background = rgbToHex(a);
    $("hx-swatch-B").style.background = rgbToHex(b);

    const ctx = $("hx-gradient").getContext("2d");
    const steps = 48, w = 560 / steps;
    for (let i = 0; i < steps; i++) {
      const t = i / (steps - 1);
      ctx.fillStyle = rgbToHex([0, 1, 2].map((c) => Math.round(a[c] + (b[c] - a[c]) * t)));
      ctx.fillRect(i * w, 0, w + 1, 30);
    }

    for (const [name, m] of Object.entries(METHODS)) {
      const raw = m.raw(a, b), d = (raw / m.max) * 100;
      colorRows[name].dist.textContent = d.toFixed(1);
      colorRows[name].raw.textContent = raw.toFixed(1);
      pill(colorRows[name].pill, d <= tolerance);
    }
  }

  // --- region panel ---------------------------------------------------------

  const head = $("hx-region-head");
  head.innerHTML = "<th>method</th>" +
    Object.keys(COLUMNS).map((c) => "<th>" + c + "</th>").join("") +
    Object.keys(AGGREGATES).map((a) => "<th>" + a + "</th>").join("");
  const legendHtml = (hints) =>
    Object.entries(hints).map(([k, v]) => "<b>" + k + ":</b> " + v).join("&nbsp; &nbsp;");
  $("hx-legend-num").innerHTML = legendHtml(COLUMNS);
  $("hx-legend-agg").innerHTML = legendHtml(AGGREGATES);

  const regionRows = {};
  for (const name of Object.keys(METHODS)) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td class="hx-name">' + name + '</td><td class="hx-num">-</td>' +
      '<td class="hx-raw">-</td>' +
      Object.keys(AGGREGATES).map(() => '<td><span class="hx-pill hx-empty">-</span></td>').join("");
    $("hx-region-rows").appendChild(tr);
    const pills = {};
    Object.keys(AGGREGATES).forEach((a, i) => {
      pills[a] = tr.children[3 + i].firstChild;
    });
    regionRows[name] = { within: tr.children[1], mean: tr.children[2], pills };
  }

  // The source image at natural size, plus the selection within it. Pixels are
  // sampled from the selection only, so dragging a box changes what is judged.
  const source = document.createElement("canvas");
  let sourceReady = false;
  let selection = null;          // {x, y, w, h} in source pixels
  let region = null;             // {pixels: [[r,g,b], ...], w, h}
  let sourceLabel = "";
  let drag = null;

  /** Reduce one method's per-pixel distances to the four aggregate verdicts.
   *  Mirrors hextol.gui.region_stats, which mirrors is_match. */
  function regionStats(dists, tol) {
    const n = dists.length;
    let within = 0, sum = 0;
    for (const d of dists) {
      if (d <= tol) within++;
      sum += d;
    }
    const mean = sum / n;
    return {
      within: within / n,
      mean: mean,
      verdicts: {
        any: within > 0,
        majority: within * 2 > n,
        all: within === n,
        average: mean <= tol,
      },
    };
  }

  /** Nearest-neighbour subsample of the selection, capped on its longest edge.
   *  Picking real pixels rather than averaging matters: a blended pixel is a
   *  color that was never in the image, and it would shift every distance. */
  function sampleSelection() {
    if (!sourceReady || !selection) return;
    const { x, y, w, h } = selection;
    const data = source.getContext("2d", { willReadFrequently: true })
      .getImageData(x, y, w, h).data;
    const step = Math.max(w, h) / ANALYSIS_MAX;
    const nw = step > 1 ? Math.max(1, Math.floor(w / step)) : w;
    const nh = step > 1 ? Math.max(1, Math.floor(h / step)) : h;
    const pixels = [];
    for (let ry = 0; ry < nh; ry++) {
      const sy = Math.floor(ry * h / nh);
      for (let rx = 0; rx < nw; rx++) {
        const i = (sy * w + Math.floor(rx * w / nw)) * 4;
        pixels.push([data[i], data[i + 1], data[i + 2]]);
      }
    }
    region = { pixels: pixels, w: nw, h: nh };
  }

  /** Map the source image into the display canvas, letterboxed and centered. */
  function fit() {
    const c = $("hx-region");
    const scale = Math.min(c.width / source.width, c.height / source.height);
    return {
      scale: scale,
      ox: (c.width - source.width * scale) / 2,
      oy: (c.height - source.height * scale) / 2,
    };
  }

  function drawRegion(preview) {
    const c = $("hx-region"), ctx = c.getContext("2d");
    ctx.fillStyle = "#232B45";
    ctx.fillRect(0, 0, c.width, c.height);
    if (!sourceReady) {
      ctx.fillStyle = "#8B93A7";
      ctx.font = '13px "Segoe UI", system-ui, sans-serif';
      ctx.textAlign = "center";
      ctx.fillText("load an image or capture your screen", c.width / 2, c.height / 2);
      return;
    }
    const f = fit();
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(source, f.ox, f.oy, source.width * f.scale, source.height * f.scale);

    const box = preview || (selection && (selection.w !== source.width ||
      selection.h !== source.height) ? selection : null);
    if (!box) return;
    const bx = f.ox + box.x * f.scale, by = f.oy + box.y * f.scale;
    const bw = box.w * f.scale, bh = box.h * f.scale;
    // Four shades around the selection: canvas cannot punch a hole in one
    // rectangle, so the unselected area is drawn as its complement.
    ctx.fillStyle = "rgba(15, 21, 38, 0.68)";
    ctx.fillRect(0, 0, c.width, by);
    ctx.fillRect(0, by + bh, c.width, c.height - by - bh);
    ctx.fillRect(0, by, bx, bh);
    ctx.fillRect(bx + bw, by, c.width - bx - bw, bh);
    ctx.strokeStyle = "#2DD4BF";
    ctx.lineWidth = 2;
    ctx.strokeRect(bx, by, bw, bh);
  }

  function adoptSource(label) {
    sourceReady = true;
    sourceLabel = label;
    selection = { x: 0, y: 0, w: source.width, h: source.height };
    sampleSelection();
    drawRegion();
    refreshAll();
  }

  /** A procedural stand-in for a screenshot: a rounded button on a dark panel.
   *  The anti-aliased corners and the inner highlight are what make the four
   *  aggregates disagree, which is the whole point of the tab. Acquisition
   *  only: it replaces the buffer, which is why it is not called "Sample". */
  function drawDemoImage() {
    source.width = 240;
    source.height = 72;
    const ctx = source.getContext("2d");
    ctx.fillStyle = "#1A2138";
    ctx.fillRect(0, 0, 240, 72);
    ctx.fillStyle = "#3B82F6";
    ctx.beginPath();
    const x = 16, y = 14, w = 208, h = 44, r = 10;
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = "rgba(255, 255, 255, 0.22)";
    ctx.fillRect(x + 18, y + 12, 76, 20);
    adoptSource("demo button");
  }

  function loadImage(src, label) {
    const img = new Image();
    img.onload = () => {
      source.width = img.naturalWidth;
      source.height = img.naturalHeight;
      source.getContext("2d").drawImage(img, 0, 0);
      adoptSource(label);
      setStatus("");
    };
    img.onerror = () => setStatus("Could not read that image.");
    img.src = src;
  }

  $("hx-demo-image").addEventListener("click", drawDemoImage);
  $("hx-load").addEventListener("click", () => $("hx-file").click());
  $("hx-file").addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => loadImage(reader.result, file.name);
    reader.readAsDataURL(file);
    e.target.value = "";
  });

  const capture = $("hx-capture");
  if (navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia) {
    capture.addEventListener("click", async () => {
      let stream;
      try {
        stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      } catch (e) {
        return;  // user cancelled the share prompt
      }
      try {
        const video = document.createElement("video");
        video.srcObject = stream;
        video.muted = true;
        await video.play();
        source.width = video.videoWidth;
        source.height = video.videoHeight;
        source.getContext("2d").drawImage(video, 0, 0);
        adoptSource("screen " + video.videoWidth + " x " + video.videoHeight);
        setStatus("");
      } catch (e) {
        setStatus("Could not read that screen frame.");
      } finally {
        stream.getTracks().forEach((t) => t.stop());
      }
    });
  } else {
    capture.disabled = true;
    capture.title = "Screen capture needs a browser with getDisplayMedia";
  }

  // --- drag a rectangle out of the image ------------------------------------

  function toSource(event) {
    const c = $("hx-region"), rect = c.getBoundingClientRect(), f = fit();
    const cx = (event.clientX - rect.left) * (c.width / rect.width);
    const cy = (event.clientY - rect.top) * (c.height / rect.height);
    return {
      x: Math.min(source.width, Math.max(0, Math.round((cx - f.ox) / f.scale))),
      y: Math.min(source.height, Math.max(0, Math.round((cy - f.oy) / f.scale))),
    };
  }
  const boxOf = (a, b) => ({
    x: Math.min(a.x, b.x), y: Math.min(a.y, b.y),
    w: Math.abs(a.x - b.x), h: Math.abs(a.y - b.y),
  });

  $("hx-region").addEventListener("pointerdown", (e) => {
    if (!sourceReady) return;
    drag = toSource(e);
    $("hx-region").setPointerCapture(e.pointerId);
  });
  $("hx-region").addEventListener("pointermove", (e) => {
    if (!drag) return;
    drawRegion(boxOf(drag, toSource(e)));
  });
  $("hx-region").addEventListener("pointerup", (e) => {
    if (!drag) return;
    const box = boxOf(drag, toSource(e));
    drag = null;
    if (box.w < 2 || box.h < 2) {
      // a plain click resets to the whole image
      selection = { x: 0, y: 0, w: source.width, h: source.height };
    } else {
      selection = box;
    }
    sampleSelection();
    drawRegion();
    refreshAll();
  });

  // --- the sampler: the same drag, on a full-size copy of the buffer ---------
  // Nothing here touches `source`. It only ever writes `selection`, so the
  // image survives and every sample is cut from the original.

  const modal = $("hx-modal"), mcanvas = $("hx-modal-canvas");
  let mscale = 1, mdrag = null, mbox = null;

  function cropped() {
    return selection && (selection.w !== source.width || selection.h !== source.height);
  }

  function openSampler() {
    if (!sourceReady) return;
    // Fill the viewport, and scale small images up rather than leaving a 240px
    // button stranded in the middle of a 1400px overlay. Capped so a favicon
    // does not end up one pixel per hand span.
    const scale = Math.min(
      Math.min(window.innerWidth * 0.9, 1400) / source.width,
      window.innerHeight * 0.74 / source.height,
      8
    );
    mscale = Math.max(scale, 0.05);
    mcanvas.width = Math.max(1, Math.round(source.width * mscale));
    mcanvas.height = Math.max(1, Math.round(source.height * mscale));
    mbox = cropped() ? selection : null;   // show what was picked last time
    mdrag = null;
    modal.classList.remove("hx-hide");
    drawSampler();
  }

  function closeSampler() {
    modal.classList.add("hx-hide");
    mdrag = null;
  }

  function drawSampler() {
    const ctx = mcanvas.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(source, 0, 0, mcanvas.width, mcanvas.height);
    if (!mbox || mbox.w < 1 || mbox.h < 1) return;
    const bx = mbox.x * mscale, by = mbox.y * mscale;
    const bw = mbox.w * mscale, bh = mbox.h * mscale;
    ctx.fillStyle = "rgba(15, 21, 38, 0.68)";
    ctx.fillRect(0, 0, mcanvas.width, by);
    ctx.fillRect(0, by + bh, mcanvas.width, mcanvas.height - by - bh);
    ctx.fillRect(0, by, bx, bh);
    ctx.fillRect(bx + bw, by, mcanvas.width - bx - bw, bh);
    ctx.strokeStyle = "#2DD4BF";
    ctx.lineWidth = 2;
    ctx.strokeRect(bx, by, bw, bh);

    // Live size readout in source pixels, which is what actually gets judged.
    // It sits under the box, or above it when the box runs to the bottom edge.
    const text = mbox.w + " x " + mbox.h;
    ctx.font = '13px Consolas, monospace';
    ctx.textAlign = "center";
    const tw = ctx.measureText(text).width;
    const tx = bx + bw / 2;
    const ty = by + bh + 22 < mcanvas.height ? by + bh + 18 : by - 8;
    ctx.fillStyle = "#0F1526";
    ctx.fillRect(tx - tw / 2 - 6, ty - 13, tw + 12, 19);
    ctx.fillStyle = "#E6EAF2";
    ctx.fillText(text, tx, ty);
  }

  function toSampler(event) {
    const rect = mcanvas.getBoundingClientRect();
    const cx = (event.clientX - rect.left) * (mcanvas.width / rect.width);
    const cy = (event.clientY - rect.top) * (mcanvas.height / rect.height);
    return {
      x: Math.min(source.width, Math.max(0, Math.round(cx / mscale))),
      y: Math.min(source.height, Math.max(0, Math.round(cy / mscale))),
    };
  }

  function commit(box) {
    selection = box;
    sampleSelection();
    closeSampler();
    drawRegion();
    refreshAll();
  }

  $("hx-sample").addEventListener("click", openSampler);
  mcanvas.addEventListener("pointerdown", (e) => {
    mdrag = toSampler(e);
    mcanvas.setPointerCapture(e.pointerId);
  });
  mcanvas.addEventListener("pointermove", (e) => {
    if (!mdrag) return;
    mbox = boxOf(mdrag, toSampler(e));
    drawSampler();
  });
  mcanvas.addEventListener("pointerup", (e) => {
    if (!mdrag) return;
    const box = boxOf(mdrag, toSampler(e));
    mdrag = null;
    if (box.w < 2 || box.h < 2) {   // a stray click, so stay open and let them retry
      mbox = null;
      drawSampler();
      return;
    }
    commit(box);
  });
  // Clicking the backdrop cancels, but only the backdrop: a drag that ends
  // outside the canvas still belongs to the canvas via pointer capture.
  modal.addEventListener("pointerdown", (e) => {
    if (e.target === modal) closeSampler();
  });
  document.addEventListener("keydown", (e) => {
    if (modal.classList.contains("hx-hide")) return;
    if (e.key === "Escape") closeSampler();
    if (e.key === "Enter") commit({ x: 0, y: 0, w: source.width, h: source.height });
  });

  function refreshRegion() {
    const target = hexToRgb($("hx-hex-T").value);
    if (!target) {
      if (!$("hx-panel-region").classList.contains("hx-hide")) {
        setStatus("Invalid color: enter hex like #3B82F6");
      }
      $("hx-target-info").textContent = "";
      for (const r of Object.values(regionRows)) {
        r.within.textContent = "-";
        r.mean.textContent = "-";
        Object.values(r.pills).forEach(clearPill);
      }
      return;
    }
    $("hx-swatch-T").style.background = rgbToHex(target);
    $("hx-target-info").textContent = "rgb(" + target.join(", ") + ")";
    if (!region) {
      $("hx-region-info").textContent = "no region yet";
      for (const r of Object.values(regionRows)) {
        r.within.textContent = "-";
        r.mean.textContent = "-";
        Object.values(r.pills).forEach(clearPill);
      }
      return;
    }
    // Three sizes matter and they are all different: what was acquired, what
    // was sampled out of it, and what survives the subsample cap.
    const crop = cropped() ? ", sampled " + selection.w + " x " + selection.h : "";
    $("hx-region-info").textContent = sourceLabel + crop + ", judging " + region.w +
      " x " + region.h + " = " + (region.w * region.h) + " pixels";

    for (const [name, m] of Object.entries(METHODS)) {
      const dists = region.pixels.map((px) => (m.raw(px, target) / m.max) * 100);
      const stats = regionStats(dists, tolerance);
      const row = regionRows[name];
      row.within.textContent = Math.round(stats.within * 100) + "%";
      row.mean.textContent = stats.mean.toFixed(1);
      for (const a of Object.keys(AGGREGATES)) pill(row.pills[a], stats.verdicts[a]);
    }
  }

  function refreshAll() {
    syncTolerance();
    setStatus("");
    refreshColor();
    refreshRegion();
  }

  drawDemoImage();
})();
</script>

## Reading the region table

Every verdict on the Region tab comes from one of exactly two numbers.

**% within** is the share of pixels individually inside the tolerance. `all`
needs it at 100%, `majority` needs it over half, `any` needs it above zero.
Those three threshold each pixel first and then count, which is why they can
never disagree out of order: `all` passing implies `majority` passes, which
implies `any` passes.

**mean dist** is the average distance across the whole region, and it is the
number `average` thresholds. Because it averages before comparing, it sits
outside that chain and can break it in either direction. A region that is 80%
perfect and 20% wildly wrong passes `majority` while the outliers drag the
mean past the tolerance; a region split exactly in half can pass `average` on
a mean that lands on the tolerance while failing `majority`, since half is not
a majority.

That is why `majority` is hextol's default: it is robust to anti-aliased edges
without letting a half-wrong region through on a flattering average.

Prefer the desktop version? `uv sync --extra dev` in the repo, then `uv run
hextol-gui`: the same two tabs, with a freeze-frame magnifier loupe for
pixel-perfect screen picking and a drag-out region capture.
