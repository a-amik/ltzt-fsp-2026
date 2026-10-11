/* Знак в движении на время загрузки данных. Анимация и палитра — в index.html (.sg):
   знак один для обеих версий — в цветах флага; при «уменьшении движения» стоит. */
export default function SignLoader({ small = false }) {
  return (
    <div className={`sg-wait ${small ? 'sg-wait--sm' : ''}`} role="status" aria-label="Загружаем">
      <svg className="sg" viewBox="-30 -24 182 192" aria-hidden="true">
        <rect className="sg-a" width="82" height="60" /><rect className="sg-b" x="40" y="30" width="82" height="60" />
        <rect className="sg-h" x="40" y="30" width="42" height="30" /><rect className="sg-l" y="90" width="40" height="54" />
      </svg>
    </div>
  );
}
