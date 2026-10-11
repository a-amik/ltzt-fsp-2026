import photoCand from './assets/landing/photo/rz-path.webp';
import photoEmployer from './assets/landing/photo/photo-employer.webp';
import './nav.css';

/* Вход: отдельный раздел, где сторона выбирается до кабинета. */
const SIDES = [
  { id: 'cand', photo: photoCand, cap: 'Кандидату', title: 'Кабинет кандидата', text: 'Вход по почте или через ФСП ID. Внутри — тест под категорию, профиль с метками и приглашения.', btn: 'Войти как кандидат' },
  { id: 'emp', photo: photoEmployer, cap: 'Работодателю', title: 'Кабинет работодателя', text: 'Вход по почте компании или в демо-компанию. Внутри — подбор по категориям, задания и приглашения с вилкой.', btn: 'Войти как работодатель' },
];

export default function Login({ go }) {
  return (
    <div className="lg">
      <div className="lg-head">
        <h1 className="r-h1">Вход в&nbsp;«Разряд»</h1>
        <p className="r-mute">Выберите, с&nbsp;какой стороны входите. Переключиться между кабинетами можно в&nbsp;шапке.</p>
      </div>
      <div className="lg-sides">
        {SIDES.map((s) => (
          <button key={s.id} className="lg-side" onClick={() => go(s.id)}>
            <img src={s.photo} alt="" width="1600" height="1067" />
            <span className="lg-side__body">
              <span className="r-micro">{s.cap}</span>
              <span className="r-h2">{s.title}</span>
              <span className="r-mute">{s.text}</span>
              <span className="r-btn r-btn--main">{s.btn}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
