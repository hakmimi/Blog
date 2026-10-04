// Fruit lab: a transparent k-nearest-neighbours classifier on synthetic fruit (apple, orange, lemon). English and Hebrew.
// Usage: <div class="fruit-lab-widget" data-lang="he" data-src="/series/classification/artifacts/fruit_points.json"></div>
// Data format: {"features":[...], "scales":{feature:sd}, "points":[{"fruit":"apple","weight_g":..,"sweetness":..,"yellow_hue":..}, ...]}
(function () {
  const NS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs = {}, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, String(attrs[k]));
    if (parent) parent.appendChild(n);
    return n;
  };
  const COLORS = { apple: '#d95f59', orange: '#e89a24', lemon: '#d1b91f' };
  const TEXT = {
    en: { names: { apple: 'Apple', orange: 'Orange', lemon: 'Lemon' }, weight: 'Weight', sweet: 'Sweetness', hue: 'Yellow hue', k: 'Neighbors, k', g: 'g',
      pred: 'Predicted class', neighbors: 'The neighbourhood', xax: 'Weight (grams)', yax: 'Sweetness (1–10)', you: 'Your fruit',
      audit: 'Audit the vote', note: 'Distance uses all three standardized features. The plot shows two; hue still affects the neighbor list.',
      rank: 'Rank', cls: 'Class', dist: 'Distance', vote: 'Vote weight', loading: 'Loading the fruit…', fail: 'The widget data could not be loaded.' },
    he: { names: { apple: 'תפוח', orange: 'תפוז', lemon: 'לימון' }, weight: 'משקל', sweet: 'מתיקות', hue: 'גוון צהוב', k: 'מספר שכנים, k', g: 'גרם',
      pred: 'המחלקה החזויה', neighbors: 'סביבת השכנים', xax: 'משקל (גרם)', yax: 'מתיקות (1–10)', you: 'הפרי שלכם',
      audit: 'בדיקת ההצבעה', note: 'המרחק משתמש בכל שלוש התכונות המתוקננות. הגרף מציג שתיים; הגוון עדיין משפיע על רשימת השכנים.',
      rank: 'דירוג', cls: 'מחלקה', dist: 'מרחק', vote: 'משקל הצבעה', loading: 'טוען את הפירות…', fail: 'לא ניתן היה לטעון את נתוני הווידג׳ט.' },
  };

  function build(root, data) {
    const T = TEXT[root.dataset.lang === 'he' ? 'he' : 'en'];
    const state = { weight_g: 135, sweetness: 5.5, yellow_hue: 55, k: 7 };
    const sx = (v) => 62 + ((v - 55) / (245 - 55)) * 620, sy = (v) => 408 - ((v - 1) / 9) * 345;
    root.innerHTML = '';
    root.classList.add('fl');
    root.innerHTML = `
      <div class="fl-controls">
        <label>${T.weight} <output class="o-w"></output><input class="i-w" type="range" min="60" max="235" step="1" value="${state.weight_g}"></label>
        <label>${T.sweet} <output class="o-s"></output><input class="i-s" type="range" min="1" max="10" step="0.1" value="${state.sweetness}"></label>
        <label>${T.hue} <output class="o-h"></output><input class="i-h" type="range" min="15" max="85" step="1" value="${state.yellow_hue}"></label>
        <label>${T.k} <output class="o-k"></output><input class="i-k" type="range" min="1" max="15" step="2" value="${state.k}"></label>
        <div class="fl-pred" aria-live="polite"><span>${T.pred}</span><strong class="fl-winner"></strong><div class="fl-bars"></div></div>
      </div>
      <div class="fl-chart"><strong>${T.neighbors}</strong><svg viewBox="0 0 720 470" role="img" aria-label="${T.neighbors}"></svg>
        <div class="fl-legend">${Object.keys(COLORS).map((c) => `<span style="--dot:${COLORS[c]}">${T.names[c]}</span>`).join('')}<span class="you">${T.you}</span></div></div>
      <div class="fl-audit"><strong>${T.audit}</strong><p>${T.note}</p>
        <table><thead><tr><th>${T.rank}</th><th>${T.cls}</th><th>${T.dist}</th><th>${T.vote}</th></tr></thead><tbody></tbody></table></div>`;
    const $ = (s) => root.querySelector(s), svg = $('svg');

    function draw() {
      $('.o-w').textContent = `${state.weight_g.toFixed(0)} ${T.g}`;
      $('.o-s').textContent = `${state.sweetness.toFixed(1)} / 10`;
      $('.o-h').textContent = `${state.yellow_hue.toFixed(0)} / 100`;
      $('.o-k').textContent = String(state.k);
      const ranked = data.points.map((p) => {
        let s = 0;
        for (const f of data.features) { const d = (state[f] - p[f]) / data.scales[f]; s += d * d; }
        return { p, distance: Math.sqrt(s) };
      }).sort((a, b) => a.distance - b.distance);
      const near = ranked.slice(0, state.k), nearSet = new Set(near.map((r) => r.p));
      const votes = { apple: 0, orange: 0, lemon: 0 };
      near.forEach((r) => (votes[r.p.fruit] += 1 / (r.distance + 1e-6)));
      const total = Object.values(votes).reduce((a, b) => a + b, 0);
      const winner = Object.entries(votes).sort((a, b) => b[1] - a[1])[0][0];
      const w = $('.fl-winner');
      w.textContent = T.names[winner]; w.style.color = COLORS[winner];
      $('.fl-bars').innerHTML = Object.entries(votes).map(([c, v]) => `<div><span>${T.names[c]}</span><i style="width:${((v / total) * 100).toFixed(1)}%;background:${COLORS[c]}"></i><b>${((v / total) * 100).toFixed(1)}%</b></div>`).join('');
      $('tbody').innerHTML = near.map((r, i) => `<tr><td>${i + 1}</td><td><span class="dot" style="background:${COLORS[r.p.fruit]}"></span>${T.names[r.p.fruit]}</td><td>${r.distance.toFixed(3)}</td><td>${(1 / (r.distance + 1e-6)).toFixed(2)}</td></tr>`).join('');
      svg.innerHTML = '';
      el('line', { x1: 62, y1: 408, x2: 682, y2: 408, class: 'fl-axis' }, svg);
      el('line', { x1: 62, y1: 408, x2: 62, y2: 63, class: 'fl-axis' }, svg);
      el('text', { x: 372, y: 455, 'text-anchor': 'middle', class: 'fl-label' }, svg).textContent = T.xax;
      el('text', { x: 18, y: 235, transform: 'rotate(-90 18 235)', 'text-anchor': 'middle', class: 'fl-label' }, svg).textContent = T.yax;
      near.forEach((r) => el('line', { x1: sx(state.weight_g), y1: sy(state.sweetness), x2: sx(r.p.weight_g), y2: sy(r.p.sweetness), class: 'fl-line' }, svg));
      data.points.forEach((p) => {
        const on = nearSet.has(p);
        el('circle', { cx: sx(p.weight_g), cy: sy(p.sweetness), r: on ? 8 : 5, fill: COLORS[p.fruit], opacity: on ? 0.95 : 0.46, stroke: on ? '#17324d' : 'white', 'stroke-width': on ? 2 : 1 }, svg);
      });
      el('circle', { cx: sx(state.weight_g), cy: sy(state.sweetness), r: 11, fill: '#fff', stroke: '#17324d', 'stroke-width': 4 }, svg);
      el('circle', { cx: sx(state.weight_g), cy: sy(state.sweetness), r: 3.5, fill: '#17324d' }, svg);
    }
    const bind = (sel, key) => $(sel).addEventListener('input', (e) => { state[key] = +e.target.value; draw(); });
    bind('.i-w', 'weight_g'); bind('.i-s', 'sweetness'); bind('.i-h', 'yellow_hue'); bind('.i-k', 'k');
    draw();
  }

  const base = document.currentScript ? new URL(document.currentScript.src).pathname.replace(/js\/fruit-lab\.js$/, '') : '/';
  document.querySelectorAll('.fruit-lab-widget').forEach((root) => {
    const T = TEXT[root.dataset.lang === 'he' ? 'he' : 'en'];
    root.textContent = T.loading;
    fetch(base + root.dataset.src.replace(/^\//, '')).then((r) => r.json()).then((d) => build(root, d)).catch(() => { root.textContent = T.fail; });
  });
})();
