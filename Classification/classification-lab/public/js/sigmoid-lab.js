// Sigmoid lab: see how a straight line z = b + w*x becomes a probability p = 1/(1+e^-z) that moves between 0 and 1.
// Usage: <div class="sigmoid-lab"></div>   (no data file: everything is computed in the browser)
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs = {}, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  };
  const sig = (z) => 1 / (1 + Math.exp(-z));
  const f = (v, d = 2) => (Math.abs(v) < 5e-3 && v !== 0 && d === 2 ? v.toExponential(1) : v.toFixed(d));

  const TEXT = {
    en: { slope: 'Slope', shift: 'Shift (bias)', ev: 'Evidence x', sweep: '▶ Sweep x', pause: '⏸ Pause', steeper: 'Steeper', flip: 'Flip sign', reset: 'Reset',
      t1: '1. The straight line', h1: 'z = b + w·x can be any number', t2: '2. The sigmoid', h2: 'p = 1 / (1 + e^−z) stays between 0 and 1',
      xax: 'x (evidence)', zax: 'z (log-odds)', pax: 'p (probability)', odds: 'odds p/(1−p)', slopeR: 'slope dp/dx', oddsx: 'odds × per +1 in x',
      steep: 'Near z = 0 the curve is steepest: a small change in the evidence moves the probability a lot.',
      flat: (end) => 'Far from z = 0 the curve is flat: more evidence barely changes a probability that is already close to ' + end + '.',
      tail: ' The line on the left keeps growing; the curve on the right never leaves 0 to 1.', gold: (x) => ' The gold dot, x = ' + x + ', is where p = 0.5 (the decision boundary).' },
    he: { slope: 'שיפוע', shift: 'הזזה (bias)', ev: 'ראיה x', sweep: '▶ סרוק x', pause: '⏸ השהיה', steeper: 'תלול יותר', flip: 'הפוך סימן', reset: 'איפוס',
      t1: '1. הקו הישר', h1: 'z = b + w·x יכול להיות כל מספר', t2: '2. הסיגמואיד', h2: 'p = 1 / (1 + e^−z) נשאר בין 0 ל-1',
      xax: 'x (ראיה)', zax: 'z (לוג-סיכויים)', pax: 'p (הסתברות)', odds: 'סיכויים p/(1−p)', slopeR: 'שיפוע dp/dx', oddsx: 'סיכויים × לכל +1 ב-x',
      steep: 'ליד z = 0 העקומה תלולה ביותר: שינוי קטן בראיה מזיז את ההסתברות הרבה.',
      flat: (end) => 'רחוק מ-z = 0 העקומה שטוחה: ראיות נוספות כמעט לא משנות הסתברות שכבר קרובה ל-' + end + '.',
      tail: ' הקו משמאל ממשיך לגדול; העקומה מימין אף פעם לא יוצאת מהטווח 0 עד 1.', gold: (x) => ' הנקודה הזהובה, x = ' + x + ', היא איפה ש-p = 0.5 (גבול ההחלטה).' },
  };

  function build(root) {
    const T = TEXT[root.dataset.lang === 'he' ? 'he' : 'en'];
    let w = 1.5, b = 0, x = 1, timer = null;
    const XMIN = -6, XMAX = 6, W = 400, H = 250, M = { l: 40, r: 12, t: 12, b: 30 };
    const iw = W - M.l - M.r, ih = H - M.t - M.b;
    const X = (v) => M.l + ((v - XMIN) / (XMAX - XMIN)) * iw;

    root.innerHTML = '';
    root.classList.add('sg');
    const controls = document.createElement('div');
    controls.className = 'sg-controls';
    controls.innerHTML = `
      <label>${T.slope} <strong class="sg-wv"></strong><input class="sg-w" type="range" min="-4" max="4" step="0.1" value="${w}"></label>
      <label>${T.shift} <strong class="sg-bv"></strong><input class="sg-b" type="range" min="-6" max="6" step="0.1" value="${b}"></label>
      <label>${T.ev} <strong class="sg-xv"></strong><input class="sg-x" type="range" min="${XMIN}" max="${XMAX}" step="0.05" value="${x}"></label>
      <div class="sg-buttons"><button type="button" class="sg-play">${T.sweep}</button><button type="button" class="sg-steep">${T.steeper}</button><button type="button" class="sg-flip">${T.flip}</button><button type="button" class="sg-reset">${T.reset}</button></div>`;
    root.appendChild(controls);
    const read = document.createElement('div');
    read.className = 'sg-read';
    root.appendChild(read);
    const panels = document.createElement('div');
    panels.className = 'sg-panels';
    root.appendChild(panels);
    const mk = (title, hint) => {
      const fg = document.createElement('figure');
      const cap = document.createElement('figcaption');
      cap.innerHTML = `<strong>${title}</strong> <span>${hint}</span>`;
      fg.appendChild(cap);
      const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': title });
      fg.appendChild(svg);
      panels.appendChild(fg);
      return svg;
    };
    const svgZ = mk(T.t1, T.h1);
    const svgP = mk(T.t2, T.h2);
    const $ = (s) => root.querySelector(s);

    function frame(svg, ymin, ymax, yticks, ylabel) {
      svg.innerHTML = '';
      const Y = (v) => M.t + (1 - (v - ymin) / (ymax - ymin)) * ih;
      el('rect', { x: M.l, y: M.t, width: iw, height: ih, class: 'sg-frame' }, svg);
      for (let t = -6; t <= 6; t += 2) {
        el('line', { x1: X(t), x2: X(t), y1: M.t, y2: M.t + ih, class: 'sg-grid' }, svg);
        el('text', { x: X(t), y: H - 14, class: 'sg-tick', 'text-anchor': 'middle' }, svg).textContent = t;
      }
      for (const t of yticks) {
        el('line', { x1: M.l, x2: M.l + iw, y1: Y(t), y2: Y(t), class: 'sg-grid' }, svg);
        el('text', { x: M.l - 5, y: Y(t) + 3, class: 'sg-tick', 'text-anchor': 'end' }, svg).textContent = t;
      }
      el('text', { x: M.l + iw / 2, y: H - 1, class: 'sg-axis', 'text-anchor': 'middle' }, svg).textContent = T.xax;
      el('text', { x: 10, y: M.t + ih / 2, class: 'sg-axis', 'text-anchor': 'middle', transform: `rotate(-90 10 ${M.t + ih / 2})` }, svg).textContent = ylabel;
      return Y;
    }
    function curve(svg, fn, Y, cls, ymin, ymax) {
      let d = '';
      for (let i = 0; i <= 240; i++) {
        const xv = XMIN + ((XMAX - XMIN) * i) / 240, yv = Math.max(ymin, Math.min(ymax, fn(xv)));
        d += (i ? 'L' : 'M') + X(xv).toFixed(1) + ' ' + Y(yv).toFixed(1);
      }
      el('path', { d, class: cls }, svg);
    }

    function draw() {
      const z = b + w * x, p = sig(z), slope = p * (1 - p) * w;
      $('.sg-wv').textContent = f(w, 1);
      $('.sg-bv').textContent = f(b, 1);
      $('.sg-xv').textContent = f(x, 2);
      // 1. line
      const ZMIN = -8, ZMAX = 8, YZ = frame(svgZ, ZMIN, ZMAX, [-8, -4, 0, 4, 8], T.zax);
      curve(svgZ, (v) => b + w * v, YZ, 'sg-line', ZMIN, ZMAX);
      el('line', { x1: X(x), x2: X(x), y1: YZ(0), y2: YZ(Math.max(ZMIN, Math.min(ZMAX, z))), class: 'sg-drop' }, svgZ);
      el('circle', { cx: X(x), cy: YZ(Math.max(ZMIN, Math.min(ZMAX, z))), r: 5, class: 'sg-dot' }, svgZ);
      // 2. sigmoid
      const YP = frame(svgP, 0, 1, [0, 0.25, 0.5, 0.75, 1], T.pax);
      el('rect', { x: M.l, y: YP(0.5), width: iw, height: ih / 2, class: 'sg-low' }, svgP);
      el('line', { x1: M.l, x2: M.l + iw, y1: YP(0.5), y2: YP(0.5), class: 'sg-half' }, svgP);
      curve(svgP, (v) => sig(b + w * v), YP, 'sg-curve', 0, 1);
      // tangent at the current point (slope in p per unit x), clipped to the frame
      const t0 = Math.max(XMIN, x - 1.2), t1 = Math.min(XMAX, x + 1.2);
      const yy = (v) => Math.max(0, Math.min(1, p + slope * (v - x)));
      el('line', { x1: X(t0), y1: YP(yy(t0)), x2: X(t1), y2: YP(yy(t1)), class: 'sg-tan' }, svgP);
      el('line', { x1: X(x), x2: X(x), y1: YP(0), y2: YP(p), class: 'sg-drop' }, svgP);
      el('circle', { cx: X(x), cy: YP(p), r: 5.5, class: 'sg-dot' }, svgP);
      const cross = w !== 0 ? -b / w : null;
      if (cross !== null && cross >= XMIN && cross <= XMAX) el('circle', { cx: X(cross), cy: YP(0.5), r: 3.5, class: 'sg-mid' }, svgP);
      read.innerHTML = `
        <dl class="sg-stats">
          <div><dt>z = b + w·x</dt><dd>${f(z)}</dd></div>
          <div><dt>p = σ(z)</dt><dd class="${p >= 0.5 ? 'pos' : 'neg'}">${(100 * p).toFixed(1)}%</dd></div>
          <div><dt>${T.odds}</dt><dd>${z > 7 ? '> 1000' : z < -7 ? '< 0.001' : f(Math.exp(z))}</dd></div>
          <div><dt>${T.slopeR}</dt><dd>${f(slope, 3)}</dd></div>
          <div><dt>${T.oddsx}</dt><dd>${f(Math.exp(w))}</dd></div>
        </dl>
        <p class="sg-note">${Math.abs(z) < 1 ? T.steep : T.flat(z > 0 ? '1' : '0')}${T.tail}${cross !== null && cross >= XMIN && cross <= XMAX ? T.gold(f(cross, 1)) : ''}</p>`;
    }
    const bind = (sel, fn) => $(sel).addEventListener('input', (e) => { fn(+e.target.value); draw(); });
    const sync = () => { $('.sg-w').value = w; $('.sg-b').value = b; $('.sg-x').value = x; };
    bind('.sg-w', (v) => (w = v)); bind('.sg-b', (v) => (b = v)); bind('.sg-x', (v) => { x = v; stop(); });
    function stop() { if (timer) { clearInterval(timer); timer = null; $('.sg-play').textContent = T.sweep; } }
    $('.sg-play').addEventListener('click', () => {
      if (timer) return stop();
      $('.sg-play').textContent = T.pause;
      if (x >= XMAX - 0.1) x = XMIN;
      timer = setInterval(() => { x += 0.08; if (x >= XMAX) { x = XMAX; stop(); } sync(); draw(); }, 30);
    });
    $('.sg-steep').addEventListener('click', () => { w = Math.max(-4, Math.min(4, (w >= 0 ? 1 : -1) * Math.min(4, Math.abs(w) + 1))); sync(); draw(); });
    $('.sg-flip').addEventListener('click', () => { w = -w; sync(); draw(); });
    $('.sg-reset').addEventListener('click', () => { stop(); w = 1.5; b = 0; x = 1; sync(); draw(); });
    draw();
  }
  document.querySelectorAll('.sigmoid-lab').forEach(build);
})();
