/* ==========================================================================
   02805 Social Graphs — interactive charts for the weekly posts
   Hand-rolled SVG, no libraries, same approach as the weeks spider in site.js.
   Colours come from the stylesheet's own tokens, so a chart can never drift
   out of step with the site's palette.

   Each chart is a <div class="chart" data-chart="..."> sitting next to the
   static PNG inside a <figure>. The PNG is what the page shows on its own; if
   this script runs and the data loads, it swaps in the interactive version.
   With JS off, or if the fetch fails, the reader keeps the PNG.
   ========================================================================== */

(function () {
  'use strict';

  var DATA_URL = document.currentScript
    ? document.currentScript.getAttribute('data-src')
    : null;

  /* ---- palette ---------------------------------------------------------- */

  var C = {
    real: 'var(--accent)',
    deg:  'var(--accent2)',
    er:   'var(--chart-gold)',
    cfg:  'var(--chart-violet)',
    ink:  'var(--text)',
    muted:'var(--muted)',
    line: 'var(--line)',
    panel:'var(--bg-panel)'
  };

  /* ---- tiny SVG helpers ------------------------------------------------- */

  var NS = 'http://www.w3.org/2000/svg';

  function el(name, attrs, parent) {
    var node = document.createElementNS(NS, name);
    for (var k in attrs) {
      if (attrs[k] !== null && attrs[k] !== undefined) {
        node.setAttribute(k, attrs[k]);
      }
    }
    if (parent) parent.appendChild(node);
    return node;
  }

  function div(cls, parent, text) {
    var node = document.createElement('div');
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    if (parent) parent.appendChild(node);
    return node;
  }

  /* Numbers in a tooltip should read like the post's prose, not like a float. */
  function fmt(v, hint) {
    if (v === null || v === undefined) return '—';
    if (hint === 'int') return Math.round(v).toLocaleString('en-GB');
    var a = Math.abs(v);
    if (a >= 1000) return v.toLocaleString('en-GB', { maximumFractionDigits: 0 });
    if (a >= 100) return v.toFixed(1);
    if (a >= 10) return v.toFixed(2);
    return v.toFixed(3);
  }

  /* Axis labels should read 0.05, 0.10, 0.15 - not 0.093, 0.174, 0.256. */
  function niceTicks(x0, x1, target) {
    var span = x1 - x0;
    if (!(span > 0)) return [x0];
    var raw = span / (target || 5);
    var mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var step = [1, 2, 2.5, 5, 10].reduce(function (best, mult) {
      var s = mult * mag;
      return Math.abs(s - raw) < Math.abs(best - raw) ? s : best;
    }, mag);
    var out = [];
    for (var v = Math.ceil(x0 / step) * step; v <= x1 + step * 1e-6; v += step) {
      out.push(Math.abs(v) < step * 1e-6 ? 0 : v);
    }
    return out.length >= 2 ? out : [x0, x1];
  }

  function tickLabel(v, step) {
    var dec = Math.max(0, -Math.floor(Math.log10(step)) + (step < 1 ? 0 : 0));
    if (Math.abs(v) >= 1000) return v.toLocaleString('en-GB', { maximumFractionDigits: 0 });
    return dec > 0 ? v.toFixed(Math.min(4, dec)) : String(Math.round(v));
  }

  /* The analysis speaks in null-model terms; the post's table speaks plainly.
     The tooltip has to agree with the table the reader just looked at, including
     the two rows the post hedges by hand. */
  var VERDICT = {
    'survives': 'Real',
    'explained by degrees': 'Just popularity',
    'fixed by the null': "Can't be tested"
  };
  var VERDICT_BY_LABEL = {
    'Mean shortest path': 'Real, but tiny',
    'Components': 'Too close to call'
  };

  function verdictOf(row) {
    return VERDICT_BY_LABEL[row.label] || VERDICT[row.verdict] || row.verdict;
  }

  function hint(label) {
    return /Triangles|size|Separate|Densest|Widest|Characters/i.test(label) ? 'int' : null;
  }

  /* ---- tooltip ---------------------------------------------------------- */

  var tip = null;

  function showTip(host, html, x, y) {
    if (!tip) {
      tip = div('chart-tip');
      document.body.appendChild(tip);
    }
    tip.innerHTML = html;
    tip.style.display = 'block';
    var r = tip.getBoundingClientRect();
    var left = x - r.width / 2;
    left = Math.max(8, Math.min(window.innerWidth - r.width - 8, left));
    tip.style.left = Math.round(left) + 'px';
    tip.style.top = Math.round(y - r.height - 12) + 'px';
  }

  function hideTip() {
    if (tip) tip.style.display = 'none';
  }

  /* Hover on a pointer device, tap on a touch one - a touch "hover" would
     otherwise leave the tooltip stuck on screen. */
  function hoverable(node, host, htmlFn) {
    function move(ev) {
      var t = ev.touches ? ev.touches[0] : ev;
      showTip(host, htmlFn(), t.clientX, t.clientY);
    }
    node.addEventListener('mouseenter', move);
    node.addEventListener('mousemove', move);
    node.addEventListener('mouseleave', hideTip);
    node.addEventListener('touchstart', function (ev) {
      move(ev);
      ev.stopPropagation();
    }, { passive: true });
  }

  document.addEventListener('touchstart', hideTip, { passive: true });
  window.addEventListener('scroll', hideTip, { passive: true });

  /* ---- histogram chart -------------------------------------------------- */
  /* Overlaid null distributions plus the measured value. The legend toggles a
     series; the measured line stays put so the comparison never disappears. */

  function histChart(host, spec, opts) {
    opts = opts || {};
    var off = {};
    var body = div('chart__plot', host);
    var legend = div('chart__legend', host);

    spec.series.forEach(function (s) {
      var b = document.createElement('button');
      b.className = 'chart__key';
      b.type = 'button';
      b.innerHTML = '<span class="chart__swatch" style="background:' + C[s.colour] + '"></span>' +
                    s.label + ' <span class="chart__keynum">' + fmt(s.mean, opts.hint) + '</span>';
      b.setAttribute('aria-pressed', 'true');
      b.addEventListener('click', function () {
        off[s.key] = !off[s.key];
        b.classList.toggle('is-off', !!off[s.key]);
        b.setAttribute('aria-pressed', off[s.key] ? 'false' : 'true');
        draw();
      });
      legend.appendChild(b);
    });

    var mk = div('chart__key chart__key--static', legend);
    mk.innerHTML = '<span class="chart__swatch chart__swatch--line" style="background:' +
                   C.real + '"></span>Our universe <span class="chart__keynum">' +
                   fmt(spec.real, opts.hint) + '</span>';

    function draw() {
      body.innerHTML = '';
      var W = Math.max(280, body.clientWidth || host.clientWidth || 640);
      var H = opts.height || 300;
      var m = { t: 14, r: 14, b: 38, l: 46 };
      var iw = W - m.l - m.r, ih = H - m.t - m.b;

      var live = spec.series.filter(function (s) { return !off[s.key]; });
      var bars = live.filter(function (s) { return s.edges; });
      var pins = live.filter(function (s) { return s.pin !== undefined; });

      // x window: every visible series, plus the measured value
      var xs = [spec.real];
      live.forEach(function (s) {
        if (s.edges) { xs.push(s.edges[0], s.edges[s.edges.length - 1]); }
        else { xs.push(s.pin); }
      });
      var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
      if (x1 === x0) { x0 -= 1; x1 += 1; }
      var ymax = 1;
      bars.forEach(function (s) {
        s.counts.forEach(function (c) { if (c > ymax) ymax = c; });
      });

      var svg = el('svg', {
        width: W, height: H, viewBox: '0 0 ' + W + ' ' + H,
        role: 'img', 'aria-label': opts.alt || ''
      }, body);

      var X = function (v) { return m.l + (v - x0) / (x1 - x0) * iw; };
      var Y = function (v) { return m.t + ih - v / ymax * ih; };

      // y grid, on round counts
      niceTicks(0, ymax, 4).forEach(function (yv) {
        if (yv > ymax) return;
        el('line', { x1: m.l, y1: Y(yv), x2: m.l + iw, y2: Y(yv),
                     stroke: C.line, 'stroke-width': 1, opacity: yv ? 0.5 : 0.9 }, svg);
        el('text', { x: m.l - 8, y: Y(yv) + 4, 'text-anchor': 'end',
                     class: 'chart__tick' }, svg)
          .textContent = Math.round(yv).toLocaleString('en-GB');
      });

      // x ticks, on round values
      var xt = niceTicks(x0, x1, W < 460 ? 4 : 6);
      var xstep = xt.length > 1 ? xt[1] - xt[0] : (x1 - x0);
      xt.forEach(function (xv) {
        el('line', { x1: X(xv), y1: m.t + ih, x2: X(xv), y2: m.t + ih + 4,
                     stroke: C.line, 'stroke-width': 1 }, svg);
        el('text', { x: X(xv), y: m.t + ih + 20, 'text-anchor': 'middle',
                     class: 'chart__tick' }, svg).textContent = tickLabel(xv, xstep);
      });

      // bars, drawn back to front so the narrow piles stay visible
      bars.forEach(function (s) {
        var g = el('g', { fill: C[s.colour], opacity: 0.78 }, svg);
        for (var b = 0; b < s.counts.length; b++) {
          if (!s.counts[b]) continue;
          var bx = X(s.edges[b]), bw = Math.max(1, X(s.edges[b + 1]) - bx);
          var by = Y(s.counts[b]);
          var rect = el('rect', { x: bx, y: by, width: bw,
                                  height: m.t + ih - by, rx: 1 }, g);
          (function (s, b) {
            hoverable(rect, host, function () {
              return '<strong>' + s.label + '</strong><br>' +
                     fmt(s.edges[b], opts.hint) + ' to ' + fmt(s.edges[b + 1], opts.hint) +
                     '<br>' + s.counts[b] + ' of ' + spec.nrep.toLocaleString('en-GB') + ' universes';
            });
          })(s, b);
        }
      });

      // a null that pins the value: one dashed line, not a pile
      pins.forEach(function (s) {
        var px = X(s.pin);
        el('line', { x1: px, y1: m.t, x2: px, y2: m.t + ih, stroke: C[s.colour],
                     'stroke-width': 2.4, 'stroke-dasharray': '5 3', opacity: 0.95 }, svg);
        var hitp = el('rect', { x: px - 7, y: m.t, width: 14, height: ih,
                                fill: 'transparent' }, svg);
        hoverable(hitp, host, function () {
          return '<strong>' + s.label + '</strong><br>identical in all ' +
                 spec.nrep.toLocaleString('en-GB') + ' universes<br>' + fmt(s.pin, opts.hint);
        });
      });

      // the measured value
      var rx = X(spec.real);
      el('line', { x1: rx, y1: m.t - 4, x2: rx, y2: m.t + ih, stroke: C.real,
                   'stroke-width': 2.4 }, svg);
      var hit = el('rect', { x: rx - 8, y: m.t - 4, width: 16, height: ih + 4,
                             fill: 'transparent' }, svg);
      hoverable(hit, host, function () {
        return '<strong>Our universe</strong><br>' + fmt(spec.real, opts.hint);
      });

      el('text', { x: m.l + iw / 2, y: H - 4, 'text-anchor': 'middle',
                   class: 'chart__axis' }, svg).textContent = opts.xlabel || '';
    }

    return draw;
  }

  /* ---- the battery ------------------------------------------------------ */
  /* One row per quantity, bar length = how far our value sits from the null.
     Clipped at ±30 so a z of −181 does not flatten the rest. */

  function battery(host, rows, nrep) {
    var which = 'deg';
    var controls = div('chart__controls', host);
    var body = div('chart__plot', host);

    div('chart__label', controls, 'Compare against:');
    [['deg', 'Fame-preserving universes'], ['er', 'Blind universes']].forEach(function (opt) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'chart__toggle' + (opt[0] === which ? ' is-on' : '');
      b.textContent = opt[1];
      b.addEventListener('click', function () {
        which = opt[0];
        Array.prototype.forEach.call(controls.querySelectorAll('.chart__toggle'),
          function (o) { o.classList.remove('is-on'); });
        b.classList.add('is-on');
        draw();
      });
      controls.appendChild(b);
    });

    function draw() {
      body.innerHTML = '';
      var W = Math.max(300, body.clientWidth || host.clientWidth || 700);
      var narrow = W < 560;
      var labelW = narrow ? 0 : Math.min(230, W * 0.34);
      var rowH = narrow ? 46 : 30;
      var m = { t: 10, r: 16, b: 34, l: labelW + (narrow ? 8 : 12) };
      var H = m.t + rows.length * rowH + m.b;
      var iw = W - m.l - m.r;
      var LIM = 30;

      var svg = el('svg', { width: W, height: H, viewBox: '0 0 ' + W + ' ' + H,
                            role: 'img', 'aria-label': 'How far each measurement sits from the shuffled universes' }, body);
      var X = function (z) { return m.l + (Math.max(-LIM, Math.min(LIM, z)) + LIM) / (2 * LIM) * iw; };

      // the band of ordinary variation
      el('rect', { x: X(-2), y: m.t, width: X(2) - X(-2), height: rows.length * rowH,
                   fill: C.line, opacity: 0.5 }, svg);
      el('line', { x1: X(0), y1: m.t, x2: X(0), y2: m.t + rows.length * rowH,
                   stroke: C.muted, 'stroke-width': 1 }, svg);

      rows.forEach(function (r, i) {
        var d = r[which];
        var yc = m.t + i * rowH + rowH / 2;
        var barH = narrow ? 12 : 14;

        if (narrow) {
          el('text', { x: m.l, y: yc - 12, class: 'chart__rowlabel' }, svg)
            .textContent = r.plain;
        } else {
          var tx = el('text', { x: labelW, y: yc + 4, 'text-anchor': 'end',
                                class: 'chart__rowlabel' }, svg);
          tx.textContent = r.plain.length > 34 ? r.plain.slice(0, 32) + '…' : r.plain;
          if (tx.textContent !== r.plain) {
            el('title', {}, tx).textContent = r.plain;
          }
        }

        if (d.z === null) {
          el('text', { x: X(0) + 8, y: yc + 4, class: 'chart__pinned' }, svg)
            .textContent = 'the shuffle cannot change this';
        } else {
          var zx = X(d.z), zero = X(0);
          var rect = el('rect', {
            x: Math.min(zero, zx), y: yc - barH / 2,
            width: Math.max(2, Math.abs(zx - zero)), height: barH,
            fill: which === 'deg' ? C.deg : C.er, opacity: 0.9, rx: 2
          }, svg);
          if (Math.abs(d.z) > LIM) {
            el('text', { x: zx + (d.z > 0 ? -6 : 6), y: yc + 4,
                         'text-anchor': d.z > 0 ? 'end' : 'start',
                         class: 'chart__clip' }, svg).textContent = Math.round(d.z);
          }
          hoverable(rect, host, function () {
            return '<strong>' + r.plain + '</strong><br>' +
                   'Our universe: ' + fmt(r.real, hint(r.label)) + '<br>' +
                   'Shuffled: ' + fmt(d.mean, hint(r.label)) + ' ± ' + fmt(d.sd) + '<br>' +
                   'Distance: ' + (d.z > 0 ? '+' : '') + d.z + '<br>' +
                   (d.matched === 0 ? 'No shuffle in ' + nrep.toLocaleString('en-GB') + ' matched it'
                                    : d.matched + ' of ' + nrep.toLocaleString('en-GB') + ' matched or beat it') +
                   '<br><em>' + verdictOf(r) + '</em>';
          });
        }
      });

      var yb = m.t + rows.length * rowH;
      [-30, -20, -10, 0, 10, 20, 30].forEach(function (z) {
        if (narrow && (z === -20 || z === 20)) return;   // no room for all seven
        el('text', { x: X(z), y: yb + 18, 'text-anchor': 'middle', class: 'chart__tick' }, svg)
          .textContent = z;
      });
      el('text', { x: m.l + iw / 2, y: H - 3, 'text-anchor': 'middle', class: 'chart__axis' }, svg)
        .textContent = narrow ? 'Distance from the shuffled universes'
                              : 'Distance from the shuffled universes (shaded strip = ordinary variation)';
    }

    return draw;
  }

  /* ---- the panel picker ------------------------------------------------- */
  /* The static figure could only fit six of the twelve. Here you can pick any. */

  function panels(host, data, order, nrep) {
    var controls = div('chart__chips', host);
    var plot = div('', host);
    var current = order[0];
    var redraw = null;

    order.forEach(function (row) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'chart__chip' + (row.label === current.label ? ' is-on' : '');
      b.textContent = row.plain.length > 26 ? row.plain.slice(0, 24) + '…' : row.plain;
      b.title = row.plain;
      b.addEventListener('click', function () {
        current = row;
        Array.prototype.forEach.call(controls.querySelectorAll('.chart__chip'),
          function (o) { o.classList.remove('is-on'); });
        b.classList.add('is-on');
        build();
      });
      controls.appendChild(b);
    });

    function build() {
      plot.innerHTML = '';
      var spec = data[current.label];
      spec.nrep = nrep;
      var inner = div('chart', plot);
      redraw = histChart(inner, spec, {
        height: 260,
        xlabel: current.plain,
        hint: hint(current.label),
        alt: 'Distribution of ' + current.plain + ' across ' + nrep.toLocaleString('en-GB') + ' shuffled universes'
      });
      redraw();
    }

    build();
    return function () { if (redraw) redraw(); };
  }

  /* ---- the leak scatter ------------------------------------------------- */

  function leakScatter(host, leak) {
    var body = div('chart__plot', host);

    function draw() {
      body.innerHTML = '';
      var W = Math.max(280, body.clientWidth || host.clientWidth || 640);
      var H = 300;
      var m = { t: 16, r: 18, b: 42, l: 52 };
      var iw = W - m.l - m.r, ih = H - m.t - m.b;

      var pts = leak.points;
      var kmax = 0, lmax = 0;
      pts.forEach(function (p) {
        if (p.k > kmax) kmax = p.k;
        if (p.lost > lmax) lmax = p.lost;
      });

      var svg = el('svg', { width: W, height: H, viewBox: '0 0 ' + W + ' ' + H,
                            role: 'img', 'aria-label': 'Links lost by each character in the leaky recipe, against how many links they really have' }, body);

      // log x, because degree spans 1 to 106
      var lx0 = Math.log10(1), lx1 = Math.log10(kmax * 1.15);
      var X = function (k) { return m.l + (Math.log10(Math.max(1, k)) - lx0) / (lx1 - lx0) * iw; };
      var Y = function (v) { return m.t + ih - v / (lmax * 1.1) * ih; };

      [0, 1, 2, 3, 4].forEach(function (i) {
        var yv = lmax * 1.1 * i / 4;
        el('line', { x1: m.l, y1: Y(yv), x2: m.l + iw, y2: Y(yv), stroke: C.line,
                     'stroke-width': 1, opacity: i ? 0.5 : 0.9 }, svg);
        el('text', { x: m.l - 8, y: Y(yv) + 4, 'text-anchor': 'end', class: 'chart__tick' }, svg)
          .textContent = yv.toFixed(0);
      });
      [1, 3, 10, 30, 100].forEach(function (k) {
        if (k > kmax * 1.15) return;
        el('text', { x: X(k), y: m.t + ih + 20, 'text-anchor': 'middle', class: 'chart__tick' }, svg)
          .textContent = k;
      });

      pts.forEach(function (p) {
        var c = el('circle', { cx: X(p.k), cy: Y(p.lost), r: p.k > 40 ? 5 : 3.4,
                               fill: C.cfg, opacity: 0.8 }, svg);
        hoverable(c, host, function () {
          return '<strong>' + p.name + '</strong><br>' +
                 p.k + ' links in our universe<br>loses ' + p.lost.toFixed(1) +
                 ' of them per shuffle';
        });
      });

      // name the worst-hit few, since they are the point of the chart
      pts.slice().sort(function (a, b) { return b.lost - a.lost; }).slice(0, 3)
        .forEach(function (p) {
          el('text', { x: X(p.k) - 9, y: Y(p.lost) + 4, 'text-anchor': 'end',
                       class: 'chart__note' }, svg).textContent = p.name;
        });

      el('text', { x: m.l + iw / 2, y: H - 4, 'text-anchor': 'middle', class: 'chart__axis' }, svg)
        .textContent = 'Links the character really has (log scale)';
      el('text', { x: 14, y: m.t + ih / 2, class: 'chart__axis',
                   transform: 'rotate(-90 14 ' + (m.t + ih / 2) + ')',
                   'text-anchor': 'middle' }, svg).textContent = 'Links lost per shuffle';
    }

    return draw;
  }

  /* ---- boot ------------------------------------------------------------- */

  function mount(data) {
    var redraws = [];

    document.querySelectorAll('[data-chart]').forEach(function (host) {
      var kind = host.getAttribute('data-chart');
      var fig = host.closest('figure');
      var draw = null;

      if (kind === 'clustering') {
        var spec = data.clustering;
        spec.nrep = data.nrep;
        draw = histChart(host, spec, {
          height: 320,
          xlabel: 'Average clustering',
          alt: 'Average clustering across ' + data.nrep.toLocaleString('en-GB') + ' shuffled universes of three kinds'
        });
      } else if (kind === 'battery') {
        draw = battery(host, data.battery, data.nrep);
      } else if (kind === 'panels') {
        draw = panels(host, data.panels, data.battery, data.nrep);
      } else if (kind === 'leak') {
        var top = div('chart chart--stacked', host);
        var bottom = div('chart chart--stacked', host);
        var kept = data.leak.kept;
        var drawKept = histChart(top, {
          real: data.leak.real_edges,
          nrep: data.nrep,
          series: [{ key: 'kept', label: 'Links that came back', colour: 'cfg',
                     mean: kept.mean, edges: kept.edges, counts: kept.counts }]
        }, {
          height: 240, hint: 'int',
          xlabel: 'Links surviving the leaky recipe (out of ' + data.leak.real_edges + ')',
          alt: 'How many of the 1,421 links survive the leaky recipe'
        });
        var drawPts = leakScatter(bottom, data.leak);
        draw = function () { drawKept(); drawPts(); };
      }

      if (!draw) return;
      draw();
      redraws.push(draw);
      host.classList.add('is-live');
      // the PNG has done its job; keep it for print and for no-JS readers
      if (fig) {
        var img = fig.querySelector('img');
        if (img) img.hidden = true;
        fig.classList.add('figure--interactive');
      }
    });

    if (!redraws.length) return;
    var t = null;
    window.addEventListener('resize', function () {
      clearTimeout(t);
      t = setTimeout(function () { redraws.forEach(function (f) { f(); }); }, 160);
    });
  }

  function boot() {
    if (!DATA_URL || !window.fetch || !document.querySelector('[data-chart]')) return;
    fetch(DATA_URL)
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(mount)
      .catch(function () { /* the PNGs are still there; say nothing */ });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
