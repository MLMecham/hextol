# Comparison explorer

The same tool as `hextol-gui`, running in your browser. Pick two colors and
drag the tolerance slider: all three methods judge the pair live, so you can
find the right `method` and `tolerance` for your config before writing it.

The **Screen** buttons use the browser EyeDropper API to sample any pixel on
your screen (Chrome and Edge; other browsers can use the color picker).

<div id="hx-demo">
<div class="hx-cards">
<div class="hx-card">
<div class="hx-swatch" id="hx-swatch-A"></div>
<div class="hx-controls">
<span class="hx-side">A</span>
<input class="hx-hex" id="hx-hex-A" value="#3B82F6" spellcheck="false">
<input class="hx-native" id="hx-native-A" type="color" value="#3B82F6" title="Pick">
<button class="hx-btn" id="hx-eye-A" type="button">Screen</button>
</div>
</div>
<span class="hx-vs">vs</span>
<div class="hx-card">
<div class="hx-swatch" id="hx-swatch-B"></div>
<div class="hx-controls">
<span class="hx-side">B</span>
<input class="hx-hex" id="hx-hex-B" value="#2F7BEE" spellcheck="false">
<input class="hx-native" id="hx-native-B" type="color" value="#2F7BEE" title="Pick">
<button class="hx-btn" id="hx-eye-B" type="button">Screen</button>
</div>
</div>
</div>
<canvas id="hx-gradient" width="560" height="30"></canvas>
<div class="hx-tol-row">
<span class="hx-muted">tolerance</span>
<input id="hx-tol" type="range" min="0" max="100" step="0.5" value="10">
<span id="hx-tol-val" class="hx-accent">10.0</span>
</div>
<table class="hx-table">
<thead><tr><th>method</th><th>0-100</th><th>raw</th><th>verdict</th><th></th></tr></thead>
<tbody id="hx-rows"></tbody>
</table>
<div id="hx-status" class="hx-status"></div>
</div>

<style>
#hx-demo{background:#0F1526;border:1px solid #2E3854;border-radius:10px;
  padding:24px;color:#E6EAF2;font-family:"Segoe UI",system-ui,sans-serif;
  max-width:640px}
#hx-demo .hx-cards{display:flex;align-items:center;justify-content:center;gap:14px}
#hx-demo .hx-card{background:#1A2138;border:1px solid #2E3854;border-radius:8px;padding:10px}
#hx-demo .hx-swatch{width:190px;height:110px;background:#232B45;border-radius:4px}
#hx-demo .hx-controls{display:flex;align-items:center;gap:8px;margin-top:10px}
#hx-demo .hx-side{color:#8B93A7;font-weight:600}
#hx-demo .hx-vs{color:#8B93A7;font-weight:600}
#hx-demo .hx-hex{width:86px;background:#232B45;color:#E6EAF2;border:1px solid #2E3854;
  border-radius:4px;padding:4px 6px;font-family:Consolas,monospace;text-align:center}
#hx-demo .hx-hex:focus{outline:none;border-color:#2DD4BF}
#hx-demo .hx-native{width:30px;height:30px;padding:0;border:1px solid #2E3854;
  border-radius:4px;background:#232B45;cursor:pointer}
#hx-demo .hx-btn{background:#232B45;color:#E6EAF2;border:none;border-radius:4px;
  padding:5px 10px;cursor:pointer}
#hx-demo .hx-btn:hover{background:#2DD4BF;color:#0F1526}
#hx-demo .hx-btn:disabled{opacity:.4;cursor:not-allowed}
#hx-demo #hx-gradient{display:block;margin:16px auto 0;border-radius:4px}
#hx-demo .hx-tol-row{display:flex;align-items:center;gap:12px;margin-top:14px}
#hx-demo #hx-tol{flex:1;accent-color:#2DD4BF}
#hx-demo .hx-muted{color:#8B93A7}
#hx-demo .hx-accent{color:#2DD4BF;font-family:Consolas,monospace;width:44px}
#hx-demo .hx-table{width:100%;margin-top:16px;border-collapse:collapse;font-size:.85rem}
#hx-demo .hx-table th{color:#8B93A7;text-align:left;font-size:.7rem;
  text-transform:uppercase;letter-spacing:.05em;padding:4px 8px}
#hx-demo .hx-table td{padding:5px 8px;border-top:1px solid #232B45}
#hx-demo .hx-name{font-weight:600}
#hx-demo .hx-num{font-family:Consolas,monospace}
#hx-demo .hx-raw{font-family:Consolas,monospace;color:#8B93A7}
#hx-demo .hx-hint{color:#8B93A7;font-size:.8rem}
#hx-demo .hx-pill{display:inline-block;min-width:64px;text-align:center;
  border-radius:4px;padding:2px 8px;font-weight:600;font-size:.75rem}
#hx-demo .hx-match{background:#123B2E;color:#4ADE80}
#hx-demo .hx-miss{background:#3F1D25;color:#F87171}
#hx-demo .hx-empty{background:#232B45;color:#8B93A7}
#hx-demo .hx-status{color:#F87171;margin-top:10px;min-height:1.2em;font-size:.85rem}
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

  const rows = {};
  for (const name of Object.keys(METHODS)) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td class="hx-name">' + name + '</td><td class="hx-num">-</td>' +
      '<td class="hx-raw">-</td><td><span class="hx-pill hx-empty">-</span></td>' +
      '<td class="hx-hint">' + METHODS[name].hint + "</td>";
    $("hx-rows").appendChild(tr);
    rows[name] = { dist: tr.children[1], raw: tr.children[2], pill: tr.children[3].firstChild };
  }

  function refresh() {
    const tol = parseFloat($("hx-tol").value);
    $("hx-tol-val").textContent = tol.toFixed(1);
    const a = hexToRgb($("hx-hex-A").value), b = hexToRgb($("hx-hex-B").value);
    if (!a || !b) {
      $("hx-status").textContent = "Invalid color: enter hex like #3B82F6";
      for (const r of Object.values(rows)) {
        r.dist.textContent = "-";
        r.raw.textContent = "-";
        r.pill.textContent = "-";
        r.pill.className = "hx-pill hx-empty";
      }
      return;
    }
    $("hx-status").textContent = "";
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
      const raw = m.raw(a, b), d = (raw / m.max) * 100, ok = d <= tol;
      rows[name].dist.textContent = d.toFixed(1);
      rows[name].raw.textContent = raw.toFixed(1);
      rows[name].pill.textContent = ok ? "MATCH" : "MISS";
      rows[name].pill.className = "hx-pill " + (ok ? "hx-match" : "hx-miss");
    }
  }

  function setColor(side, hex) {
    $("hx-hex-" + side).value = hex.toUpperCase();
    const rgb = hexToRgb(hex);
    if (rgb) $("hx-native-" + side).value = rgbToHex(rgb).toLowerCase();
    refresh();
  }

  for (const side of ["A", "B"]) {
    $("hx-hex-" + side).addEventListener("input", refresh);
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
  $("hx-tol").addEventListener("input", refresh);
  refresh();
})();
</script>

Prefer the desktop version? `uv sync --extra dev` in the repo, then `uv run
hextol-gui`: same tool with a freeze-frame magnifier loupe for pixel-perfect
screen picking.
