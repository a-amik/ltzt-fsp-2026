import { useEffect, useState } from 'react';
import { useStore } from './store.jsx';
import { get } from './api.js';
import { GRADES, COOLDOWN_DAYS, WEIGHTS, spec, gradeName } from './const.js';
import { Trace, Mark, Score } from './ui.jsx';

export default function How() {
  const { state } = useStore();
  const [mech, setMech] = useState(null);
  const [tpls, setTpls] = useState([]);
  const [pair, setPair] = useState(null);
  const t = state.cand.tests?.[0];
  useEffect(() => { get(null, '/catalog/mechanics').then(setMech).catch(() => {}); get(null, '/catalog/templates').then(setTpls).catch(() => {}); get(null, '/catalog/fsp-pair').then(setPair).catch(() => {}); }, []);
  const cat = mech?.cat.full;
  const total = tpls.reduce((a, x) => a + x.shown, 0);
  return (
    <div className="page stack">
      <div>
        <p className="r-micro">Для жюри и&nbsp;для нас</p>
        <h1 className="r-h1">Как это работает</h1>
        <p className="r-mute">Три механики. Все цифры на&nbsp;странице — с&nbsp;сервера: пройдите тест и&nbsp;сделайте подбор, они поменяются.</p>
      </div>
      <section className="r-card r-card--flat stack-sm">
        <h2 className="r-h2">1. Тест: шаблоны и&nbsp;адаптивный показ</h2>
        <div className="steps">
          <div><b>Шаблон, а&nbsp;не&nbsp;задача.</b> У&nbsp;шаблона параметры, генератор данных и&nbsp;эталон. Цифры и&nbsp;сюжет у&nbsp;каждого кандидата свои, трудность одна — она откалибрована у&nbsp;шаблона. Эталон ответа не&nbsp;покидает сервер.</div>
          <div><b>Следующее задание — по&nbsp;текущей оценке.</b> Берём три самых информативных шаблона и&nbsp;одно из&nbsp;них случайно; самые показанные уходят в&nbsp;конец очереди. Тест короче, утечка одного варианта бесполезна.</div>
          <div><b>Стоп по&nbsp;точности.</b> {cat ? <>Минимум {cat.min_items} заданий, максимум {cat.max_items}; останавливаемся, когда погрешность ≤ {cat.target_se}. Экспресс для жюри — {mech.cat.express.max_items} задания.</> : '…'}</div>
          <div><b>Грейд — отрезок шкалы.</b> Не&nbsp;прошёл — тест на ступень ниже сразу; уверенно выше — отдельный тест на ступень выше; повтор того&nbsp;же уровня через {COOLDOWN_DAYS}&nbsp;дней. Не&nbsp;подтвердил — виден с&nbsp;меткой, ниже подтверждённых.</div>
        </div>
        {t ? <><p className="r-label">Ваш последний тест</p><Trace trace={t.trace || []} claimed={t.claimed} /></> : <p className="r-small r-mute">Пройдите тест в&nbsp;кабинете кандидата — здесь появится его ход.</p>}
        <p className="r-label">Банк шаблонов · {tpls.length} · показано экземпляров: {total}</p>
        <div className="tablewrap scroll-x"><table className="r-table">
          <thead><tr><th>Шаблон</th><th>Навык</th><th>Для кого</th><th>Формат</th><th>Трудность b</th><th>Различение a</th><th>Показан</th></tr></thead>
          <tbody>{[...tpls].sort((x, y) => x.b - y.b).map((x) => <tr key={x.id}><td>{x.id} {x.title}</td><td>{x.skill}</td><td className="r-small">{x.specs.map((s) => spec(s).name).join(', ')}</td><td>{x.format}</td><td className="r-num">{x.b}</td><td className="r-num">{x.a}</td><td className="r-num">{x.shown}</td></tr>)}</tbody>
        </table></div>
        <p className="r-small r-mute">Параметры a&nbsp;и&nbsp;b заданы экспертно и&nbsp;пересчитываются по&nbsp;ответам; шаблон с&nbsp;a&nbsp;&lt;&nbsp;0,5 уходит в&nbsp;доработку.</p>
      </section>
      <section className="r-card r-card--flat stack-sm">
        <h2 className="r-h2">2. Подбор: категории и&nbsp;порядок</h2>
        <div className="steps">
          <div><b>Сначала категория.</b> Специализация × грейд из&nbsp;теста — не&nbsp;из&nbsp;резюме. Работодатель видит категории с&nbsp;числом людей и&nbsp;выбирает сам.</div>
          <div><b>Потом порядок внутри.</b> Тест {WEIGHTS.test * 100}&nbsp;%, совпадение стека {WEIGHTS.stack * 100}&nbsp;%, ФСП {WEIGHTS.fsp * 100}&nbsp;%, свежесть {WEIGHTS.fresh * 100}&nbsp;%. Без истории ФСП — ноль по&nbsp;строке, не&nbsp;штраф. Все соревнования равны, считаются результативные.</div>
          <div><b>Объяснение из&nbsp;фактов.</b> Каждая строка «почему здесь» ссылается на&nbsp;факт и&nbsp;его источник: <Mark src="fsp" /> <Mark src="test" /> <Mark src="word" />.</div>
          <div><b>Фильтры не&nbsp;теряют отбор.</b> Отмеченные кандидаты остаются наверху при&nbsp;любом уточнении.</div>
        </div>
      </section>
      <section className="r-card r-card--flat stack-sm">
        <h2 className="r-h2">3. Контакт: приглашение и&nbsp;предразговор</h2>
        <div className="steps">
          <div><b>Пишет работодатель.</b> Приглашение без вилки не&nbsp;отправить; вилка ниже ожиданий — предупреждение до&nbsp;отправки.</div>
          <div><b>Агенты до&nbsp;решения.</b> Агент работодателя проходит один сценарий со&nbsp;всей категорией; агент кандидата отвечает только одобренными фактами. Протокол одинаков у&nbsp;обеих сторон.</div>
          <div><b>Статусы видят обе стороны.</b> Отправлено → просмотрено → принято или отклонено с&nbsp;причиной.</div>
          <div><b>Контакты — после «да».</b> До&nbsp;этого работодатель видит имя, места работы и&nbsp;подтверждённый профиль, но&nbsp;не&nbsp;почту и&nbsp;телефон.</div>
        </div>
      </section>
      {pair && (
        <section className="r-card r-card--flat stack-sm">
          <h2 className="r-h2">ФСП двигает внутри категории, но не закрывает дверь</h2>
          <p className="r-mute">{spec(pair.need.spec).name}, {gradeName(pair.need.grade).toLowerCase()}. Тест у двоих почти одинаковый, соревнования — только у одного.</p>
          <div className="grid2">{pair.pair.map((c) => (
            <div key={c.id} className="r-card stack-sm">
              <p className="r-micro">{c.fsp.length ? 'С историей ФСП' : 'Без истории ФСП'}</p>
              <p className="r-h3">{c.display} · место {c.pos} из {pair.total}</p>
              <p className="r-num r-small">оценка {c.theta.toFixed(2)} · балл {c.score.total.toFixed(3)}</p>
              <Score parts={c.score.parts} />
              {c.fsp.length ? <p className="r-small"><Mark src="fsp" /> {c.fsp[0].place} из {c.fsp[0].participants}, {c.fsp[0].level}</p> : <p className="r-small r-mute">Строка ФСП — ноль, не штраф.</p>}
            </div>))}</div>
          <p className="doc-note">В первой десятке этой категории {pair.top10_without_fsp} из 10 — без истории ФСП. Вес федерации 10 %: при равном тесте он решает порядок, при разнице в тесте больше 0,3 — нет.</p>
        </section>
      )}
      <section className="r-card r-card--flat stack-sm">
        <h2 className="r-h2">Грейды</h2>
        <div className="tablewrap scroll-x"><table className="r-table"><thead><tr><th>Грейд</th><th>Отрезок θ</th></tr></thead>
          <tbody>{GRADES.map((g) => <tr key={g.id}><td>{g.name} · {g.short}</td><td className="r-num">{g.from < -5 ? '…' : g.from} — {g.to > 5 ? '…' : g.to}</td></tr>)}</tbody></table></div>
      </section>
    </div>
  );
}
