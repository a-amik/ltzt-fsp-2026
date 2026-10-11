"""Собирает лист-доску «Карта пути» в разделе fsp-2026 кабинета.

    python3 docs/cjm/build_board.py <папка снимков> <папка листа>

Снимки — JPEG 1440×900 с живого прототипа; на доску идут WebP: превью
960 px в карточке и полный кадр для просмотрщика. Текст карточек стоит
в разметке сразу, а не рисуется скриптом: к нему цепляются нити комментариев.
"""
import html
import json
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from steps import CAND, EMP  # noqa: E402

SRC, OUT = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
(OUT / "shots").mkdir(parents=True, exist_ok=True)

CARD_W, CARD_GAP, STAGE_GAP, TOP = 520, 48, 140, 96
e = html.escape


def shots(name):
    im = Image.open(SRC / f"{name}.jpg").convert("RGB")
    im.save(OUT / "shots" / f"{name}.webp", quality=84, method=6)
    t = im.resize((960, int(im.height * 960 / im.width)), Image.LANCZOS)
    t.save(OUT / "shots" / f"{name}-s.webp", quality=80, method=6)


COL_W, COL_GAP, CARD_H = 560, 120, 600


def lane(side, stages, label):
    """Этап — колонка, шаги в ней сверху вниз; этапы слева направо."""
    out, n, rows = [], 0, 0
    for si, (stage, steps) in enumerate(stages):
        x = si * (COL_W + COL_GAP)
        cards = []
        for k, (shot, title, human, system) in enumerate(steps):
            n += 1
            shots(shot)
            down = '<i class="bd-down" aria-hidden="true"></i>' if k < len(steps) - 1 else ''
            cards.append(f'''<article class="bd-card" id="{side}-{n:02d}">
  <a class="bd-shot" href="shots/{shot}.webp" data-zoom data-full="shots/{shot}.webp"><img src="shots/{shot}-s.webp" alt="{e(label)}, шаг {n}: {e(title)}" width="960" height="600"></a>
  <div class="bd-body">
    <p class="bd-n"><span>{n:02d}</span> {e(stage)}</p>
    <p class="bd-title">{e(title)}</p>
    <p><b>{"Кандидат" if side == "c" else "Работодатель"}:</b> {e(human)}</p>
    <p><b>Система:</b> {e(system)}</p>
  </div>{down}
</article>''')
        rows = max(rows, len(steps))
        nxt = '<i class="bd-next" aria-hidden="true"></i>' if si < len(stages) - 1 else ''
        out.append(f'''<section class="bd-col" style="left:{x}px;width:{COL_W}px" aria-label="Этап {si + 1}: {e(stage)}">
<div class="bd-stage"><span class="bd-stage-n">{si + 1}</span>{e(stage)}{nxt}</div>
{chr(10).join(cards)}
</section>''')
    w = len(stages) * (COL_W + COL_GAP) - COL_GAP
    return "\n".join(out), w, n, rows


c_html, c_w, c_n, c_r = lane("c", CAND, "Кандидат")
e_html, e_w, e_n, e_r = lane("e", EMP, "Работодатель")
c_h, e_h = TOP + c_r * CARD_H, TOP + e_r * CARD_H

page = f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="color-scheme" content="light dark">
<title>Карта пути: кандидат и работодатель</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🗺️%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="../../doc.css">
<link rel="stylesheet" href="../../doc-comments.css">
<link rel="stylesheet" href="board.css">
<script>
(function(){{try{{var v=localStorage.getItem('doc-theme');if(v==='light'||v==='dark')document.documentElement.setAttribute('data-theme',v);}}catch(e){{}}}})();
</script>
</head>
<body>

<div class="scrim" id="scrim"></div>
<div class="shell">

  <aside class="panel" id="panel" aria-label="Навигация по документу">
    <div class="panel-head">
      <button type="button" class="panel-close" id="btn-panel-close" aria-label="Закрыть панель">✕</button>
      <div class="pt-icon" aria-hidden="true">🗺️</div>
      <div class="pt-name">Карта пути</div>
      <div class="pt-sub">9&nbsp;октября 2026</div>
    </div>
    <nav class="panel-nav" id="panel-nav" aria-label="Содержание документа">
      <div class="cap">Содержание</div>
      <ul>
        <li><a href="#s1"><span class="n">1</span>Доска</a></li>
        <li><a href="#s2"><span class="n">2</span>Как комментировать</a></li>
      </ul>
      <nav class="panel-links">
        <a href="../0cc0abqgjcqbou4d/index.html">Разбор ТЗ и&nbsp;решение</a>
        <a href="../s67e3hg59pczkgbz/index.html">Вопросы экспертам</a>
        <a href="../1yc8jnpwvwf0gvmd/index.html">Бренд-кит и&nbsp;UI</a>
      </nav>
    </nav>
    <div class="panel-foot" data-doc-actions="panel-btn">
      <button class="panel-btn" id="btn-print" type="button">🖨 Печать / PDF</button>
    </div>
  </aside>

  <div class="topbar" id="topbar">
    <div class="tb-name">Карта пути</div>
    <button type="button" id="btn-panel-open" aria-label="Открыть содержание" aria-expanded="false" aria-controls="panel">§</button>
  </div>

  <div class="sheet" id="doc">

    <header>
      <span class="pageicon" aria-hidden="true">🗺️</span>
      <p class="eyebrow">ФСП · Разряд · карта пути</p>
      <h1>Карта пути кандидата и&nbsp;работодателя</h1>
      <p class="props">
        <span><b>Шагов</b>&nbsp;— кандидат {c_n}, работодатель {e_n}</span>
        <span><b>Снимки</b>&nbsp;— живой прототип, 9&nbsp;октября 2026</span>
      </p>
      <p class="lede">Весь путь обеих сторон на&nbsp;одной доске: что человек делает на&nbsp;каждом шаге и&nbsp;что отвечает система. Замечание к&nbsp;шагу&nbsp;— выделите его текст и&nbsp;оставьте комментарий: он сохранится в&nbsp;кабинете и&nbsp;уйдёт в&nbsp;работу.</p>
    </header>

    <h2 id="s1"><span class="no">1.</span> Доска</h2>

    <div class="bd-wrap" id="board">
      <div class="bd-bar" data-cm-skip>
        <div class="nm-seg bd-seg" role="group" aria-label="Чей путь">
          <button type="button" data-side="c" aria-pressed="true">Кандидат</button>
          <button type="button" data-side="e" aria-pressed="false">Работодатель</button>
        </div>
        <div class="bd-tools">
          <button type="button" class="bd-btn" data-act="out" aria-label="Уменьшить" title="Уменьшить">−</button>
          <span class="bd-zoom" aria-live="polite">100&nbsp;%</span>
          <button type="button" class="bd-btn" data-act="in" aria-label="Увеличить" title="Увеличить">+</button>
          <button type="button" class="bd-btn bd-btn--text" data-act="fit">Вписать</button>
          <button type="button" class="bd-btn bd-btn--text" data-act="full">На&nbsp;весь экран</button>
        </div>
      </div>
      <div class="bd-view" tabindex="0" aria-label="Доска: тяните фон, колесо — прокрутка, Ctrl и колесо или щипок — масштаб">
        <div class="bd-world" data-side="c" style="width:{c_w}px;height:{c_h}px">
{c_html}
        </div>
        <div class="bd-world" data-side="e" style="width:{e_w}px;height:{e_h}px" hidden>
{e_html}
        </div>
      </div>
    </div>

    <h2 id="s2"><span class="no">2.</span> Как комментировать</h2>
    <ul>
      <li><b>К&nbsp;шагу</b>&nbsp;— выделите текст карточки: название, строку «Кандидат», «Работодатель» или «Система». Появится кнопка комментария.</li>
      <li><b>Двигать доску</b>&nbsp;— тянуть за&nbsp;фон, прокрутка колесом или двумя пальцами; масштаб&nbsp;— Ctrl и&nbsp;колесо, щипок или кнопки над доской.</li>
      <li><b>Снимок крупно</b>&nbsp;— щелчок по&nbsp;снимку.</li>
    </ul>

  </div>
</div>

<script src="../../doc-stat.js"></script>
<script src="../../doc.js"></script>
<script src="../../doc-comments.js"></script>
<script src="../../offline.js"></script>
<script src="board.js"></script>
</body>
</html>
'''
(OUT / "index.html").write_text(page)
if not (OUT / "comments.json").exists():
    (OUT / "comments.json").write_text('{ "comments": [] }\n')
print("ok", c_n, e_n, c_w, e_w)
