/* Доска карты пути: панорама, масштаб, переключение сторон.
   Мир — div с transform translate+scale внутри окна. Тянуть можно только
   за фон: на карточке перетаскивание выделяет текст — так к шагу
   оставляют комментарий. Колесо — прокрутка, Ctrl+колесо и щипок — масштаб. */
(function () {
  var wrap = document.getElementById('board');
  if (!wrap) return;
  var view = wrap.querySelector('.bd-view');
  var label = wrap.querySelector('.bd-zoom');
  var KEY = 'fsp-cjm-side';
  var side = 'c';
  try { side = localStorage.getItem(KEY) === 'e' ? 'e' : 'c'; } catch (e) { /* приватное окно */ }
  var st = { c: null, e: null };
  var MIN = 0.12, MAX = 2;

  function world() { return wrap.querySelector('.bd-world[data-side="' + side + '"]'); }
  function apply() {
    var w = world(), s = st[side];
    w.style.transform = 'translate(' + s.x + 'px,' + s.y + 'px) scale(' + s.k + ')';
    label.textContent = Math.round(s.k * 100) + ' %';
  }
  function fit() {
    var w = world(), vw = view.clientWidth, vh = view.clientHeight;
    // Высота мира — по самой высокой колонке: карточки растут по тексту.
    var ww = parseFloat(w.style.width), wh = 0;
    w.querySelectorAll('.bd-col').forEach(function (c) { wh = Math.max(wh, c.offsetHeight); });
    w.style.height = wh + 'px';
    var k = Math.min((vw - 48) / ww, (vh - 48) / wh, 1);
    st[side] = { k: k, x: (vw - ww * k) / 2, y: Math.max(24, (vh - wh * k) / 2) };
    apply();
  }
  function zoomAt(f, cx, cy) {
    var s = st[side], k = Math.max(MIN, Math.min(MAX, s.k * f));
    s.x = cx - (cx - s.x) * (k / s.k); s.y = cy - (cy - s.y) * (k / s.k); s.k = k; apply();
  }
  function show(next) {
    side = next;
    try { localStorage.setItem(KEY, side); } catch (e) { /* приватное окно */ }
    wrap.querySelectorAll('.bd-world').forEach(function (w) { w.hidden = w.dataset.side !== side; });
    wrap.querySelectorAll('.bd-seg button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.side === side)); });
    if (st[side]) apply(); else fit();
  }

  wrap.querySelectorAll('.bd-seg button').forEach(function (b) { b.addEventListener('click', function () { show(b.dataset.side); }); });
  wrap.querySelector('.bd-tools').addEventListener('click', function (ev) {
    var b = ev.target.closest('button'); if (!b) return;
    var cx = view.clientWidth / 2, cy = view.clientHeight / 2;
    if (b.dataset.act === 'in') zoomAt(1.25, cx, cy);
    if (b.dataset.act === 'out') zoomAt(0.8, cx, cy);
    if (b.dataset.act === 'fit') fit();
    if (b.dataset.act === 'full') {
      if (document.fullscreenElement) document.exitFullscreen(); else if (wrap.requestFullscreen) wrap.requestFullscreen();
    }
  });
  document.addEventListener('fullscreenchange', function () {
    var b = wrap.querySelector('[data-act="full"]');
    b.textContent = document.fullscreenElement ? 'Выйти из полного экрана' : 'На весь экран';
    setTimeout(fit, 60);
  });

  view.addEventListener('wheel', function (ev) {
    ev.preventDefault();
    var r = view.getBoundingClientRect();
    if (ev.ctrlKey || ev.metaKey) { zoomAt(Math.exp(-ev.deltaY * 0.0022), ev.clientX - r.left, ev.clientY - r.top); return; }
    var s = st[side]; s.x -= ev.deltaX; s.y -= ev.deltaY; apply();
  }, { passive: false });

  // Панорама за фон, щипок двумя пальцами.
  var pts = new Map(), last = null, pinch = null;
  view.addEventListener('pointerdown', function (ev) {
    if (ev.target.closest('.bd-card') && ev.pointerType === 'mouse') return;
    pts.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
    view.setPointerCapture(ev.pointerId);
    if (pts.size === 1) { last = { x: ev.clientX, y: ev.clientY }; view.classList.add('is-panning'); }
    if (pts.size === 2) {
      var p = Array.from(pts.values());
      pinch = { d: Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y) };
    }
  });
  view.addEventListener('pointermove', function (ev) {
    if (!pts.has(ev.pointerId)) return;
    pts.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
    var r = view.getBoundingClientRect();
    if (pts.size === 2 && pinch) {
      var p = Array.from(pts.values()), d = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y);
      zoomAt(d / pinch.d, (p[0].x + p[1].x) / 2 - r.left, (p[0].y + p[1].y) / 2 - r.top); pinch.d = d; return;
    }
    if (last) { var s = st[side]; s.x += ev.clientX - last.x; s.y += ev.clientY - last.y; last = { x: ev.clientX, y: ev.clientY }; apply(); }
  });
  function up(ev) { pts.delete(ev.pointerId); if (pts.size < 2) pinch = null; if (!pts.size) { last = null; view.classList.remove('is-panning'); } }
  view.addEventListener('pointerup', up);
  view.addEventListener('pointercancel', up);

  view.addEventListener('keydown', function (ev) {
    var s = st[side], step = 60;
    if (ev.key === 'ArrowLeft') s.x += step; else if (ev.key === 'ArrowRight') s.x -= step;
    else if (ev.key === 'ArrowUp') s.y += step; else if (ev.key === 'ArrowDown') s.y -= step;
    else if (ev.key === '+' || ev.key === '=') { zoomAt(1.25, view.clientWidth / 2, view.clientHeight / 2); return; }
    else if (ev.key === '-') { zoomAt(0.8, view.clientWidth / 2, view.clientHeight / 2); return; }
    else return;
    ev.preventDefault(); apply();
  });

  // Переход по якорю шага (#c-05) — показать его сторону и подвести к нему.
  function focusHash() {
    var id = location.hash.slice(1), card = id && document.getElementById(id);
    if (!card || !card.classList.contains('bd-card')) return;
    show(id.charAt(0));
    var k = Math.min(1, view.clientHeight / 760);
    var col = card.closest('.bd-col');
    st[side] = { k: k, x: view.clientWidth / 2 - (parseFloat(col.style.left) + 280) * k, y: 24 - card.offsetTop * k };
    apply();
    wrap.scrollIntoView({ block: 'start' });
  }
  window.addEventListener('hashchange', focusHash);
  window.addEventListener('resize', function () { if (st[side]) apply(); });

  show(side);
  requestAnimationFrame(function () { fit(); focusHash(); });
})();
