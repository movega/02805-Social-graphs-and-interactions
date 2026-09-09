/* ==========================================================================
   02805 Social Graphs — group site
   1. SITE: the one place to edit team name, members and repo URL.
   2. Week-state: lights up the spider legs / week grid for the current week.
   3. The weaver: the spider easter egg that draws those legs, one per week.
   Everything degrades gracefully: with JS off the page still shows the
   placeholder text written in the HTML.
   ========================================================================== */

var SITE = {
  // ---- Fill these in and every page updates ------------------------------
  teamName: 'Varmel',
  repoUrl: 'https://github.com/balpaula/02805-Social-graphs-and-interactions',
  repoLabel: 'balpaula/02805-Social-graphs-and-interactions',
  members: [
    // Roles below are a first guess — swap them around as you like.
    { name: 'Alvaro Vega',    role: 'Network analysis', link: '' },
    { name: 'Oier Garcia',    role: 'Visualization',    link: '' },
    { name: 'Paula Balcells', role: 'Writing',          link: '' }
  ],

  // ---- Course calendar ---------------------------------------------------
  // Week 1 = Wednesday 2 September 2026. Weeks 1-8 are the taught weeks,
  // 9-13 the project period.
  courseStart: new Date(2026, 8, 2),
  weekOverride: null                  // set to 1..13 to preview another week
};

(function () {
  'use strict';

  /* ---- 1. Config injection -------------------------------------------- */

  function fillConfig() {
    var i, el, els;

    if (SITE.teamName) {
      els = document.querySelectorAll('[data-site="team-name"]');
      for (i = 0; i < els.length; i++) els[i].textContent = SITE.teamName;
    }

    els = document.querySelectorAll('[data-site="repo-link"]');
    for (i = 0; i < els.length; i++) {
      el = els[i];
      if (SITE.repoUrl) el.setAttribute('href', SITE.repoUrl);
      var label = el.querySelector('[data-site="repo-label"]');
      if (label && SITE.repoLabel) label.textContent = SITE.repoLabel;
    }

    for (i = 0; i < SITE.members.length; i++) {
      var m = SITE.members[i];
      var nameEl = document.querySelector('[data-member="' + (i + 1) + '-name"]');
      var roleEl = document.querySelector('[data-member="' + (i + 1) + '-role"]');
      var linkEl = document.querySelector('[data-member="' + (i + 1) + '-link"]');
      if (nameEl && m.name) nameEl.textContent = m.name;
      if (roleEl && m.role) roleEl.textContent = m.role;
      if (linkEl) {
        if (m.link) {
          linkEl.setAttribute('href', m.link);
          linkEl.textContent = m.link.replace(/^https?:\/\//, '');
        } else {
          linkEl.parentNode.style.display = 'none';
        }
      }
    }
  }

  /* ---- 2. Week state --------------------------------------------------- */

  function legStyle(status) {
    if (status === 'past') {
      return { lineColor: 'var(--text)', lineOpacity: '0.42', lineWidth: '2.4', dash: '0', footFill: 'var(--line-node)', footStroke: 'none', footStrokeWidth: '0', footR: '6', glowOpacity: '0' };
    }
    if (status === 'current') {
      return { lineColor: 'var(--accent)', lineOpacity: '1', lineWidth: '3', dash: '0', footFill: 'var(--accent)', footStroke: 'none', footStrokeWidth: '0', footR: '9', glowOpacity: '0.85' };
    }
    return { lineColor: 'var(--line)', lineOpacity: '0.4', lineWidth: '1.4', dash: '3 5', footFill: 'var(--bg-panel)', footStroke: 'var(--line)', footStrokeWidth: '1.5', footR: '5', glowOpacity: '0' };
  }

  function footerStyle(status) {
    if (status === 'past') return { color: 'var(--text)', opacity: '0.88', tag: 'done', tagColor: 'var(--muted)' };
    if (status === 'current') return { color: 'var(--accent)', opacity: '1', tag: 'live', tagColor: 'var(--accent)' };
    return { color: 'var(--muted)', opacity: '0.62', tag: 'coming', tagColor: 'var(--line)' };
  }

  function computeCurrentWeek() {
    if (SITE.weekOverride !== null && SITE.weekOverride > 0) return Math.min(SITE.weekOverride, 13);
    var diffDays = Math.floor((new Date().getTime() - SITE.courseStart.getTime()) / 86400000);
    var week = diffDays < 0 ? 0 : Math.floor(diffDays / 7) + 1;
    return Math.min(week, 13);
  }

  function setLine(id, s) {
    var el = document.getElementById(id);
    if (!el) return;
    el.setAttribute('stroke', s.lineColor);
    el.setAttribute('stroke-width', s.lineWidth);
    el.setAttribute('stroke-opacity', s.lineOpacity);
    el.setAttribute('stroke-dasharray', s.dash);
  }

  function applyWeekState(currentWeek) {
    for (var w = 1; w <= 8; w++) {
      var status = w < currentWeek ? 'past' : (w === currentWeek ? 'current' : 'upcoming');
      var leg = legStyle(status);
      setLine('leg' + w + '-line1', leg);
      setLine('leg' + w + '-line2', leg);

      var glow = document.getElementById('leg' + w + '-glow');
      if (glow) glow.setAttribute('opacity', leg.glowOpacity);

      var foot = document.getElementById('leg' + w + '-foot');
      if (foot) {
        foot.setAttribute('r', leg.footR);
        foot.setAttribute('fill', leg.footFill);
        foot.setAttribute('stroke', leg.footStroke);
        foot.setAttribute('stroke-width', leg.footStrokeWidth);
      }

      var fs = footerStyle(status);
      var tagEl = document.getElementById('footer-w' + w + '-tag');
      if (tagEl) {
        tagEl.textContent = fs.tag;
        tagEl.style.borderColor = fs.tagColor;
        tagEl.style.color = fs.tagColor;
      }
      var titleEl = document.getElementById('footer-w' + w + '-title');
      if (titleEl) {
        titleEl.style.color = fs.color;
        titleEl.style.opacity = fs.opacity;
      }
    }

    var projectStatus = currentWeek > 13 ? 'past' : (currentWeek >= 9 ? 'current' : 'upcoming');
    var projectFooter;
    if (projectStatus === 'current') {
      projectFooter = { color: 'var(--accent2)', opacity: '1', tag: 'in progress', tagColor: 'var(--accent2)' };
    } else if (projectStatus === 'past') {
      projectFooter = { color: 'var(--text)', opacity: '0.88', tag: 'done', tagColor: 'var(--muted)' };
    } else {
      projectFooter = { color: 'var(--muted)', opacity: '0.62', tag: 'coming', tagColor: 'var(--line)' };
    }
    var pTag = document.getElementById('project-tag');
    if (pTag) {
      pTag.textContent = projectFooter.tag;
      pTag.style.borderColor = projectFooter.tagColor;
      pTag.style.color = projectFooter.tagColor;
    }
    var pTitle = document.getElementById('project-title');
    if (pTitle) {
      pTitle.style.color = projectFooter.color;
      pTitle.style.opacity = projectFooter.opacity;
    }

    var bodyGlow = document.getElementById('body-glow');
    if (bodyGlow) bodyGlow.setAttribute('opacity', currentWeek > 8 ? '0.85' : '0');
    var bodyFill = document.getElementById('body-fill');
    if (bodyFill) bodyFill.setAttribute('fill', currentWeek >= 1 ? 'var(--text)' : 'var(--line)');

    var labelEl = document.getElementById('week-label');
    if (labelEl) {
      labelEl.textContent = currentWeek <= 0 ? 'Starting soon'
        : (currentWeek <= 8 ? ('Week ' + currentWeek + ' of 8') : 'Project period');
    }

    var caption = document.getElementById('reveal-caption');
    if (caption) caption.style.display = currentWeek >= 8 ? '' : 'none';
  }

  /* ---- 3. The weaver --------------------------------------------------- */
  /* An easter egg: a spider drops in on a thread, walks out one leg per
     elapsed week to draw it, then hangs under the hub. Click a woven week and
     it comes over to that foot. Decorative only — if anything here throws,
     the static SVG in the HTML is still a correct picture of the term.
     Leg geometry is read back out of the HTML so the animation and the drawn
     legs can never drift apart. */

  function readLegs() {
    var legs = {};
    for (var w = 1; w <= 8; w++) {
      var l1 = document.getElementById('leg' + w + '-line1');
      var l2 = document.getElementById('leg' + w + '-line2');
      if (!l1 || !l2) continue;
      legs[w] = {
        knee: [parseFloat(l1.getAttribute('x2')), parseFloat(l1.getAttribute('y2'))],
        foot: [parseFloat(l2.getAttribute('x2')), parseFloat(l2.getAttribute('y2'))]
      };
    }
    return legs;
  }

  function initSpiderWeave(currentWeek) {
    var spider = document.getElementById('spider');
    if (!spider) return;

    var LEGS = readLegs();
    var thread = document.getElementById('spider-thread');
    var pulse = document.getElementById('reveal-pulse');
    var caption = document.getElementById('reveal-caption');
    var hint = document.getElementById('weeks-hint');
    var scene = document.getElementById('weeks-svg');

    var reduce = false;
    try {
      reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {}

    var woven = Math.max(0, Math.min(8, currentWeek));
    var isComplete = currentWeek >= 8;

    var ANCHOR = { x: 0, y: 14 };   // where the hanging thread is tied
    var HANG = isComplete ? 128 : 52;
    var TOP = -178;                 // off the top of the frame

    function d(ax, ay, bx, by) {
      return Math.sqrt((bx - ax) * (bx - ax) + (by - ay) * (by - ay));
    }
    function easeInOut(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }
    function easeOutBack(t) {
      var c = 1.70158 + 1;
      return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2);
    }
    function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

    var legs = {};
    for (var w = 1; w <= 8; w++) {
      var g = LEGS[w];
      if (!g) continue;
      var l1 = d(0, 0, g.knee[0], g.knee[1]);
      var l2 = d(g.knee[0], g.knee[1], g.foot[0], g.foot[1]);
      legs[w] = {
        knee: g.knee,
        foot: g.foot,
        l1: l1,
        l2: l2,
        total: l1 + l2,
        line1: document.getElementById('leg' + w + '-line1'),
        line2: document.getElementById('leg' + w + '-line2'),
        footEl: document.getElementById('leg' + w + '-foot')
      };
    }

    /* Draw a leg to `p` (0..1) by walking its dash offset. */
    function setLegProgress(w, p) {
      var L = legs[w];
      if (!L) return;
      var run = p * L.total;
      if (L.line1) {
        var p1 = Math.max(0, Math.min(1, L.l1 ? run / L.l1 : 1));
        L.line1.setAttribute('stroke-dasharray', L.l1.toFixed(2));
        L.line1.setAttribute('stroke-dashoffset', (L.l1 * (1 - p1)).toFixed(2));
      }
      if (L.line2) {
        var p2 = Math.max(0, Math.min(1, L.l2 ? (run - L.l1) / L.l2 : 1));
        L.line2.setAttribute('stroke-dasharray', L.l2.toFixed(2));
        L.line2.setAttribute('stroke-dashoffset', (L.l2 * (1 - p2)).toFixed(2));
      }
    }
    function clearLegDash(w) {
      var L = legs[w];
      if (!L) return;
      [L.line1, L.line2].forEach(function (el) {
        if (!el) return;
        el.removeAttribute('stroke-dasharray');
        el.removeAttribute('stroke-dashoffset');
      });
    }
    function pointOnLeg(w, p) {
      var L = legs[w];
      var run = p * L.total;
      if (run <= L.l1) {
        var t = L.l1 ? run / L.l1 : 0;
        return { x: L.knee[0] * t, y: L.knee[1] * t };
      }
      var t2 = L.l2 ? (run - L.l1) / L.l2 : 0;
      return {
        x: L.knee[0] + (L.foot[0] - L.knee[0]) * t2,
        y: L.knee[1] + (L.foot[1] - L.knee[1]) * t2
      };
    }

    var pos = { x: 0, y: TOP };
    var angle = 0;

    function paint() {
      spider.setAttribute(
        'transform',
        'translate(' + pos.x.toFixed(2) + ',' + pos.y.toFixed(2) + ') rotate(' + angle.toFixed(2) + ')'
      );
    }
    function setThread(ax, ay, on) {
      if (!thread) return;
      if (!on) { thread.setAttribute('opacity', '0'); return; }
      thread.setAttribute('opacity', '0.5');
      thread.setAttribute('x1', ax.toFixed(2));
      thread.setAttribute('y1', ay.toFixed(2));
      thread.setAttribute('x2', pos.x.toFixed(2));
      thread.setAttribute('y2', pos.y.toFixed(2));
    }
    function faceTowards(dx, dy) {
      if (dx === 0 && dy === 0) return;
      angle = (Math.atan2(dy, dx) * 180) / Math.PI - 90;
    }
    function walking(on) {
      if (on) spider.classList.add('walking');
      else spider.classList.remove('walking');
    }

    /* ---- phases -------------------------------------------------------- */

    function pDrop() {
      return {
        dur: 900,
        start: function () { pos.x = 0; pos.y = TOP; angle = 0; walking(false); },
        run: function (t) {
          var e = easeOutBack(t);
          pos.x = 0;
          pos.y = TOP + (-46 - TOP) * e;
          angle = Math.sin(t * Math.PI * 2) * 5;
          setThread(0, TOP, true);
        }
      };
    }

    function pArcTo(target, dur, bulge) {
      var from = { x: 0, y: 0 };
      return {
        dur: dur,
        start: function () { from.x = pos.x; from.y = pos.y; walking(true); },
        run: function (t) {
          var e = easeInOut(t);
          var mx = (from.x + target.x) / 2;
          var my = (from.y + target.y) / 2;
          var nx = -(target.y - from.y);
          var ny = target.x - from.x;
          var len = Math.sqrt(nx * nx + ny * ny) || 1;
          var cx = mx + (nx / len) * (bulge || 0);
          var cy = my + (ny / len) * (bulge || 0);
          var u = 1 - e;
          var px = u * u * from.x + 2 * u * e * cx + e * e * target.x;
          var py = u * u * from.y + 2 * u * e * cy + e * e * target.y;
          faceTowards(px - pos.x, py - pos.y);
          pos.x = px;
          pos.y = py;
          setThread(from.x, from.y, true);
        },
        end: function () { walking(false); }
      };
    }

    function pWeave(w) {
      return {
        dur: 520,
        start: function () { walking(true); },
        run: function (t) {
          var e = easeInOut(t);
          var p = pointOnLeg(w, e);
          faceTowards(p.x - pos.x, p.y - pos.y);
          pos.x = p.x;
          pos.y = p.y;
          setLegProgress(w, e);
          setThread(0, 0, false);
        },
        end: function () { setLegProgress(w, 1); clearLegDash(w); walking(false); }
      };
    }

    function pTieOff() {
      return { dur: 170, run: function (t) { angle += Math.sin(t * Math.PI * 6) * 2.2; } };
    }

    /* Week 8: the web is finished, so drop further and pulse once. */
    function pReveal() {
      return {
        dur: 1150,
        start: function () {
          walking(false);
          if (caption) { caption.style.opacity = '1'; caption.style.transform = 'translateY(0)'; }
        },
        run: function (t) {
          var e = easeOutCubic(t);
          pos.x = 0;
          pos.y = -46 + (HANG - -46) * e;
          angle = Math.sin(t * Math.PI * 3) * 8;
          setThread(ANCHOR.x, ANCHOR.y, true);
          if (pulse) {
            pulse.setAttribute('r', (18 + 150 * e).toFixed(1));
            pulse.setAttribute('opacity', (0.55 * (1 - e)).toFixed(3));
          }
        },
        end: function () { if (pulse) pulse.setAttribute('opacity', '0'); }
      };
    }

    function idleAt(rope) {
      var t0 = 0;
      var nextHop = 0;
      return {
        idle: true,
        start: function (now) {
          t0 = now;
          nextHop = now + 6500 + Math.random() * 4000;
          walking(false);
        },
        run: function (now) {
          var phase = ((now - t0) / 2800) * Math.PI * 2;
          var swing = (Math.sin(phase) * 9 * Math.PI) / 180;
          pos.x = ANCHOR.x + Math.sin(swing) * rope;
          pos.y = ANCHOR.y + Math.cos(swing) * rope;
          angle = (swing * 180) / Math.PI;
          setThread(ANCHOR.x, ANCHOR.y, true);
          if (now > nextHop) {
            nextHop = now + 6500 + Math.random() * 4000;
            var targets = [];
            for (var k = 1; k <= woven; k++) {
              if (legs[k]) targets.push(legs[k].foot);
            }
            if (targets.length) hopTo(targets[Math.floor(Math.random() * targets.length)]);
          }
        }
      };
    }

    /* ---- sequence ------------------------------------------------------ */

    function buildSequence() {
      var seq = [pDrop()];
      for (var k = 1; k <= woven; k++) {
        if (!legs[k]) continue;
        seq.push(pArcTo({ x: 0, y: 0 }, 240, 0));
        seq.push(pWeave(k));
        seq.push(pTieOff());
      }
      if (isComplete) {
        seq.push(pArcTo({ x: 0, y: -46 }, 320, 0));
        seq.push(pReveal());
      } else {
        seq.push(pArcTo({ x: ANCHOR.x, y: ANCHOR.y + HANG }, 480, 26));
      }
      return seq;
    }

    function finalState() {
      for (var k = 1; k <= woven; k++) {
        if (!legs[k]) continue;
        setLegProgress(k, 1);
        clearLegDash(k);
      }
      if (caption) { caption.style.opacity = '1'; caption.style.transform = 'translateY(0)'; }
      pos.x = ANCHOR.x;
      pos.y = ANCHOR.y + HANG;
      angle = 0;
      paint();
      setThread(ANCHOR.x, ANCHOR.y, true);
    }

    // Hide the legs that are about to be woven, so they get drawn on screen.
    for (var j = 1; j <= woven; j++) {
      if (legs[j]) setLegProgress(j, 0);
    }
    if (caption) { caption.style.opacity = '0'; caption.style.transform = 'translateY(6px)'; }
    if (pulse) pulse.setAttribute('opacity', '0');
    paint();
    setThread(0, TOP, true);

    if (reduce) {
      finalState();
      return;
    }

    var seq = buildSequence();
    var idle = idleAt(HANG);
    var index = -1;
    var phaseStart = 0;
    var current = null;
    var raf = null;
    var running = false;
    var started = false;

    function step(now) {
      if (!running) return;
      if (current === null) {
        index++;
        current = index < seq.length ? seq[index] : idle;
        phaseStart = now;
        if (current.start) current.start(now);
      }
      if (current.idle) {
        current.run(now);
        paint();
        raf = window.requestAnimationFrame(step);
        return;
      }
      var t = Math.min(1, (now - phaseStart) / current.dur);
      current.run(t);
      paint();
      if (t >= 1) {
        if (current.end) current.end();
        current = null;
      }
      raf = window.requestAnimationFrame(step);
    }

    function hopTo(foot) {
      seq = [
        pArcTo({ x: foot[0], y: foot[1] }, 430, 34),
        pTieOff(),
        pArcTo({ x: ANCHOR.x, y: ANCHOR.y + HANG }, 520, -30)
      ];
      index = -1;
      current = null;
    }

    function play() {
      if (running) return;
      running = true;
      started = true;
      raf = window.requestAnimationFrame(step);
    }
    function stop() {
      running = false;
      if (raf) window.cancelAnimationFrame(raf);
      raf = null;
    }

    // Click a woven week and the weaver walks over to it.
    var clickable = 0;
    Object.keys(legs).forEach(function (key) {
      var k = parseInt(key, 10);
      var L = legs[k];
      if (!L.footEl || k > woven) return;
      clickable++;
      L.footEl.style.cursor = 'pointer';
      L.footEl.addEventListener('click', function () {
        if (!started) return;
        hopTo(L.foot);
        if (!running) play();
      });
    });
    // Only advertise the trick once there is a woven week to click.
    if (hint) hint.hidden = clickable === 0;

    // Only animate while the figure is actually on screen.
    try {
      var io = new window.IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) play();
          else stop();
        });
      }, { threshold: 0.15 });
      if (scene) io.observe(scene);
      else play();
    } catch (e) {
      play();
    }
  }

  function init() {
    var currentWeek = computeCurrentWeek();
    fillConfig();
    applyWeekState(currentWeek);
    try {
      initSpiderWeave(currentWeek);
    } catch (err) {
      /* the weaver is decorative — never let it break the page */
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
