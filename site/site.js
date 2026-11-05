(function () {
  'use strict';
  var D = window.CINETV || {};
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var canHover = window.matchMedia && matchMedia('(hover:hover)').matches;

  /* --- плавное появление блоков (только прозрачность, раскладка не меняется) --- */
  var rev = $$('.reveal');
  rev.forEach(function (el, i) { el.style.setProperty('--d', (i % 4) * 0.07 + 's'); });
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });
    rev.forEach(function (el) { io.observe(el); });
  } else rev.forEach(function (el) { el.classList.add('in'); });

  /* --- счётчики --- */
  function count(el) {
    var to = +el.dataset.count, plus = el.dataset.plus ? '+' : '';
    if (reduce || to === 0) { el.textContent = to + plus; return; }
    var t0 = performance.now(), dur = 1300;
    (function step(t) {
      var p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(to * e) + (p === 1 ? plus : '');
      if (p < 1) requestAnimationFrame(step);
    })(t0);
  }
  if ('IntersectionObserver' in window) {
    var co = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { count(e.target); co.unobserve(e.target); } });
    }, { threshold: 0.6 });
    $$('[data-count]').forEach(function (el) { co.observe(el); });
  }

  /* --- шапка и полоса прокрутки --- */
  var top = $('#top'), prog = $('#progress'), ticking = false;
  function onScroll() {
    var y = window.scrollY || 0, h = document.documentElement.scrollHeight - innerHeight;
    if (top) top.classList.toggle('scrolled', y > 8);
    document.documentElement.style.setProperty('--sy', y);
    if (prog) prog.style.transform = 'scaleX(' + (h > 0 ? Math.min(1, y / h) : 0) + ')';
    ticking = false;
  }
  addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  /* --- эффекты фона: пылинки в луче, свечение за курсором --- */
  var dust = $('#dust'), cursor = $('#cursor');
  if (dust && !reduce && dust.getContext) {
    var ctx = dust.getContext('2d'), DPR = Math.min(window.devicePixelRatio || 1, 1.5), W = 0, H = 0, P = [], mx = -999, my = -999;
    var resize = function () {
      W = innerWidth; H = innerHeight;
      dust.width = W * DPR; dust.height = H * DPR;
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      var n = W < 700 ? 34 : 78;
      while (P.length < n) P.push(spawn(true));
      P.length = n;
    };
    var spawn = function (anywhere) {
      return { x: Math.random() * W, y: anywhere ? Math.random() * H : H + 10, r: 0.6 + Math.random() * 1.8,
               vx: (Math.random() - 0.5) * 0.18, vy: -(0.06 + Math.random() * 0.22), a: 0.18 + Math.random() * 0.5, t: Math.random() * 6.28 };
    };
    resize();
    addEventListener('resize', resize);
    addEventListener('pointermove', function (e) { mx = e.clientX; my = e.clientY; }, { passive: true });
    (function frame() {
      if (!document.hidden) {
        ctx.clearRect(0, 0, W, H);
        for (var i = 0; i < P.length; i++) {
          var q = P[i];
          q.t += 0.02; q.x += q.vx + Math.sin(q.t) * 0.12; q.y += q.vy;
          var dx = q.x - mx, dy = q.y - my, d2 = dx * dx + dy * dy;
          if (d2 < 14400) { var f = (1 - d2 / 14400) * 1.4; q.x += dx / 60 * f; q.y += dy / 60 * f; }
          if (q.y < -10 || q.x < -10 || q.x > W + 10) { P[i] = spawn(false); continue; }
          // ближе к лучу (верх, центр) светятся ярче
          var beam = Math.max(0, 1 - Math.abs(q.x - W / 2) / (W * (0.12 + q.y / H * 0.5)));
          ctx.globalAlpha = Math.min(1, q.a * (0.55 + beam * 1.1) * (0.7 + 0.3 * Math.sin(q.t * 2)));
          ctx.fillStyle = '#cdbfff';
          ctx.beginPath(); ctx.arc(q.x, q.y, q.r, 0, 6.283); ctx.fill();
        }
        ctx.globalAlpha = 1;
      }
      requestAnimationFrame(frame);
    })();
  }
  if (cursor && canHover && !reduce) {
    var cx = 0, cy = 0, tx = 0, ty = 0, on = false;
    addEventListener('pointermove', function (e) { tx = e.clientX; ty = e.clientY; if (!on) { on = true; cursor.style.opacity = 1; cx = tx; cy = ty; } }, { passive: true });
    document.addEventListener('mouseleave', function () { cursor.style.opacity = 0; on = false; });
    (function follow() {
      cx += (tx - cx) * 0.12; cy += (ty - cy) * 0.12;
      cursor.style.transform = 'translate3d(' + cx + 'px,' + cy + 'px,0)';
      requestAnimationFrame(follow);
    })();
  }

  /* --- телевизор слегка поворачивается за курсором --- */
  var stage = $('.stage'), tv = stage && $('.tv', stage);
  if (stage && tv && canHover && !reduce) {
    stage.addEventListener('pointermove', function (e) {
      var r = stage.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      tv.style.setProperty('--ry', (x * 7).toFixed(2) + 'deg');
      tv.style.setProperty('--rx', (-y * 5).toFixed(2) + 'deg');
    });
    stage.addEventListener('pointerleave', function () { tv.style.setProperty('--ry', '0deg'); tv.style.setProperty('--rx', '0deg'); });
  }

  /* --- подсветка ячеек возможностей за курсором --- */
  if (canHover && !reduce) {
    $$('.fcell').forEach(function (c) {
      c.addEventListener('pointermove', function (e) {
        var r = c.getBoundingClientRect();
        c.style.setProperty('--mx', (e.clientX - r.left) + 'px');
        c.style.setProperty('--my', (e.clientY - r.top) + 'px');
      });
    });
  }

  /* --- смена экранов на телевизоре в hero --- */
  var slides = $$('#slides img');
  if (slides.length > 1 && !reduce) {
    var si = 0;
    setInterval(function () {
      if (document.hidden) return;
      slides[si].classList.remove('on');
      si = (si + 1) % slides.length;
      slides[si].classList.add('on');
    }, 3800);
  }

  /* --- витрина скриншотов --- */
  var sets = D.shots || {}, cur = 'android', idx = 0, timer;
  var shot = $('#shot'), cap = $('#cap'), frame = $('#frame'), thumbs = $$('.thumb');
  function show(i, user) {
    var list = sets[cur]; if (!list) return;
    idx = (i + list.length) % list.length;
    var s = list[idx];
    frame.classList.add('swap');
    setTimeout(function () {
      shot.src = s.src; shot.alt = s.title + ': ' + s.text;
      cap.innerHTML = '';
      var b = document.createElement('b'); b.textContent = s.title;
      cap.appendChild(b); cap.appendChild(document.createTextNode(' — ' + s.text));
      var done = function () { frame.classList.remove('swap'); };
      shot.onload = done; shot.onerror = done; if (shot.complete) done();
    }, reduce ? 0 : 180);
    thumbs.forEach(function (t) {
      var on = t.dataset.set === cur && +t.dataset.i === idx;
      t.classList.toggle('on', on); t.setAttribute('aria-current', on ? 'true' : 'false');
    });
    if (user) restart();
  }
  function setTab(name) {
    cur = name; frame.dataset.kind = name;
    $$('.tab').forEach(function (t) { var on = t.dataset.set === name; t.classList.toggle('on', on); t.setAttribute('aria-selected', on); });
    thumbs.forEach(function (t) { t.hidden = t.dataset.set !== name; });
    show(0, true);
  }
  function restart() {
    clearInterval(timer);
    if (reduce) return;
    timer = setInterval(function () { show(idx + 1); }, 5000);
  }
  if (shot && frame) {
    $$('.tab').forEach(function (t) { t.addEventListener('click', function () { setTab(t.dataset.set); }); });
    thumbs.forEach(function (t) { t.addEventListener('click', function () { cur = t.dataset.set; show(+t.dataset.i, true); }); });
    $('#prev').addEventListener('click', function () { show(idx - 1, true); });
    $('#next').addEventListener('click', function () { show(idx + 1, true); });
    var st = $('#stage'); st.addEventListener('mouseenter', function () { clearInterval(timer); }); st.addEventListener('mouseleave', restart);
    thumbs.forEach(function (t) { t.hidden = t.dataset.set !== 'android'; });
    thumbs[0] && thumbs[0].classList.add('on');
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) {
        if (es[0].isIntersecting) restart(); else clearInterval(timer);
      }, { threshold: 0.3 }).observe(st);
    }
    var sx = 0;
    st.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; }, { passive: true });
    st.addEventListener('touchend', function (e) {
      var dx = e.changedTouches[0].clientX - sx;
      if (Math.abs(dx) > 40) show(idx + (dx < 0 ? 1 : -1), true);
    });
  }

  /* --- система посетителя: подсвечиваем нужную платформу (текст и размеры не меняются) --- */
  var ua = navigator.userAgent || '', os = null;
  if (/Android/i.test(ua)) os = 'android';
  else if (/Windows/i.test(ua)) os = 'windows';
  else if (/Macintosh|Mac OS X/i.test(ua) && !/iPhone|iPad/i.test(ua)) os = 'macos';
  if (os) {
    $$('[data-plat="' + os + '"],[data-os="' + os + '"]').forEach(function (el) { el.classList.add('rec'); });
  }

  /* --- свежие ссылки на скачивание из релизов GitHub --- */
  var API = 'https://api.github.com/repos/' + (D.repo || 'kholodniakruslan/CineTV-releases') + '/releases?per_page=40';
  var RULES = {
    android: { prefix: 'android-v', files: { arm64: /arm64-v8a.*\.apk$/i, v7a: /armeabi-v7a.*\.apk$/i } },
    windows: { prefix: 'windows-v', files: { setup: /setup.*\.exe$/i, zip: /portable.*\.zip$/i } },
    macos: { prefix: 'macos-v', files: { arm: /arm64.*\.dmg$/i, x64: /x64.*\.dmg$/i } }
  };
  function apply(rels) {
    Object.keys(RULES).forEach(function (p) {
      var rule = RULES[p];
      var rel = rels.filter(function (r) { return !r.draft && !r.prerelease && r.tag_name.indexOf(rule.prefix) === 0; })[0];
      if (!rel) return;
      var ver = rel.tag_name.slice(rule.prefix.length);
      $$('[data-ver="' + p + '"]').forEach(function (v) { v.textContent = ver; });
      Object.keys(rule.files).forEach(function (k) {
        var a = (rel.assets || []).filter(function (x) { return rule.files[k].test(x.name); })[0];
        var link = $('[data-dl="' + p + '-' + k + '"]');
        if (a && link) link.href = a.browser_download_url;
      });
    });
  }
  var KEY = 'cinetv-releases-v1', cached = null;
  try { cached = JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch (e) {}
  if (cached && Date.now() - cached.t < 3600e3) apply(cached.d);
  else if (window.fetch) {
    fetch(API, { headers: { Accept: 'application/vnd.github+json' } })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (d) {
        apply(d);
        try { sessionStorage.setItem(KEY, JSON.stringify({ t: Date.now(), d: d.map(function (r) { return { tag_name: r.tag_name, draft: r.draft, prerelease: r.prerelease, assets: (r.assets || []).map(function (a) { return { name: a.name, browser_download_url: a.browser_download_url }; }) }; }) })); } catch (e) {}
      })
      .catch(function () { /* остаются ссылки, зашитые при сборке */ });
  }
})();
