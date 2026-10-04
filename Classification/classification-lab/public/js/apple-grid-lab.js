// Grid lab: cut the apple plane into k x k cells and watch the grid memorise the training apples while test accuracy stalls.
// Usage: <div class="apple-grid-lab" data-src="/series/x/artifacts/apple_grid.json"></div>
// Data format: {"train":{"x":[],"y":[],"label":[]},"test":{...},"logistic":{"intercept":b,"coef":[w1,w2]}}
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs = {}, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  };
  const GREEN = [64, 160, 90], RED = [214, 84, 80];
  const mix = (p) => GREEN.map((g, i) => Math.round(RED[i] + (g - RED[i]) * p));     // p = share of green apples

  function build(root, data) {
    const S = 360, M = 34, IW = S - M - 8, sigmoid = (z) => 1 / (1 + Math.exp(-z));
    const L = data.logistic, prob = (r, a) => sigmoid(L.intercept + L.coef[0] * r + L.coef[1] * a);
    const tr = data.train, te = data.test, n = tr.x.length;
    const majority = tr.label.reduce((a, b) => a + b, 0) * 2 >= n ? 1 : 0;
    let k = 2, mode = 'rate', showLine = true, showTest = false;

    root.innerHTML = '';
    root.classList.add('ag');
    const controls = document.createElement('div');
    controls.className = 'ag-controls';
    controls.innerHTML = `
      <label class="ag-slider">Cuts per axis <strong class="ag-k"></strong>
        <input class="ag-range" type="range" min="1" max="12" step="1" value="${k}"></label>
      <label>Colour cells by
        <select class="ag-mode"><option value="rate">share of green apples (the grid)</option><option value="prob">logistic probability at the cell centre</option></select></label>
      <label class="ag-check"><input type="checkbox" class="ag-line" checked> logistic decision line</label>
      <label class="ag-check"><input type="checkbox" class="ag-test"> show test apples</label>`;
    root.appendChild(controls);
    const body = document.createElement('div');
    body.className = 'ag-body';
    root.appendChild(body);
    const svg = el('svg', { viewBox: `0 0 ${S} ${S}`, role: 'img', 'aria-label': 'Apples on a redness and acidity plane, cut into a grid' });
    body.appendChild(svg);
    const side = document.createElement('div');
    side.className = 'ag-side';
    body.appendChild(side);
    const $ = (s) => root.querySelector(s);
    const X = (v) => M + v * IW, Y = (v) => 8 + (1 - v) * IW;

    function cellOf(v) { return Math.min(k - 1, Math.floor(v * k)); }
    function evaluate() {
      const count = new Int32Array(k * k), green = new Int32Array(k * k);
      for (let i = 0; i < n; i++) { const c = cellOf(tr.y[i]) * k + cellOf(tr.x[i]); count[c]++; green[c] += tr.label[i]; }
      const predOf = (c) => (count[c] ? (green[c] * 2 >= count[c] ? 1 : 0) : majority);
      const acc = (d) => { let ok = 0; const m = d.x.length; for (let i = 0; i < m; i++) ok += predOf(cellOf(d.y[i]) * k + cellOf(d.x[i])) === d.label[i]; return ok / m; };
      const sorted = Array.from(count).sort((a, b) => a - b), h = sorted.length >> 1;
      const median = sorted.length % 2 ? sorted[h] : (sorted[h - 1] + sorted[h]) / 2;
      return { count, green, empty: sorted.filter((v) => v === 0).length, median, train: acc(tr), test: acc(te) };
    }
    function logisticAcc(d) { let ok = 0; const m = d.x.length; for (let i = 0; i < m; i++) ok += (prob(d.x[i], d.y[i]) >= 0.5 ? 1 : 0) === d.label[i]; return ok / m; }
    const lrTrain = logisticAcc(tr), lrTest = logisticAcc(te);
    const pct = (v) => (100 * v).toFixed(1) + '%';

    function draw() {
      const ev = evaluate();
      $('.ag-k').textContent = `${k} (${k * k} cell${k === 1 ? '' : 's'})`;
      svg.innerHTML = '';
      el('rect', { x: M, y: 8, width: IW, height: IW, class: 'ag-frame' }, svg);
      const w = IW / k;
      for (let r = 0; r < k; r++) for (let c = 0; c < k; c++) {
        const i = r * k + c, cnt = ev.count[i];
        let fill, op;
        if (mode === 'prob') { fill = `rgb(${mix(prob((c + 0.5) / k, (r + 0.5) / k))})`; op = 0.45; }
        else if (cnt === 0) { fill = 'var(--muted)'; op = 0.18; }
        else { fill = `rgb(${mix(ev.green[i] / cnt)})`; op = 0.25 + 0.5 * Math.min(1, cnt / 12); }
        el('rect', { x: M + c * w, y: 8 + (k - 1 - r) * w, width: w, height: w, fill, 'fill-opacity': op, class: 'ag-cell' }, svg);
      }
      for (let j = 1; j < k; j++) {
        el('line', { x1: X(j / k), x2: X(j / k), y1: 8, y2: 8 + IW, class: 'ag-cut' }, svg);
        el('line', { x1: M, x2: M + IW, y1: Y(j / k), y2: Y(j / k), class: 'ag-cut' }, svg);
      }
      const dots = (d, cls, rad) => { for (let i = 0; i < d.x.length; i++) el('circle', { cx: X(d.x[i]), cy: Y(d.y[i]), r: rad, class: `${cls} ${d.label[i] ? 'ag-g' : 'ag-r'}` }, svg); };
      dots(tr, 'ag-pt', 2.6);
      if (showTest) dots(te, 'ag-pt ag-te', 2.6);
      if (showLine) {            // boundary: intercept + w1*red + w2*acid = 0
        const pts = [];
        for (const rd of [0, 1]) { const a = -(L.intercept + L.coef[0] * rd) / L.coef[1]; if (a >= 0 && a <= 1) pts.push([rd, a]); }
        for (const ac of [0, 1]) { const rd = -(L.intercept + L.coef[1] * ac) / L.coef[0]; if (rd >= 0 && rd <= 1) pts.push([rd, ac]); }
        if (pts.length >= 2) el('line', { x1: X(pts[0][0]), y1: Y(pts[0][1]), x2: X(pts[1][0]), y2: Y(pts[1][1]), class: 'ag-line-d' }, svg);
      }
      el('text', { x: M + IW / 2, y: S - 2, class: 'ag-axis', 'text-anchor': 'middle' }, svg).textContent = 'redness of the skin →';
      const yl = el('text', { x: 9, y: 8 + IW / 2, class: 'ag-axis', 'text-anchor': 'middle', transform: `rotate(-90 9 ${8 + IW / 2})` }, svg);
      yl.textContent = 'acidity →';
      const gap = ev.train - ev.test;
      side.innerHTML = `
        <dl class="ag-stats">
          <div><dt>Cells</dt><dd>${k * k}</dd></div>
          <div><dt>Empty cells</dt><dd class="${ev.empty ? 'neg' : ''}">${ev.empty}</dd></div>
          <div><dt>Median apples per cell</dt><dd>${ev.median}</dd></div>
        </dl>
        <table class="ag-table">
          <thead><tr><th></th><th>train</th><th>test</th></tr></thead>
          <tbody>
            <tr><th>Grid (${k}×${k})</th><td>${pct(ev.train)}</td><td>${pct(ev.test)}</td></tr>
            <tr><th>Logistic line</th><td>${pct(lrTrain)}</td><td>${pct(lrTest)}</td></tr>
          </tbody>
        </table>
        <p class="ag-note">Train minus test for the grid: <strong>${(100 * gap).toFixed(1)} points</strong>. An empty cell predicts the majority class of the training apples. Accuracy on 400 test apples moves by about ±1.7 points from chance alone, so read the trend, not single steps.</p>`;
    }
    $('.ag-range').addEventListener('input', (e) => { k = +e.target.value; draw(); });
    $('.ag-mode').addEventListener('change', (e) => { mode = e.target.value; draw(); });
    $('.ag-line').addEventListener('change', (e) => { showLine = e.target.checked; draw(); });
    $('.ag-test').addEventListener('change', (e) => { showTest = e.target.checked; draw(); });
    draw();
  }

  const base = document.currentScript ? new URL(document.currentScript.src).pathname.replace(/js\/apple-grid-lab\.js$/, '') : '/';
  document.querySelectorAll('.apple-grid-lab').forEach((root) => {
    const src = root.dataset.src;
    root.textContent = 'Loading apples…';
    fetch(base + src.replace(/^\//, '')).then((r) => r.json()).then((d) => build(root, d)).catch(() => { root.textContent = 'The widget data could not be loaded.'; });
  });
})();
