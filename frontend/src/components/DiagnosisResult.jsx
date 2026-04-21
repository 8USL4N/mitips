function HypothesisCard({ item, title }) {
  return (
    <article className="result-card">
      {title && <h4>{title}</h4>}
      <h3>
        {item.diagnosis}
        {item.icd10 ? ` (${item.icd10})` : ""}
      </h3>
      <p>
        Лечение: <strong>{item.treatment_name}</strong>
      </p>
      <p>
        Совпадений: {item.matched_count}/{item.answered_count} из проверенных, критериев всего: {item.total_count}
      </p>

      <h4>План действий</h4>
      <ol>
        {item.actions.map((action, index) => (
          <li key={`${action}-${index}`}>{action}</li>
        ))}
      </ol>

      <h4>Объяснение</h4>
      <table>
        <thead>
          <tr>
            <th>Характеристика</th>
            <th>Ожидаемое</th>
            <th>Введённое</th>
            <th>Совпало</th>
          </tr>
        </thead>
        <tbody>
          {item.explanation.map((row, index) => (
            <tr key={`${row.characteristic}-${index}`} className={row.match ? "row-ok" : "row-bad"}>
              <td>{row.characteristic}</td>
              <td>{row.expected}</td>
              <td>{row.actual ?? "не указано"}</td>
              <td>{row.match ? "Да" : "Нет"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </article>
  );
}

function selectionMethodLabel(method) {
  if (method === "ml") {
    return "ML-модель";
  }
  if (method === "rules") {
    return "Правила";
  }
  return "Fallback";
}

export default function DiagnosisResult({ result }) {
  if (!result) {
    return null;
  }

  const statusClass = `status-banner status-${result.status}`;
  const primary = result.primary;
  const hasAlternatives = Array.isArray(result.alternatives) && result.alternatives.length > 0;

  return (
    <div className="result-block">
      <div className={statusClass}>{result.message}</div>

      {result.status === "ml_selected" && (
        <div className="alert">
          Найдено несколько подходящих диагнозов. Модель выбрала наиболее вероятный.
        </div>
      )}

      <div className="alert">
        Метод выбора: <strong>{selectionMethodLabel(result.selection_method)}</strong>
        {typeof result.confidence === "number" && (
          <>
            {" "}
            | Уверенность: <strong>{Math.round(result.confidence * 100)}%</strong>
          </>
        )}
      </div>

      {primary && <HypothesisCard item={primary} />}

      {Array.isArray(result.ranked_candidates) && result.ranked_candidates.length > 0 && (
        <div>
          <h4>Ранжированные кандидаты</h4>
          <table>
            <thead>
              <tr>
                <th>Диагноз</th>
                <th>Оценка</th>
                <th>Источник</th>
              </tr>
            </thead>
            <tbody>
              {result.ranked_candidates.map((item) => (
                <tr key={item.diagnosis_id}>
                  <td>{item.diagnosis}</td>
                  <td>{Math.round(item.score * 100)}%</td>
                  <td>{item.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {hasAlternatives && (
        <div className="accordion-list">
          {result.alternatives.map((item, index) => (
            <details key={item.diagnosis_id} open={index === 0}>
              <summary>
                {item.diagnosis}
                {item.icd10 ? ` (${item.icd10})` : ""}
              </summary>
              <HypothesisCard item={item} title="Альтернативный кандидат" />
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
