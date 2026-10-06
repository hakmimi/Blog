// Threshold lab: drag a decision threshold and watch ROC, precision-recall, simulated contribution and the confusion matrix respond (retrospective simulation, illustrative prices).
// Usage: <div class="threshold-lab" data-src="/series/x/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
// Data format: {"y":[0,1,...], "models":{"name":[scores...]}}
(function () {
  const TEXT = {
    en: { model: 'Model', price1: 'Illustrative price list: a subscription is worth', price2: 'contacts (a contact costs 1)', threshold: 'Threshold',
      be: 'Break-even (1/value)', best: 'Best on this sample', def: 'Default 0.5', called: 'Called', notCalled: 'Not called', subscribes: 'Subscribes', declines: 'Declines',
      hits: 'hits', missed: 'missed', wasted: 'wasted contacts', skipped: 'correctly skipped', selected: 'Records selected', precision: 'Precision', recall: 'Recall', contribution: 'Simulated contribution',
      roc: 'ROC curve', pr: 'Precision vs recall', profit: 'Simulated contribution vs threshold', hist: 'Score distribution',
      fpr: 'false positive rate', tpr: 'recall (TPR)', rec: 'recall', prec: 'precision', thr: 'threshold', contr: 'contribution', pp: 'predicted probability', rs: 'records (√ scale)',
      loading: 'Loading scores…', fail: 'Could not load the interactive lab.' },
    he: { model: 'מודל', price1: 'רשימת מחירים להמחשה: הרשמה שווה', price2: 'שיחות (שיחה עולה 1)', threshold: 'סף',
      be: 'נקודת איזון (1/ערך)', best: 'הטוב ביותר במדגם הזה', def: 'ברירת מחדל 0.5', called: 'התקשרנו', notCalled: 'לא התקשרנו', subscribes: 'נרשמים', declines: 'לא נרשמים',
      hits: 'פגיעות', missed: 'הוחמצו', wasted: 'שיחות מבוזבזות', skipped: 'דולגו נכון', selected: 'רשומות שנבחרו', precision: 'דיוק חיובי (precision)', recall: 'שלמות (recall)', contribution: 'תרומה מדומה',
      roc: 'עקומת ROC', pr: 'דיוק חיובי מול שלמות', profit: 'תרומה מדומה מול סף', hist: 'התפלגות הציונים',
      fpr: 'שיעור חיוביים שגויים', tpr: 'שלמות (TPR)', rec: 'שלמות', prec: 'דיוק חיובי', thr: 'סף', contr: 'תרומה', pp: 'הסתברות חזויה', rs: 'רשומות (סקאלת √)',
      loading: 'טוען ציונים…', fail: 'לא ניתן היה לטעון את המעבדה האינטראקטיבית.' },
  };
  const textFor = (root) => TEXT[root.dataset.lang === 'he' ? 'he' : 'en'];
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs = {}, parent) => {
    const n = tag in { svg: 1, path: 1, line: 1, circle: 1, rect: 1, text: 1, g: 1 } ? document.createElementNS(NS, tag) : document.createElement(tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  };
  const fmt = (x, d = 0) => x.toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d });

  function build(root, data) {
    const T = textFor(root);
    const COST = +root.dataset.cost || 1;
    let VALUE = +root.dataset.value || 8;
    const names = Object.keys(data.models);
    const y = data.y, n = y.length, P = y.reduce((a, b) => a + b, 0);
    let name = names[0], t = 1 / VALUE;
    let order, sortedScores, cumTP;

    function prepare() {
      const s = data.models[name];
      order = Array.from({ length: n }, (_, i) => i).sort((a, b) => s[b] - s[a]);
      sortedScores = order.map((i) => s[i]);
      cumTP = new Int32Array(n + 1);
      for (let k = 0; k < n; k++) cumTP[k + 1] = cumTP[k] + y[order[k]];
    }
    // number of records with score >= thr (sortedScores is descending)
    function callsAt(thr) {
      let lo = 0, hi = n;
      while (lo < hi) { const m = (lo + hi) >> 1; if (sortedScores[m] >= thr) lo = m + 1; else hi = m; }
      return lo;
    }
    function stats(thr) {
      const k = callsAt(thr), tp = cumTP[k], fp = k - tp, fn = P - tp, tn = n - P - fp;
      return { k, tp, fp, fn, tn, prec: k ? tp / k : 1, rec: tp / P, fpr: fp / (n - P), profit: VALUE * tp - COST * k };
    }

    root.innerHTML = '';
    root.classList.add('tl');
    const controls = el('div', { class: 'tl-controls' }, root);
    controls.innerHTML = `
      <label>${T.model} <select class="tl-model">${names.map((m) => `<option>${m}</option>`).join('')}</select></label>
      <label>${T.price1} <select class="tl-value"><option>2</option><option>4</option><option selected>8</option><option>16</option></select> ${T.price2}</label>
      <label class="tl-slider">${T.threshold} <strong class="tl-tval"></strong>
        <input class="tl-range" type="range" min="0.01" max="0.9" step="0.005"></label>
      <div class="tl-buttons"><button type="button" class="tl-be">${T.be}</button><button type="button" class="tl-best">${T.best}</button><button type="button" class="tl-def">${T.def}</button></div>`;
    const readout = el('div', { class: 'tl-readout' }, root);
    const panels = el('div', { class: 'tl-panels' }, root);
    const mk = (title) => { const f = el('figure', {}, panels); el('figcaption', {}, f).textContent = title; return el('svg', { viewBox: '0 0 300 220', role: 'img', 'aria-label': title }, f); };
    const svgRoc = mk(T.roc), svgPr = mk(T.pr), svgProfit = mk(T.profit), svgHist = mk(T.hist);

    const $ = (s) => root.querySelector(s);
    const range = $('.tl-range'), tval = $('.tl-tval');

    const M = { l: 38, r: 10, t: 10, b: 30 }, W = 300, H = 220, iw = W - M.l - M.r, ih = H - M.t - M.b;
    function axes(svg, xl, yl, xt, yt) {
      svg.innerHTML = '';
      el('rect', { x: M.l, y: M.t, width: iw, height: ih, class: 'tl-frame' }, svg);
      xt.forEach(([v, lab]) => { const x = M.l + v * iw; el('line', { x1: x, x2: x, y1: M.t, y2: M.t + ih, class: 'tl-grid' }, svg); el('text', { x, y: H - 16, class: 'tl-tick', 'text-anchor': 'middle' }, svg).textContent = lab; });
      yt.forEach(([v, lab]) => { const yy = M.t + (1 - v) * ih; el('line', { x1: M.l, x2: M.l + iw, y1: yy, y2: yy, class: 'tl-grid' }, svg); el('text', { x: M.l - 5, y: yy + 3, class: 'tl-tick', 'text-anchor': 'end' }, svg).textContent = lab; });
      el('text', { x: M.l + iw / 2, y: H - 3, class: 'tl-axis', 'text-anchor': 'middle' }, svg).textContent = xl;
      el('text', { x: 10, y: M.t + ih / 2, class: 'tl-axis', 'text-anchor': 'middle', transform: `rotate(-90 10 ${M.t + ih / 2})` }, svg).textContent = yl;
    }
    const X = (v) => M.l + v * iw, Y = (v) => M.t + (1 - v) * ih;
    const pathOf = (pts, cls, svg) => el('path', { d: pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' '), class: cls }, svg);
    const dot = (x, yv, svg) => el('circle', { cx: x, cy: yv, r: 5, class: 'tl-dot' }, svg);
    const ticks01 = [[0, '0'], [0.25, ''], [0.5, '.5'], [0.75, ''], [1, '1']];

    // curve points sampled over the sorted list (every ~n/250 customers)
    function curve() {
      const pts = [], step = Math.max(1, Math.floor(n / 250));
      for (let k = 0; k <= n; k += step) pts.push(k);
      if (pts[pts.length - 1] !== n) pts.push(n);
      return pts;
    }

    function draw() {
      const cur = stats(t), ks = curve();
      tval.textContent = t.toFixed(3);
      range.value = t;
      // readout
      readout.innerHTML = `
        <div class="tl-cm"><div></div><b>${T.called}</b><b>${T.notCalled}</b>
          <b>${T.subscribes}</b><span class="good">${fmt(cur.tp)}<small>${T.hits}</small></span><span class="bad">${fmt(cur.fn)}<small>${T.missed}</small></span>
          <b>${T.declines}</b><span class="bad">${fmt(cur.fp)}<small>${T.wasted}</small></span><span class="good">${fmt(cur.tn)}<small>${T.skipped}</small></span></div>
        <dl class="tl-stats">
          <div><dt>${T.selected}</dt><dd>${fmt(cur.k)}</dd></div>
          <div><dt>${T.precision}</dt><dd>${fmt(cur.prec * 100, 1)}%</dd></div>
          <div><dt>${T.recall}</dt><dd>${fmt(cur.rec * 100, 1)}%</dd></div>
          <div><dt>${T.contribution}</dt><dd class="${cur.profit >= 0 ? 'pos' : 'neg'}">${cur.profit >= 0 ? '+' : ''}${fmt(cur.profit)}</dd></div>
        </dl>`;
      // ROC
      axes(svgRoc, T.fpr, T.tpr, ticks01, ticks01);
      el('line', { x1: X(0), y1: Y(0), x2: X(1), y2: Y(1), class: 'tl-diag' }, svgRoc);
      pathOf(ks.map((k) => [X((k - cumTP[k]) / (n - P)), Y(cumTP[k] / P)]), 'tl-curve', svgRoc);
      dot(X(cur.fpr), Y(cur.rec), svgRoc);
      // PR
      axes(svgPr, T.rec, T.prec, ticks01, ticks01);
      el('line', { x1: X(0), x2: X(1), y1: Y(P / n), y2: Y(P / n), class: 'tl-diag' }, svgPr);
      pathOf(ks.filter((k) => k > 0).map((k) => [X(cumTP[k] / P), Y(cumTP[k] / k)]), 'tl-curve', svgPr);
      dot(X(cur.rec), Y(cur.prec), svgPr);
      // Profit vs threshold
      const grid = []; for (let th = 0.01; th <= 0.9001; th += 0.01) grid.push(th);
      const profits = grid.map((th) => stats(th).profit), best = Math.max(...profits), bestT = grid[profits.indexOf(best)];
      const lo = Math.min(0, ...profits), hi = Math.max(best, cur.profit, 1), norm = (v) => (v - lo) / (hi - lo);
      const XT = (th) => X((th - 0.01) / 0.89);
      axes(svgProfit, T.thr, T.contr, [[0, '0'], [(0.25 - 0.01) / 0.89, '.25'], [(0.5 - 0.01) / 0.89, '.5'], [(0.75 - 0.01) / 0.89, '.75']],
        [[norm(0), '0'], [1, fmt(hi)]]);
      el('line', { x1: XT(1 / VALUE), x2: XT(1 / VALUE), y1: M.t, y2: M.t + ih, class: 'tl-be-line' }, svgProfit);
      pathOf(grid.map((th, i) => [XT(th), Y(norm(profits[i]))]), 'tl-curve', svgProfit);
      el('circle', { cx: XT(bestT), cy: Y(norm(best)), r: 3.5, class: 'tl-best-dot' }, svgProfit);
      el('line', { x1: XT(t), x2: XT(t), y1: M.t, y2: M.t + ih, class: 'tl-cur-line' }, svgProfit);
      dot(XT(Math.min(Math.max(t, 0.01), 0.9)), Y(norm(cur.profit)), svgProfit);
      draw.bestT = bestT;
      // histogram of scores by class (log-ish: 20 bins on 0..1)
      const bins = 20, h0 = new Array(bins).fill(0), h1 = new Array(bins).fill(0), s = data.models[name];
      for (let i = 0; i < n; i++) (y[i] ? h1 : h0)[Math.min(bins - 1, Math.floor(s[i] * bins))]++;
      const mx = Math.max(...h0, ...h1), sc = (v) => Math.sqrt(v / mx);
      axes(svgHist, T.pp, T.rs, ticks01, []);
      const bw = iw / bins;
      for (let b = 0; b < bins; b++) {
        el('rect', { x: M.l + b * bw + 1, y: Y(sc(h0[b])), width: bw / 2 - 1, height: ih * sc(h0[b]), class: 'tl-h0' }, svgHist);
        el('rect', { x: M.l + b * bw + bw / 2, y: Y(sc(h1[b])), width: bw / 2 - 1, height: ih * sc(h1[b]), class: 'tl-h1' }, svgHist);
      }
      el('line', { x1: X(t), x2: X(t), y1: M.t, y2: M.t + ih, class: 'tl-cur-line' }, svgHist);
    }

    range.addEventListener('input', () => { t = +range.value; draw(); });
    $('.tl-model').addEventListener('change', (e) => { name = e.target.value; prepare(); draw(); });
    $('.tl-value').addEventListener('change', (e) => { VALUE = +e.target.value; draw(); });
    $('.tl-be').addEventListener('click', () => { t = Math.min(0.9, Math.max(0.01, 1 / VALUE)); draw(); });
    $('.tl-best').addEventListener('click', () => { draw(); t = draw.bestT; draw(); });
    $('.tl-def').addEventListener('click', () => { t = 0.5; draw(); });
    prepare(); draw();
  }

  const base = document.currentScript ? new URL(document.currentScript.src).pathname.replace(/js\/threshold-lab\.js$/, '') : '/';
  document.querySelectorAll('.threshold-lab').forEach((root) => {
    root.textContent = textFor(root).loading;
    fetch(base + root.dataset.src.replace(/^\//, '')).then((r) => r.json()).then((d) => build(root, d))
      .catch(() => { root.textContent = textFor(root).fail; });
  });
})();
