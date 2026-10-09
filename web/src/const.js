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
export const WEIGHTS = { test: 0.6, stack: 0.2, fsp: 0.1, fresh: 0.1 };
export const spec = (id) => SPECS.find((s) => s.id === id) || SPECS[0];
export const gradeName = (g) => (g == null ? '—' : GRADES[g].name);
export const fmt = (v) => (v == null ? '—' : v.toLocaleString('ru-RU').replace(/,/g, ' ') + ' ₽');
export const fmtRange = (a, b) => `${(a / 1000).toFixed(0)}–${(b / 1000).toFixed(0)} тыс. ₽`;
export const dateRu = (s) => (s ? new Date(s).toLocaleDateString('ru-RU') : '—');
