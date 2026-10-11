/* Справочник для отрисовки. Источник истины — сервер (/api/catalog); эти
   значения совпадают с ним и нужны, чтобы рисовать до первого ответа. */
export const GRADES = [
  { id: 0, name: 'Стажёр', short: 'Intern', from: -9, to: -1.5 },
  { id: 1, name: 'Младший', short: 'Junior', from: -1.5, to: -0.5 },
  { id: 2, name: 'Средний', short: 'Middle', from: -0.5, to: 0.5 },
  { id: 3, name: 'Старший', short: 'Senior', from: 0.5, to: 1.5 },
  { id: 4, name: 'Ведущий', short: 'Lead', from: 1.5, to: 9 },
];
export const GRADE_HINT = ['Учусь, решаю учебные задачи', 'Делаю задачи под присмотром', 'Веду задачу сам от постановки до продакшена', 'Отвечаю за сервис и решения в нём', 'Отвечаю за систему и людей'];
export const SPECS = [
  { id: 'backend', name: 'Бэкенд', stack: ['Python', 'Go', 'Java', 'PostgreSQL', 'Kafka', 'Redis', 'Docker'] },
  { id: 'frontend', name: 'Фронтенд', stack: ['TypeScript', 'React', 'Vue', 'Next.js', 'CSS', 'Webpack'] },
  { id: 'mobile', name: 'Мобильная разработка', stack: ['Kotlin', 'Swift', 'Flutter', 'React Native'] },
  { id: 'data', name: 'Анализ данных', stack: ['SQL', 'Python', 'ClickHouse', 'Airflow', 'Tableau'] },
  { id: 'ml', name: 'Машинное обучение', stack: ['Python', 'PyTorch', 'scikit-learn', 'CUDA', 'MLflow'] },
  { id: 'devops', name: 'DevOps', stack: ['Kubernetes', 'Terraform', 'Linux', 'Ansible', 'Prometheus'] },
];
export const FORMATS = ['офис', 'гибрид', 'удалённо'];
export const REASONS = ['мало денег', 'не тот стек', 'формат', 'не ищу сейчас', 'компания не интересна'];
export const COOLDOWN_DAYS = 90;
export const WEIGHTS = { test: 0.6, stack: 0.15, fsp: 0.1, fresh: 0.1, social: 0.05 };
export const spec = (id) => SPECS.find((s) => s.id === id) || SPECS[0];
export const gradeName = (g) => (g == null ? '—' : GRADES[g].name);
export const fmt = (v) => (v == null ? '—' : v.toLocaleString('ru-RU').replace(/,/g, ' ') + ' ₽');
export const fmtRange = (a, b) => `${(a / 1000).toFixed(0)}–${(b / 1000).toFixed(0)} тыс. ₽`;
// Значение для экрана: с заглавной (данные в API остаются как есть).
export const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
// Дробное число по-русски: запятая и настоящий минус.
// Число со словом в нужной форме: plural(4, 'задание', 'задания', 'заданий') → «4 задания».
export const plural = (n, one, few, many) => { const a = Math.abs(n) % 100, b = a % 10; return `${n}\u00a0${a > 10 && a < 20 ? many : b === 1 ? one : b > 1 && b < 5 ? few : many}`; };
export const ZAD = ['задание', 'задания', 'заданий'];
export const KAND = ['кандидат', 'кандидата', 'кандидатов'];
export const LET = ['год', 'года', 'лет'];
export const num = (x, d = 2) => x.toFixed(d).replace('.', ',').replace('-', '−');
// Сервер отдаёт время в UTC без зоны («2026-10-11T18:05:00»): без «Z» браузер принял бы его за местное.
export const srvDate = (s) => new Date(typeof s === 'string' && !/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s + 'Z' : s);
export const dateRu = (s) => (s ? srvDate(s).toLocaleDateString('ru-RU') : '—');

// Статус поиска кандидата и статус найма компании (поля search и hiring на сервере).
export const SEARCH = [
  { id: 'active', name: 'Ищу работу', full: 'Ищу работу', hint: 'В выдаче компаний, приглашения приходят' },
  { id: 'open', name: 'Рассматриваю', full: 'Рассматриваю предложения', hint: 'В выдаче с меткой «Рассматривает предложения»' },
  { id: 'closed', name: 'Не ищу', full: 'Не ищу работу', hint: 'Из выдачи пропадаете, новых приглашений нет' },
];
export const searchName = (id) => (SEARCH.find((x) => x.id === (id || 'active')) || SEARCH[0]).full;
export const HIRING = [
  { id: 'active', name: 'Нанимаем', hint: 'Вакансии и задания видны кандидатам' },
  { id: 'paused', name: 'На паузе', hint: 'Вакансии и задания скрыты; подбор и банк работают' },
];
export const CITIES = ['Москва', 'Санкт-Петербург', 'Казань', 'Новосибирск', 'Екатеринбург', 'Томск', 'Иннополис', 'Нижний Новгород'];
export const FIELDS = ['Финтех', 'Ритейл', 'Медицина', 'Логистика', 'ГосИТ', 'Аналитика', 'B2B SaaS'];
export const SIZES = ['до 50', '50–200', '200–1000', '1000+'];

// Настройка агента кандидата (Candidate.agent на сервере, core/agents.py).
export const AGENT_CRITS = [['pay', 'Деньги'], ['format', 'Формат'], ['stack', 'Стек'], ['grade', 'Грейд'], ['motive', 'Рост и задачи']];
export const AGENT_IMP = [{ id: 'low', name: 'Неважно' }, { id: 'high', name: 'Важно' }, { id: 'stop', name: 'Стоп-фактор' }];
export const AGENT_STOPS = [['office', 'Офис без удалёнки'], ['duty', 'Ночные дежурства'], ['outstaff', 'Аутстаф и аутсорс'], ['grey', 'Неофициальная зарплата'], ['longtest', 'Тестовое дольше 4 часов']];
export const AGENT_ASKS = ['Кто будет руководителем и как устроена команда?', 'Как пересматривают зарплату?', 'Как устроен онбординг в первый месяц?', 'Можно ли работать из другого города?', 'Сколько этапов собеседования?', 'Какой технический долг в проекте?'];

// Ближайшие соревнования ФСП, на которые кандидат может записаться из профиля.
export const FSP_UPCOMING = [
  { id: 'cup-prod', name: 'Кубок России по продуктовому программированию', date: '14–16 ноября 2026', where: 'Онлайн-отбор', disc: 'Продуктовое программирование' },
  { id: 'ctf', name: 'Всероссийские соревнования по информационной безопасности', date: '28 ноября 2026', where: 'Онлайн', disc: 'Информационная безопасность' },
  { id: 'algo', name: 'Чемпионат России по алгоритмическому программированию, отбор', date: '6 декабря 2026', where: 'Региональные площадки', disc: 'Алгоритмическое программирование' },
];
