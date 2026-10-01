// Prior-shift lab: tell the model what the new base rate is (Bayes odds correction) and watch calls and profit change.
// Usage: <div class="prior-shift-lab" data-src="/series/x/artifacts/prior_shift_lab.json" data-cost="1" data-value="8"></div>
// Data format: {"y":[...], "train_rate":0.064, "test_rate":0.308, "models":{"name":[scores...]}}
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const svgEl = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); parent.appendChild(n); return n; };
  const fmt = (x, d = 0) => x.toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d });

  function build(root, data) {
    const COST = +root.dataset.cost || 1, VALUE = +root.dataset.value || 8, T = 1 / VALUE;
    const names = Object.keys(data.models), y = data.y, n = y.length;
    const old = data.train_rate, truth = data.test_rate;
    let name = names[0], assumed = old;
    const shift = (p, nw) => { const q = Math.min(Math.max(p, 1e-6), 1 - 1e-6); const o = q / (1 - q) * (nw / (1 - nw)) / (old / (1 - old)); return o / (1 + o); };
    function evalAt(nw) {
      const s = data.models[name]; let calls = 0, tp = 0, sum = 0;
      for (let i = 0; i < n; i++) { const p = shift(s[i], nw); sum += p; if (p >= T) { calls++; tp += y[i]; } }
      return { calls, profit: VALUE * tp - COST * calls, meanP: sum / n, prec: calls ? tp / calls : 1 };
    }

    root.classList.add('tl'); root.innerHTML = `
      <div class="tl-controls">
        <label>Model <select class="ps-model">${names.map((m) => `<option>${m}</option>`).join('')}</select></label>
        <label class="tl-slider">Base rate you tell the model: <strong class="ps-val"></strong>
          <input class="tl-range ps-range" type="range" min="0.02" max="0.5" step="0.002"></label>
        <div class="tl-buttons"><button type="button" class="ps-old">Training era (${fmt(old * 100, 1)}%)</button><button type="button" class="ps-new">Actual future (${fmt(truth * 100, 1)}%)</button></div>
      </div>
      <div class="tl-readout ps-readout"></div>
      <figure style="margin:0"><figcaption>Profit at threshold 1/${VALUE} as a function of the base rate you assume</figcaption><svg class="ps-svg" viewBox="0 0 640 230" role="img" aria-label="Profit versus assumed base rate"></svg></figure>`;
    const $ = (s) => root.querySelector(s), range = $('.ps-range'), svg = $('.ps-svg');
    const rates = []; for (let r = 0.02; r <= 0.5001; r += 0.01) rates.push(r);
    const M = { l: 52, r: 12, t: 12, b: 34 }, W = 640, H = 230, iw = W - M.l - M.r, ih = H - M.t - M.b;

    function draw() {
      const cur = evalAt(assumed), curve = rates.map((r) => evalAt(r).profit);
      const hi = Math.max(...curve, cur.profit), lo = Math.min(0, ...curve, cur.profit);
      const X = (r) => M.l + (r - 0.02) / 0.48 * iw, Y = (v) => M.t + (1 - (v - lo) / (hi - lo)) * ih;
      $('.ps-val').textContent = fmt(assumed * 100, 1) + '%';
      range.value = assumed;
      $('.ps-readout').innerHTML = `<dl class="tl-stats">
        <div><dt>Calls at 1/${VALUE}</dt><dd>${fmt(cur.calls)}</dd></div>
        <div><dt>Mean predicted p</dt><dd>${fmt(cur.meanP * 100, 1)}%</dd></div>
        <div><dt>Profit</dt><dd class="${cur.profit >= 0 ? 'pos' : 'neg'}">${cur.profit >= 0 ? '+' : ''}${fmt(cur.profit)}</dd></div></dl>
        <p style="margin:0;max-width:30rem;color:var(--muted)">The true rate in this period is ${fmt(truth * 100, 1)}%. Ranking (AP, AUC) never changes here, only who crosses the threshold.</p>`;
      svg.innerHTML = '';
      svgEl('rect', { x: M.l, y: M.t, width: iw, height: ih, class: 'tl-frame' }, svg);
      [0, 0.1, 0.2, 0.3, 0.4, 0.5].forEach((r) => { const x = X(Math.max(r, 0.02)); svgEl('line', { x1: x, x2: x, y1: M.t, y2: M.t + ih, class: 'tl-grid' }, svg); svgEl('text', { x, y: H - 16, class: 'tl-tick', 'text-anchor': 'middle' }, svg).textContent = fmt(r * 100) + '%'; });
      [lo, (lo + hi) / 2, hi].forEach((v) => { svgEl('text', { x: M.l - 5, y: Y(v) + 3, class: 'tl-tick', 'text-anchor': 'end' }, svg).textContent = fmt(v); });
      svgEl('text', { x: M.l + iw / 2, y: H - 3, class: 'tl-axis', 'text-anchor': 'middle' }, svg).textContent = 'base rate assumed by the correction';
      svgEl('path', { d: rates.map((r, i) => (i ? 'L' : 'M') + X(r).toFixed(1) + ' ' + Y(curve[i]).toFixed(1)).join(' '), class: 'tl-curve' }, svg);
      [[old, 'training era'], [truth, 'actual']].forEach(([r, lab], i) => {
        svgEl('line', { x1: X(r), x2: X(r), y1: M.t, y2: M.t + ih, class: i ? 'tl-be-line' : 'tl-diag' }, svg);
        svgEl('text', { x: X(r) + 4, y: M.t + 11, class: 'tl-tick' }, svg).textContent = lab;
      });
      svgEl('circle', { cx: X(assumed), cy: Y(cur.profit), r: 5, class: 'tl-dot' }, svg);
    }
    range.addEventListener('input', () => { assumed = +range.value; draw(); });
    $('.ps-model').addEventListener('change', (e) => { name = e.target.value; draw(); });
    $('.ps-old').addEventListener('click', () => { assumed = old; draw(); });
    $('.ps-new').addEventListener('click', () => { assumed = truth; draw(); });
    draw();
  }

  const base = document.currentScript ? new URL(document.currentScript.src).pathname.replace(/js\/prior-shift-lab\.js$/, '') : '/';
  document.querySelectorAll('.prior-shift-lab').forEach((root) => {
    root.textContent = 'Loading scores…';
    fetch(base + root.dataset.src.replace(/^\//, '')).then((r) => r.json()).then((d) => build(root, d))
      .catch(() => { root.textContent = 'Could not load the interactive lab.'; });
  });
})();
